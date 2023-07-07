# Distributed Tracing using Open Telemetry
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.propagators.cloud_trace_propagator import (
    CloudTraceFormatPropagator,
)
from opentelemetry.propagate import set_global_textmap
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.instrumentation.confluent_kafka import ConfluentKafkaInstrumentor


def configure_tracer(name: str, version: str = ""):
    resource = Resource.create(
        {
            "service.name": name,
            "service.version": version,
        }
    )
    tracer_provider = TracerProvider(resource=resource)
    cloud_trace_exporter = CloudTraceSpanExporter()
    tracer_provider.add_span_processor(
        # BatchSpanProcessor buffers spans and sends them in batches in a
        # background thread. The default parameters are sensible, but can be
        # tweaked to optimize your performance
        BatchSpanProcessor(cloud_trace_exporter)
    )
    trace.set_tracer_provider(tracer_provider)
    # Using the X-Cloud-Trace-Context header
    set_global_textmap(CloudTraceFormatPropagator())
    return trace.get_tracer(name, version)


def instrument_kafka_producer(producer):
    return ConfluentKafkaInstrumentor.instrument_producer(producer)


# Capture requests (sync and async)
RequestsInstrumentor().instrument()
HTTPXClientInstrumentor().instrument()
# Using the X-Cloud-Trace-Context header
set_global_textmap(CloudTraceFormatPropagator())
tracer = configure_tracer(name="cdip-integrations")
