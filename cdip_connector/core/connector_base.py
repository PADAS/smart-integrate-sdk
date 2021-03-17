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


# todo
async def gather_with_semaphore(n, *tasks):
    semaphore = asyncio.Semaphore(n)

    async def sem_task(task):
        async with semaphore:
            return await task
    return await asyncio.gather(*(sem_task(task) for task in tasks))


class AbstractConnector(ABC):
    DEFAULT_LOOKBACK_DAYS = cdip_settings.DEFAULT_LOOKBACK_DAYS
    DEFAULT_REQUESTS_TIMEOUT = (3.1, 20)

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
            # Fudge with a really long timeout value.
            async with ClientSession(timeout=ClientTimeout(total=180)) as session:
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

            if extracted is not None:
                logger.info(f'{integration.login}:{integration.id} {len(extracted)} recs to send')
                if extracted:
                    logger.info(f'first transformed payload: {extracted[0]}')

                await self.load(session, extracted)
                await self.update_state(session, integration)

                self.metrics.incr_count(MetricsEnum.TO_CDIP, len(extracted))
                total += len(extracted)
        if not total:
            logger.info(f'{integration.login}:{integration.id} Nothing to send to SIntegrate')
        return total

    @abstractmethod
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation) -> AsyncGenerator[List[CDIPBaseModel], None]:
        s = yield 0  # unreachable, but makes the return type AsyncGenerator, expected by caller

    async def update_state(self,
                           session: ClientSession,
                           integration_info: IntegrationInformation) -> None:
        await self.portal.update_state(session, integration_info)

    async def load(self,
                   session: ClientSession,
                   transformed_data: List[CDIPBaseModel]) -> None:

        headers = await self.portal.get_auth_header(session)

        def generate_batches(iterable, n=self.load_batch_size):
            for i in range(0, len(iterable), n):
                yield iterable[i:i+n]    

        logger.info(f'Posting to: {cdip_settings.CDIP_API_ENDPOINT}')
        for i, batch in enumerate(generate_batches(transformed_data)):
            for i in range(2):
                logger.debug(f'sending batch no: {i + 1}')
                clean_batch = [json.loads(r.json()) for r in batch]
                # batch = [dict(r) for r in batch]
                client_response = await session.post(url=cdip_settings.CDIP_API_ENDPOINT,
                                        headers=headers,
                                        json=clean_batch)
                # logger.info(client_response)
                # Kludge to handle Unauthorized.
                if client_response.status == 401:
                    headers = await self.portal.get_auth_header(session)
                else:
                    continue


