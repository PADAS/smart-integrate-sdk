import asyncio
import logging
from datetime import datetime
from typing import List

from aiohttp import ClientSession

from cdip_connector.core.connector_base import AbstractConnector
from cdip_connector.core.schemas import IntegrationInformation, CdipPosition

logger = logging.getLogger(__name__)


class MyConnector(AbstractConnector):
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation) -> List[CdipPosition]:
        # ETL extract code goes here. This is specific to each integration

        # update the state datastructure in IntegrationInformation before yield

        # yield a list of data records from this method, & caller will post to cdip api
        # needs to be a yield for this method to return an async_generator required by caller
        yield []


if __name__ == '__main__':
    logger.info('executing connector')
    connector = MyConnector()
    connector.execute()
    logger.info('all done. returning from external_trigger')
