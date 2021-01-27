import logging

import statsd

from cdip_connector.core import cdip_settings
from .schemas import MetricsEnum

logger = logging.getLogger(__name__)
logger.setLevel(cdip_settings.LOG_LEVEL)


class CdipMetrics:

    def __init__(self):
        metrics_prefix = cdip_settings.METRICS_PREFIX

        # query and add k8s namespace to metrics_prefix if deployed to k8s
        if cdip_settings.RUNNING_IN_K8S:
            try:
                with open('/var/run/secrets/kubernetes.io/serviceaccount/namespace', 'r') as f:
                    metrics_prefix = f'{f.read()}.{metrics_prefix}'
            except Exception as ex:
                logger.warning(f"Running in k8s but can't get namespace?? {ex}")

        logger.debug(f'statsd host: {cdip_settings.METRICS_PROXY_HOST}, port: {cdip_settings.METRICS_PROXY_PORT},'
                     f'prefix: {metrics_prefix}')

        self.statsd_client = statsd.StatsClient(host=cdip_settings.METRICS_PROXY_HOST,
                                                port=cdip_settings.METRICS_PROXY_PORT,
                                                prefix=metrics_prefix)

    def incr_count(self, stat: MetricsEnum, count: int = 1) -> None:
        self.statsd_client.incr(stat.value, count)
