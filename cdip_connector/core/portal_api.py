import json
import logging
from typing import List, Dict, Any
from uuid import UUID

from aiohttp import ClientSession
from pydantic import parse_raw_as

from cdip_connector.core import cdip_settings
from .schemas import IntegrationInformation, OAuthToken, TIntegrationInformation, DeviceState

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

    async def get_authorized_integrations(self,
                                          session: ClientSession,
                                          t_int_info: TIntegrationInformation = IntegrationInformation) -> List[IntegrationInformation]:
        logger.debug(f'get_authorized_integrations for : {cdip_settings.KEYCLOAK_CLIENT_ID}')
        headers = await self.get_auth_header(session)

        logger.debug(f'url: {self.integrations_endpoint}')
        response = await session.get(url=self.integrations_endpoint,
                                     headers=headers)
        response.raise_for_status()
        json_response = await response.text()
        json_response = json.loads(json_response)
        if isinstance(json_response, dict):
            json_response = [json_response]

        logger.debug(f'Got {len(json_response)} integrations for {cdip_settings.KEYCLOAK_CLIENT_ID}')
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
        logger.info(f'update integration state resp: {response.status}')
        response.raise_for_status()

        return await self.update_states_with_dict(session,
                                                   integration_info.id,
                                                   integration_info.device_states)

    async def fetch_device_states(self,
                                  session: ClientSession,
                                  inbound_id: UUID):
        headers = await self.get_auth_header(session)
        response = await session.get(url=f'{cdip_settings.PORTAL_API_DEVICES_ENDPOINT}/?inbound_config_id={inbound_id}',
                                     headers=headers)
        response.raise_for_status()
        resp_text = await response.text()
        states_received = parse_raw_as(List[DeviceState], resp_text)
        # todo: cleanup after all functions have their device state migrated over
        states_asdict = {}
        for s in states_received:
            if isinstance(s.state, dict) and 'value' in s.state:
                states_asdict[s.device_external_id] = s.state.get('value')
            else:
                states_asdict[s.device_external_id] = s.state
        return states_asdict
        # return {s.device_external_id: s.state for s in states_received}

    async def update_device_states(self,
                                   session: ClientSession,
                                   inbound_id: UUID,
                                   device_state: List[DeviceState]):
        states_dict = {s.device_external_id: s.state for s in device_state}
        return await self.update_states_with_dict(session, inbound_id, states_dict)

    async def update_states_with_dict(self,
                                      session: ClientSession,
                                      inbound_id: UUID,
                                      states_dict: Dict[str, Any]):
        headers = await self.get_auth_header(session)
        response = await session.post(url=f'{cdip_settings.PORTAL_API_DEVICES_ENDPOINT}/update/{inbound_id}',
                                      headers=headers,
                                      json=states_dict)
        response.raise_for_status()
        text = await response.text()
        logger.info(f'update device_states resp: {response.status}')
        return text

