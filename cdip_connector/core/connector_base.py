import asyncio, aiohttp
import json
import logging
from abc import ABC, abstractmethod
from typing import List, AsyncGenerator, Any

from aiohttp import ClientSession, ClientTimeout

from cdip_connector.core import cdip_settings
from cdip_connector.core import logconfig
from .schemas import IntegrationInformation, CDIPBaseModel
from .portal_api import PortalApi
from .tracing import tracer


logconfig.init()


class AbstractConnector(ABC):
    DEFAULT_LOOKBACK_DAYS = cdip_settings.DEFAULT_LOOKBACK_DAYS
    DEFAULT_REQUESTS_TIMEOUT = (3.1, 20)

    def __init__(self):

        self.logger = logging.getLogger(self.__class__.__name__)

        self.portal = PortalApi()

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

            async with ClientSession() as s:
                integrations = await self.portal.get_authorized_integrations(s)

            for idx in range(0, len(integrations), self.concurrency):

                async with ClientSession() as session:

                    self.logger.info(f"Running Integrations for client_id: {cdip_settings.KEYCLOAK_CLIENT_ID}")

                    tasks = [
                        asyncio.ensure_future(self.__class__().extract_load(session, integration))
                        for integration in integrations[idx: idx + self.concurrency]
                    ]

                    result = await asyncio.gather(*tasks)
                    self.logger.info(result)

        except Exception as ex:
            self.logger.exception("Uncaught exception in main.")
            raise

    async def extract_load(
        self, session: ClientSession, integration: IntegrationInformation
    ) -> int:


        self.logger.info(f'Executing Function for Integration: {integration.name} ({integration.id})', extra={
            'integration_id': str(integration.id),
            'integration_name': integration.name,
            'integration_endpoint': integration.endpoint
        })

        total = 0
        integration.device_states = await self.portal.fetch_device_states(session, integration.id)

        async for extracted in self.extract(session, integration):

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
            self, session: ClientSession, integration_info: IntegrationInformation
    ) -> AsyncGenerator[List[CDIPBaseModel], None]:
        s = (
            yield 0
        )  # unreachable, but makes the return type AsyncGenerator, expected by caller

    def item_callback(self, item):
        pass

    async def update_state(self, integration_info: IntegrationInformation) -> None:
        async with aiohttp.ClientSession() as sess:
            await self.portal.update_state(sess, integration_info)

    async def load(self, transformed_data: List[CDIPBaseModel]) -> None:

        async with aiohttp.ClientSession() as sess:
            headers = await self.portal.get_auth_header(sess)

        def generate_batches(iterable, n=self.load_batch_size):
            for i in range(0, len(iterable), n):
                yield iterable[i: i + n]

        for i, batch in enumerate(generate_batches(transformed_data)):

            self.logger.info(f"Posting to: {cdip_settings.CDIP_API_ENDPOINT}")

            self.logger.debug(f"r1 is: {batch[0]}")
            clean_batch = [json.loads(r.json()) for r in batch]

            for j in range(2):

                self.logger.debug(
                    "sending batch.",
                    extra={
                        "batch_no": i,
                        "length": len(batch),
                        "attempt": j,
                        "api": cdip_settings.CDIP_API_ENDPOINT,
                    },
                )

                async with aiohttp.ClientSession() as sess:
                    client_response = await sess.post(
                        url=cdip_settings.CDIP_API_ENDPOINT,
                        headers=headers,
                        json=clean_batch,
                        ssl=cdip_settings.CDIP_API_SSL_VERIFY,
                    )

                # Catch to attempt to re-authorized
                if client_response.status == 401:
                    headers = await self.portal.get_auth_header(sess)
                else:
                    [self.item_callback(item) for item in batch]
                    client_response.raise_for_status()
                    break
