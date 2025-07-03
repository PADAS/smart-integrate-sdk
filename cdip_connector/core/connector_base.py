import asyncio
import json
import logging
import hashlib
import backoff

from abc import ABC, abstractmethod
import uuid
from typing import List, AsyncGenerator, Dict, Any
import httpx
from cdip_connector.core import cdip_settings
from cdip_connector.core import logconfig
from gundi_core.schemas import IntegrationInformation, CDIPBaseModel
from gundi_client import PortalApi
from .tracing import tracer


logconfig.init()

logger = logging.getLogger(__name__)

class SessionExpiredException(Exception):
    pass


def calculate_partition(uuid: uuid.UUID, num_partitions: int) -> int:
    '''
    Calculate a partition from the UUID.
    This is a nice way to allow multiple instances of the same connector to run in parallel.
    '''
    return int(hashlib.sha1(uuid.bytes).hexdigest(), 16) % num_partitions

def filter_items_for_task(items: List[Any]) -> List[Any]:

    if cdip_settings.JOB_IS_PARTITIONED:
        logger.info(f"Filtering items for task. job_completion_index: {cdip_settings.JOB_COMPLETION_INDEX}, job_completion_count: {cdip_settings.JOB_COMPLETION_COUNT}")
        items = [item for item in items if calculate_partition(item.id, cdip_settings.JOB_COMPLETION_COUNT) == cdip_settings.JOB_COMPLETION_INDEX]
    return items

class AbstractConnector(ABC):
    DEFAULT_LOOKBACK_DAYS = cdip_settings.DEFAULT_LOOKBACK_DAYS
    DEFAULT_REQUESTS_TIMEOUT = (3.1, 20)

    def __init__(self):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.portal = PortalApi(data_timeout=cdip_settings.DEFAULT_DATA_TIMEOUT_SECONDS)

        self.load_batch_size = cdip_settings.INTEGRATION_LOAD_BATCH_SIZE
        self.concurrency = cdip_settings.INTEGRATION_CONCURRENCY

    def execute(self) -> None:
        connector_name = self.__class__.__name__
        with tracer.start_as_current_span(
            f"integrations.{connector_name}.execute"
        ) as current_span:
            current_span.set_attribute("service", f"cdip-integrations.{connector_name}")
            asyncio.run(self.main())

    async def main(self) -> None:
        try:
            integrations = await self.portal.get_authorized_integrations()
        except Exception as e:
            self.logger.exception(f"Exception reading integrations from the portal: {e}. Abort.")
            raise e
        self.logger.info(f"Running Integrations for client_id: {cdip_settings.KEYCLOAK_CLIENT_ID}")
        for idx in range(0, len(integrations), self.concurrency):
            tasks = [
                asyncio.ensure_future(self.__class__().extract_load(integration))
                for integration in integrations[idx: idx + self.concurrency]
            ]
            try:
                result = await asyncio.gather(*tasks)
            except Exception as e:
                self.logger.exception(f"Exception processing integrations batch {tasks}: {e}. Continuing.")
                continue
            else:
                self.logger.info(result)
        self.logger.info("Finished processing integrations.")

    async def extract_load(
        self, integration: IntegrationInformation
    ) -> Dict:

        self.logger.info(f'Executing Function for Integration: {integration.name} ({integration.id})', extra={
            'integration_id': str(integration.id),
            'integration_name': integration.name,
            'integration_endpoint': integration.endpoint
        })

        total = 0
        integration.device_states = await self.portal.fetch_device_states(integration.id)

        async for extracted in self.extract(integration):

            if extracted is not None:
                self.logger.info(
                    f"{integration.login}:{integration.id} extracted {len(extracted)} items",
                    extra={
                        "integration_id": integration.id,
                        "extracted_count": len(extracted),
                        "integration_type": integration.type_slug,
                        "integration_name": integration.name,
                        "integration_login": integration.login,

                    }
                )

                await self.load(extracted)
                total += len(extracted)

        await self.update_state(integration)

        if not total:
            self.logger.info(
                f"{integration.login}:{integration.id} no new data.",
                extra={
                    "integration_id": integration.id,
                    "extracted_count": total,
                    "integration_type": integration.type_slug,
                    "integration_name": integration.name,
                    "integration_login": integration.login,
                }
            )

        # Summary report for a single Integration.
        return {
            "integration_id": integration.id,
            "extracted_count": total,
            "integration_type": integration.type_slug,
            "integration_name": integration.name,
            "integration_login": integration.login,
        }

    @abstractmethod
    async def extract(
            self, integration_info: IntegrationInformation
    ) -> AsyncGenerator[List[CDIPBaseModel], None]:
        s = (
            yield 0
        )  # unreachable, but makes the return type AsyncGenerator, expected by caller

    def item_callback(self, item):
        pass

    async def update_state(self, integration_info: IntegrationInformation) -> None:
        await self.portal.update_state(integration_info)

    async def load(self, transformed_data: List[CDIPBaseModel]) -> None:

        def generate_batches(iterable, n=self.load_batch_size):
            for i in range(0, len(iterable), n):
                yield iterable[i: i + n]

        for i, batch in enumerate(generate_batches(transformed_data)):

            self.logger.info(f"Posting to: {cdip_settings.CDIP_API_ENDPOINT}")

            self.logger.debug(f"r1 is: {batch[0]}")
            clean_batch = [json.loads(r.json()) for r in batch]

            self.logger.debug(
                    "sending batch.",
                    extra={
                    "batch_no": i,
                    "length": len(clean_batch),
                    "api": cdip_settings.CDIP_API_ENDPOINT,
                    },
                )

            await self.load_batch(clean_batch)


    @backoff.on_exception(backoff.expo, (httpx.HTTPError, httpx.ReadTimeout, SessionExpiredException), max_tries=3)
    async def load_batch(self, clean_batch: List[CDIPBaseModel]) -> None:
        
        headers = await self.portal.get_auth_header()
        async with httpx.AsyncClient(timeout=120, verify=cdip_settings.CDIP_API_SSL_VERIFY) as session:
            client_response = await session.post(
                url=cdip_settings.CDIP_API_ENDPOINT,
                headers=headers,
                json=clean_batch,
            )

            # Catch to attempt to re-authorized
            if client_response.status_code == 401:
                raise SessionExpiredException()
            else:
                [self.item_callback(item) for item in clean_batch]
                client_response.raise_for_status()
