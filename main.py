import asyncio
import json
import itertools
import logging
from datetime import datetime

from aiohttp import ClientSession

from cdip_connector.core.connector_base import ConnectorBase
from cdip_connector.core.schemas import IntegrationInformation

logger = logging.getLogger(__name__)


class MyConnector(ConnectorBase):
    async def extract(self,
                      session: ClientSession,
                      integration_info: IntegrationInformation):
        # ETL extract code goes here. This is specific to each integration

        # might optionally update state with cdip portal:
        await self.update_state(session, integration_info)

        # return a list of data records from this method, & connector base will post to cdip api
        return []


if __name__ == '__main__':
    logger.info(f'executing connector')
    connector = MyConnector()
    connector.execute()
    logger.info('all done. returning from external_trigger')
