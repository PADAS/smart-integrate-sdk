import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from uuid import UUID

import pytz
import requests
from aiohttp import ClientSession, ClientResponseError
from pydantic import parse_obj_as

from cdip_connector.core import cdip_settings
from .schemas import IntegrationInformation, OAuthToken, TIntegrationInformation, DeviceState

logger = logging.getLogger(__name__)
logger.setLevel(cdip_settings.LOG_LEVEL)


class PortalApi:

    def __init__(self):
        self.client_id = cdip_settings.KEYCLOAK_CLIENT_ID
        self.client_secret = cdip_settings.KEYCLOAK_CLIENT_SECRET
        self.integrations_endpoint = f'{cdip_settings.PORTAL_API_ENDPOINT}/integrations/inbound/configurations'
        self.device_states_endpoint = f'{cdip_settings.PORTAL_API_ENDPOINT}/devices/states'
        self.devices_endpoint = f'{cdip_settings.PORTAL_API_ENDPOINT}/devices'

        self.oauth_token_url = cdip_settings.OAUTH_TOKEN_URL
        self.audience = cdip_settings.KEYCLOAK_AUDIENCE
        self.portal_api_endpoint = cdip_settings.PORTAL_API_ENDPOINT

        self.cached_token = None
        self.cached_token_expires_at = datetime.min.replace(tzinfo=pytz.utc)

    async def get_access_token(self,
                               session: ClientSession) -> OAuthToken:

        if self.cached_token and self.cached_token_expires_at > datetime.now(tz=pytz.utc):
            logger.info('Using cached token.')
            return self.cached_token

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
        token = await response.json()
        token = OAuthToken.parse_obj(token)
        self.cached_token_expires_at = datetime.now(tz=pytz.utc) + timedelta(
            seconds=token.expires_in - 15)  # fudge factor
        self.cached_token = token
        return token

    async def get_auth_header(self, session: ClientSession) -> dict:
        token_object = await self.get_access_token(session)
        return {
            "authorization": f"{token_object.token_type} {token_object.access_token}"
        }

    async def get_authorized_integrations(self,
                                          session: ClientSession,
                                          t_int_info: TIntegrationInformation = IntegrationInformation) -> List[
        IntegrationInformation]:
        logger.debug(f'get_authorized_integrations for : {cdip_settings.KEYCLOAK_CLIENT_ID}')
        headers = await self.get_auth_header(session)

        logger.debug(f'url: {self.integrations_endpoint}')
        response = await session.get(url=self.integrations_endpoint,
                                     headers=headers)
        response.raise_for_status()
        json_response = await response.json()

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
        try:
            headers = await self.get_auth_header(session)

            # This ought to be quick so just do it straight away.
            response = requests.get(url=f'{self.device_states_endpoint}/',
                                    params={'inbound_config_id': str(inbound_id)}, headers=headers, timeout=(3.1, 10))
            if response.status_code == 200:
                result = response.json()
        except ClientResponseError as ex:
            logger.exception('Failed to get devices for iic: {inbound_id}')
        else:
            states_received = parse_obj_as(List[DeviceState], result)
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

    async def ensure_device(self,
                            session: ClientSession,
                            inbound_id: UUID,
                            external_id: str):
        # Post device ID and Integration ID combination to ensure it exists
        # in the Portal's database and is also in the Integration's default
        # device group.
        headers = await self.get_auth_header(session)
        payload = {
            'external_id': external_id,
            'inbound_configuration': inbound_id
        }
        response = await session.post(url=self.devices_endpoint, json=payload, headers=headers)
        resp = await response.json()
        print(resp)
        if response.ok:
            return True
        else:
            logger.error('Failed to post device to portal.', extra={**payload, **resp})

        return False

    async def update_states_with_dict(self,
                                      session: ClientSession,
                                      inbound_id: UUID,
                                      states_dict: Dict[str, Any]):
        headers = await self.get_auth_header(session)
        response = await session.post(url=f'{self.device_states_endpoint}/update/{inbound_id}',
                                      headers=headers,
                                      json=states_dict)
        response.raise_for_status()
        text = await response.text()
        logger.info(f'update device_states resp: {response.status}')
        return text

    async def get_bridge_integration(self, session: ClientSession, bridge_id: str):

        headers = await self.get_auth_header(session)
        response = await session.get(url=f'{cdip_settings.PORTAL_API_ENDPOINT}/integrations/bridges/{bridge_id}',
                                     headers=headers)
        response.raise_for_status()
        return await response.json()
