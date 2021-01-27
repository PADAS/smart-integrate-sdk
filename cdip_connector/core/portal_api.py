import json
import logging
from typing import List

from aiohttp import ClientSession

from cdip_connector.core import cdip_settings
from .schemas import IntegrationInformation, OAuthToken, TIntegrationInformation

logger = logging.getLogger(__name__)
logger.setLevel(cdip_settings.LOG_LEVEL)


class PortalApi:

    def __init__(self):
        self.client_id = cdip_settings.KEYCLOAK_CLIENT_ID
        self.client_secret = cdip_settings.KEYCLOAK_CLIENT_SECRET
        self.integrations_endpoint = cdip_settings.PORTAL_API_INBOUND_INTEGRATIONS_ENDPOINT
        self.oauth_token_url = cdip_settings.OAUTH_TOKEN_URL
        self.audience = cdip_settings.KEYCLOAK_AUDIENCE

    async def get_access_token(self,
                               session: ClientSession) -> OAuthToken:
        logger.debug(f'get_access_token from {self.oauth_token_url} using client_id: {self.client_id}')
        payload = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'audience': self.audience,
            'grant_type': 'urn:ietf:params:oauth:grant-type:uma-ticket',
            'scope': 'openid',
        }

        response = await session.post(self.oauth_token_url,
                                      data=payload)

        response.raise_for_status()
        token = await response.text()
        return OAuthToken.parse_obj(json.loads(token))

    async def get_auth_header(self, session: ClientSession) -> dict:
        token_object = await self.get_access_token(session)
        return {
            "authorization": f"{token_object.token_type} {token_object.access_token}"
        }

    async def get_integrations_for_type(self,
                                        session: ClientSession,
                                        type_slug: str,
                                        t_int_info: TIntegrationInformation = IntegrationInformation) -> List[IntegrationInformation]:
        logger.debug(f'get_integrations_for_type: {type_slug}')
        headers = await self.get_auth_header(session)

        logger.debug(f'url: {self.integrations_endpoint}, params: {type_slug}')
        response = await session.get(url=self.integrations_endpoint,
                                     params=dict(type_slug=type_slug),
                                     headers=headers)
        response.raise_for_status()
        json_response = await response.text()
        json_response = json.loads(json_response)
        if isinstance(json_response, dict):
            json_response = [json_response]

        logger.debug(f'Got {len(json_response)} integrations of type {type_slug}')
        return [
            t_int_info.parse_obj(r) for r in json_response
        ]

    async def update_state(self,
                           session: ClientSession,
                           integration_info: IntegrationInformation) -> None:
        headers = await self.get_auth_header(session)

        response = await session.put(
            url=f'{self.integrations_endpoint}/{integration_info.id}',
            headers=headers,
            json=dict(state=integration_info.state))
        logger.info(f'cursor upd resp: {response.status}')
        response.raise_for_status()
