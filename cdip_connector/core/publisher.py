import json
import logging
from abc import ABC, abstractmethod

from confluent_kafka import Producer

from cdip_connector.core import cdip_settings

logger = logging.getLogger(__name__)


class Publisher(ABC):

    @abstractmethod
    def publish(self, topic: str, data: dict, extra: dict = None):
        ...


class KafkaPublisher(Publisher):

    def __init__(self):
        cloud_enabled = cdip_settings.CONFLUENT_CLOUD_ENABLED

        config_dict = {'bootstrap.servers': cdip_settings.KAFKA_BROKER}

        if cloud_enabled:
            config_dict['security.protocol'] = 'SASL_SSL'
            config_dict['sasl.mechanisms'] = 'PLAIN'
            config_dict['sasl.username'] = cdip_settings.CONFLUENT_CLOUD_USERNAME
            config_dict['sasl.password'] = cdip_settings.CONFLUENT_CLOUD_PASSWORD

        self.producer = Producer(config_dict)

    @staticmethod
    def create_message_key(data):
        integration_id = data.get('integration_id')
        device_id = data.get('device_id')
        if integration_id and device_id:
            return f'{integration_id}.{device_id}'
        else:
            # logger.warning(f'Unable to determine key, integration_id or device_id not present in observation')
            return None

    def publish(self, topic: str, data: dict, extra: dict = None):
        if not extra:
            extra = {}
        key = None
        if cdip_settings.KEY_ORDERING_ENABLED:
            key = self.create_message_key(data)
        message = {'attributes': extra,
                   'data': data}
        jsonified_data = json.dumps(message, default=str)
        try:
            if key:
                self.producer.produce(topic, value=jsonified_data, key=key)
            else:
                self.producer.produce(topic, value=jsonified_data)
            self.producer.poll()
        except Exception as e:
            # TODO: For message integrity, how should we recover here?
            self.producer.flush()
            messsage_size_bytes = 0
            extra_dict = {}
            if jsonified_data:
                messsage_size_bytes = len(jsonified_data.encode('utf-8'))
                extra_dict['message'] = jsonified_data
                extra_dict['message_size_bytes'] = messsage_size_bytes
            logger.exception(f'Exception thrown while attempting to publish message to kafka stream: {e}',
                             extra=extra_dict)


class NullPublisher(Publisher):

    def publish(self, topic: str, data: dict, extra: dict = None):
        pass


def get_publisher():
    if cdip_settings.PUBSUB_ENABLED:
        # return GooglePublisher()
        return KafkaPublisher()
    else:
        return NullPublisher()