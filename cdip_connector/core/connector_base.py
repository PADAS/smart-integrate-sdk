import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Any

from aiohttp import ClientSession

from cdip_connector.core import cdip_settings
from cdip_connector.core import logconfig
from .schemas import MetricsEnum, IntegrationInformation, CDIPBaseModel
from .metrics import CdipMetrics
from .portal_api import PortalApi

logconfig.init()
logger = logging.getLogger(__name__)
logger.setLevel(cdip_settings.LOG_LEVEL)


# todo
async def gather_with_semaphore(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*(sem_task(task) for task in tasks))


class AbstractConnector(ABC):

    def __init__(self):
        super().__init__()
        self.portal = PortalApi()
        self.metrics = CdipMetrics()
        self.load_batch_size = 1000  # a default meant to be overridden as needed

    def execute(self) -> None:
        self.metrics.incr_count(MetricsEnum.INVOKED)
        asyncio.run(self.main())

    async def main(self) -> None:
        try:
            async with ClientSession() as session:
                logger.info(f'CLIENT_ID: {cdip_settings.KEYCLOAK_CLIENT_ID}')
                integration_info = await self.portal.get_authorized_integrations(session)

                # todo gather_with_semaphore!
                result = await asyncio.gather(*[
                    self.extract_load(session, i) for i in integration_info
                ])

                logger.info(result)
        except Exception as ex:
            self.metrics.incr_count(MetricsEnum.ERRORS)
            logger.exception(f'Exception raised {ex}')

    async def extract_load(self,
                           session: ClientSession,
                           integration: IntegrationInformation) -> int:
        total = 0
        device_states = await self.portal.fetch_device_states(session, integration.id)
        integration.device_states = device_states
        async for extracted in self.extract(session, integration):
            # transformed = [self.transform(integration.integration_id, r) for r in extracted]
            if extracted:
                logger.info(f'{integration.login}:{integration.id} {len(extracted)} recs to send')
                logger.info(f'first transformed payload: {extracted[0]}')

                await self.load(session, extracted)
                await self.update_state(session, integration)

                self.metrics.incr_count(MetricsEnum.TO_CDIP, len(extracted))
                total += len(extracted)
        if not total:
            logger.info(f'{integration.login}:{integration.id} Nothing to send to CDIP')
        return total

    @abstractmethod
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation) -> AsyncGenerator[List[CDIPBaseModel], None]:
        s = yield 0  # unreachable, but makes the return type AsyncGenerator, expected by caller

    # @abstractmethod
    # def transform(self, integration_id, data):
    #     return data

    async def update_state(self,
                           session: ClientSession,
                           integration_info: IntegrationInformation) -> None:
        await self.portal.update_state(session, integration_info)

    async def load(self,
                   session: ClientSession,
                   transformed_data: List[CDIPBaseModel]) -> None:

        transformed_data = [r.dict() for r in transformed_data]
        headers = await self.portal.get_auth_header(session)

        def generate_batches(batch_size=self.load_batch_size):
            num_obs = len(transformed_data)
            for start_index in range(0, num_obs, batch_size):
                yield transformed_data[start_index: min(start_index + batch_size, num_obs)]

        logger.info(f'Posting to: {cdip_settings.CDIP_API_ENDPOINT}')
        for i, batch in enumerate(generate_batches()):
            logger.debug(f'sending batch no: {i + 1}')
            resp = await session.post(url=cdip_settings.CDIP_API_ENDPOINT, headers=headers, json=batch)
            logger.info(resp)
            resp.raise_for_status()
