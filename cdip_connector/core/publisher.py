import json
import logging
from abc import ABC, abstractmethod

from cdip_connector.core import cdip_settings
from confluent_kafka import Producer, KafkaException

from . import tracing

logger = logging.getLogger(__name__)


class Publisher(ABC):
    @abstractmethod
    def publish(self, topic: str, data: dict, extra: dict = None):
        ...


class KafkaPublisher(Publisher):
    def __init__(self):

        cloud_enabled = cdip_settings.CONFLUENT_CLOUD_ENABLED

        config_dict = {"bootstrap.servers": cdip_settings.KAFKA_BROKER}

        if cloud_enabled:
            config_dict["security.protocol"] = "SASL_SSL"
            config_dict["sasl.mechanisms"] = "PLAIN"
            config_dict["sasl.username"] = cdip_settings.CONFLUENT_CLOUD_USERNAME
            config_dict["sasl.password"] = cdip_settings.CONFLUENT_CLOUD_PASSWORD

        self.producer = tracing.instrument_kafka_producer(Producer(config_dict))

    def __del__(self):
        """
        Flushes the producer before being GC'd.
        """
        self.producer.flush(timeout=10)

    @staticmethod
    def create_message_key(data):
        integration_id = data.get("integration_id")
        device_id = data.get("device_id")
        if integration_id and device_id:
            return f"{integration_id}.{device_id}"

    def on_delivery(self, err, msg):
        if err:
            logger.error("Error: %s (%s)", error.name(), err.code())
        else:
            logger.debug("Message delivered to %s [%d]", msg.topic(), msg.partition())

    def publish(self, topic: str, data: dict, extra: dict = None):

        extra = extra or {}
        key = None

        if cdip_settings.KEY_ORDERING_ENABLED:
            key = self.create_message_key(data)
        message = {"attributes": extra, "data": data}
        jsonified_data = json.dumps(message, default=str)

        try:
            self.producer.produce(
                topic, value=jsonified_data, key=key, on_delivery=self.on_delivery
            )
            self.producer.poll(timeout=10)
        except KafkaException as e:
            # TODO: For message integrity, how should we recover here?
            self.producer.flush(timeout=10)
            logger.exception(
                f"Exception thrown while attempting to publish message to kafka stream: {e}"
            )


class NullPublisher(Publisher):
    def publish(self, topic: str, data: dict, extra: dict = None):
        pass


def get_publisher():
    if cdip_settings.PUBSUB_ENABLED:
        # return GooglePublisher()
        return KafkaPublisher()
    else:
        return NullPublisher()
