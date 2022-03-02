import asyncio
import json
import logging
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Any

from aiohttp import ClientSession, ClientTimeout

from cdip_connector.core import cdip_settings
from cdip_connector.core import logconfig
from .schemas import MetricsEnum, IntegrationInformation, CDIPBaseModel
from .metrics import CdipMetrics
from .portal_api import PortalApi

logconfig.init()
logger = logging.getLogger(__name__)
logger.setLevel(cdip_settings.LOG_LEVEL)

CLIENT_TIMEOUT_TOTAL = 180  # seconds


class AbstractConnector(ABC):
    DEFAULT_LOOKBACK_DAYS = cdip_settings.DEFAULT_LOOKBACK_DAYS
    DEFAULT_REQUESTS_TIMEOUT = (3.1, 20)

    def __init__(self):
        super().__init__()
        self.request_schema = None
        self.portal = PortalApi()
        self.metrics = CdipMetrics()
        self.load_batch_size = 1000  # a default meant to be overridden as needed

    def execute_action(self):
        """
            Executes an specific action within an already-set schema

            AVAILABLE ACTIONS:

            - "test_login": Get payload info and try to authenticate into external API

            - "fetch_samples": With payload info, go to the integration 'extract' code and fetch a few samples (pydantic model)

            - "extract_and_load": With payload info, executes integration 'extract' and then transform the data to be posted to ER

            :param self: The complete request schema (self.request_schema)
            :return: JSON with the result and status
        """
        self.metrics.incr_count(MetricsEnum.INVOKED)

        logger.info(f'EXECUTING ACTION: {self.request_schema.action}')

        action_function = getattr(self, self.request_schema.action)
        message, status = asyncio.run(action_function())

        return {"result": message}, status

    async def test_login(self):
        """
            Get payload info and try to authenticate into external API

            :param self: The complete request schema (self.request_schema)
            :return: JSON with the result and status
        """
        try:
            async with ClientSession(timeout=ClientTimeout(total=CLIENT_TIMEOUT_TOTAL)) as session:
                result = await self.authenticate(
                    session,
                    self.request_schema.configuration.username,
                    self.request_schema.configuration.password,
                    self.request_schema.configuration.url
                )
                logger.info(result)
                return ("Logged successfully!", 200) if result else ("Unsuccessful login.", 403)

        except Exception as ex:
            self.metrics.incr_count(MetricsEnum.ERRORS)
            logger.exception('Uncaught exception in test_login.')
            return "An error occurred.", 500

    async def extract_and_load(self):
        """
            With payload info, executes integration 'extract' and then transform the data to be posted to ER,
            then the state is updated to latest timestamp (integration)

            :param self: The complete request schema (self.request_schema)
            :return: JSON with the result and status
        """
        try:
            async with ClientSession(timeout=ClientTimeout(total=CLIENT_TIMEOUT_TOTAL)) as session:
                result = [await self.extract_load(session)]
                logger.info(result)
                return result, 200
        except Exception as ex:
            self.metrics.incr_count(MetricsEnum.ERRORS)
            logger.exception('Uncaught exception in extract_and_load.')
            return "An error occurred.", 500

    async def fetch_samples(self):
        """
            With payload info, go to the integration 'extract' code and fetch a few samples (pydantic model)

            :param self: The complete request schema (self.request_schema)
            :return: JSON with the result and status
        """
        try:
            async with ClientSession(timeout=ClientTimeout(total=CLIENT_TIMEOUT_TOTAL)) as session:
                async for extracted in self.extract(session, self.request_schema):
                    return extracted[:3], 200
        except Exception as ex:
            self.metrics.incr_count(MetricsEnum.ERRORS)
            logger.exception('Uncaught exception in fetch_samples.')
            return "An error occurred.", 500

    async def extract_load(self, session: ClientSession) -> int:
        total = 0
        device_states, integration_state = await self.portal.get_states(session, self.request_schema.configuration.integration_id)
        self.request_schema.configuration.device_states = device_states
        self.request_schema.configuration.state = integration_state
        async for extracted in self.extract(session, self.request_schema):
            if extracted is not None:
                logger.info(
                    f'{self.request_schema.configuration.username}:{self.request_schema.configuration.integration_id} {len(extracted)} recs to send')
                if extracted:
                    logger.info(f'first transformed payload: {extracted[0]}')

                await self.load(session, extracted)
                await self.update_state(session)

                self.metrics.incr_count(MetricsEnum.TO_CDIP, len(extracted))
                total += len(extracted)
        if not total:
            logger.info(
                f'{self.request_schema.configuration.username}:{self.request_schema.configuration.integration_id} Nothing to send to SIntegrate')
        return total

    """
    async def get_integration_info(self, integration_id: str) -> IntegrationInformation:
        try:
            async with ClientSession(timeout=ClientTimeout(total=CLIENT_TIMEOUT_TOTAL)) as session:
                logger.info(f'GETTING INTEGRATION FOR CLIENT_ID: {cdip_settings.KEYCLOAK_CLIENT_ID}')
                return await self.portal.get_authorized_integrations(session, integration_id)

        except Exception as ex:
            self.metrics.incr_count(MetricsEnum.ERRORS)
            logger.exception('Uncaught exception in get_integration_info.')
            raise
    """

    @abstractmethod
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation) -> AsyncGenerator[List[CDIPBaseModel], None]:
        s = yield 0  # unreachable, but makes the return type AsyncGenerator, expected by caller

    def item_callback(self, item):
        pass

    async def update_state(self, session: ClientSession) -> None:
        await self.portal.update_state(session, self.request_schema.configuration)

    async def load(self,
                   session: ClientSession,
                   transformed_data: List[CDIPBaseModel]) -> None:

        headers = {
            "apikey": f"{self.request_schema.configuration.apikey}"
        }

        def generate_batches(iterable, n=self.load_batch_size):
            for i in range(0, len(iterable), n):
                yield iterable[i:i + n]

        logger.info(f'Posting to: {self.request_schema.configuration.sensors_api_url}')
        for i, batch in enumerate(generate_batches(transformed_data[:10])):

            logger.debug(f'r1 is: {batch[0]}')
            clean_batch = [json.loads(r.json()) for r in batch]

            for j in range(2):

                logger.debug('sending batch.', extra={'batch_no': i, 'length': len(batch), 'attempt': j})

                client_response = await session.post(url=self.request_schema.configuration.sensors_api_url,
                                                     headers=headers,
                                                     json=clean_batch,
                                                     ssl=True)

                # Catch to attemp to re-authorized
                if client_response.status == 401:
                    headers = await self.portal.get_auth_header(session)
                else:
                    # [self.item_callback(item) for item in batch]
                    client_response.raise_for_status()
                    break
