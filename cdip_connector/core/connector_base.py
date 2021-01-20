import asyncio
import logging
from abc import ABC, abstractmethod
from typing import List

from aiohttp import ClientSession

from cdip_connector.core import cdip_settings as settings
from cdip_connector.core import logconfig
from .schemas import MetricsEnum, IntegrationInformation, CdipPosition
from .metrics import CdipMetrics
from .portal_api import PortalApi

logconfig.init()
logger = logging.getLogger(__name__)


class ConnectorBase(ABC):

    def __init__(self):
        super().__init__()
        self.portal = PortalApi()
        self.metrics = CdipMetrics()
        self.load_batch_size = 500  # a default meant to be overridden as needed

    def execute(self) -> None:
        self.metrics.incr_count(MetricsEnum.INVOKED)
        asyncio.run(self.main())

    async def main(self) -> None:
        try:
            async with ClientSession() as session:
                logger.info(f'CDIP_INTEGRATION_TYPE_SLUG: {settings.CDIP_INTEGRATION_TYPE_SLUG}')
                integration_info = await self.portal.get_integrations_for_type(session,
                                                                               settings.CDIP_INTEGRATION_TYPE_SLUG)

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
        extracted = await self.extract(session, integration)
        if extracted:
            # transformed = [self.transform(integration.integration_id, r) for r in extracted]
            logger.info(f'{integration.login}:{integration.id} {len(extracted)} recs to send')
            logger.info(f'first transformed payload: {extracted[0]}')

            await self.load(session, extracted)
            await self.update_state(session, integration)

            self.metrics.incr_count(MetricsEnum.TO_CDIP, len(extracted))
        else:
            logger.info(f'{integration.login}:{integration.id} Nothing to send to CDIP')
        return len(extracted) if extracted else 0

    @abstractmethod
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation) -> List[CdipPosition]:
        ...

    # @abstractmethod
    # def transform(self, integration_id, data):
    #     return data

    async def update_state(self,
                           session: ClientSession,
                           integration_info: IntegrationInformation) -> None:
        await self.portal.update_state(session, integration_info)

    async def load(self,
                   session: ClientSession,
                   transformed_data: List[CdipPosition]) -> None:

        transformed_data = [r.dict() for r in transformed_data]
        headers = await self.portal.get_auth_header(session)

        def generate_batches(batch_size=self.load_batch_size):
            num_obs = len(transformed_data)
            for start_index in range(0, num_obs, batch_size):
                yield transformed_data[start_index: min(start_index + batch_size, num_obs)]

        positions_url = f'{settings.CDIP_API}/positions/'
        logger.info(positions_url)
        for i, batch in enumerate(generate_batches()):
            logger.debug(f'sending batch no: {i + 1}')
            resp = await session.post(url=positions_url, headers=headers, json=batch)
            logger.info(resp)
            resp.raise_for_status()
