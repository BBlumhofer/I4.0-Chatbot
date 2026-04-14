from __future__ import annotations

from pathlib import Path
from typing import List

import structlog
from confluent_kafka import SerializingProducer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer
from confluent_kafka.serialization import StringSerializer

from pyuaadapter.server.base_module import BaseModule
from pyuaadapter.server.plugins.base_plugin import BasePlugin

from .kafka_skill_monitoring_publisher import KafkaSkillMonitoringPublisher
from .kafka_skill_publisher import KafkaSkillPublisher


class KafkaAvroProducer:
    logger = structlog.getLogger("sf.server.plugins.kafka")

    def __init__(self, schema_file_name: str, topic: str, kafka_bootstrap_server, schema_registry_client):
        self.topic = topic
        with open(schema_file_name, "r") as file:
            value_schema = "".join(file.readlines())

        self.logger.info(f"Trying to connect to kafka bootstrap server @ {kafka_bootstrap_server}...")
        self.producer = SerializingProducer(
            {'bootstrap.servers': kafka_bootstrap_server,
             'key.serializer': StringSerializer('utf_8'),
             'value.serializer': AvroSerializer(schema_registry_client, value_schema)
             })

    def __del__(self):
        self.logger.info("Flushing kafka producer...")
        self.producer.flush()

    def publish(self, key, value, log_delivery=False) -> None:
        """ Publishes the given key/value (string/dictionary) pair to the topic of this producer. """
        self.producer.produce(topic=self.topic, key=key, value=value,
                              on_delivery=self._delivery_report if log_delivery else None)
        self.producer.poll(0.1)

    @classmethod
    def _delivery_report(cls, err, msg):
        if err is not None:
            cls.logger.error(err)
        else:
            cls.logger.debug(f'{msg.key()} = {msg.value()} successfully produced to {msg.topic()} '
                             f'[{msg.partition()}] at offset {msg.offset()}')


class Plugin(BasePlugin):
    """ This plugin provides an automatic kafka one-way mirror (publish only) of the module state and it's skills. """
    logger = structlog.getLogger("sf.server.plugins.kafka")
    module: BaseModule
    schema_registry_client: SchemaRegistryClient
    skill_producer: KafkaAvroProducer
    skill_monitoring_producer: KafkaAvroProducer
    module_producer: KafkaAvroProducer
    skill_publisher: List[KafkaSkillPublisher] = []
    skill_monitoring_publisher: List[KafkaSkillMonitoringPublisher] = []

    @property
    def is_enabled(self) -> bool:
        return hasattr(self.config, "KAFKA_ENABLE") and self.config.KAFKA_ENABLE

    async def init(self, module: BaseModule) -> None:
        self.module = module

        self.logger.setLevel(logging.DEBUG if self.config.DEBUG else logging.INFO)

        kafka_schema_registry = self.config.KAFKA_SCHEMA_REGISTRY
        self.logger.info(f"Trying to connect to kafka schema registry @ {kafka_schema_registry}...")
        self.schema_registry_client = SchemaRegistryClient({'url': kafka_schema_registry})

        skill_schema_default = Path(__file__).parent.joinpath("schemas/ifs-opcua-skill.avsc")
        skill_schema = self.config.KAFKA_SKILL_SCHEMA if self.config.KAFKA_SKILL_SCHEMA is not None else skill_schema_default
        skill_topic = self.config.KAFKA_TOPIC_PREFIX + "SKILLS" + self.config.KAFKA_TOPIC_SUFFIX
        self.skill_producer = KafkaAvroProducer(schema_file_name=skill_schema,
                                                schema_registry_client=self.schema_registry_client,
                                                topic=skill_topic,
                                                kafka_bootstrap_server=self.config.KAFKA_BOOTSTRAP_SERVER)

        skill_monitoring_schema_default = Path(__file__).parent.joinpath("schemas/ifs-opcua-skill-monitoring.avsc")
        skill_monitoring_topic = self.config.KAFKA_TOPIC_PREFIX + "SKILLS_MONITORING" + self.config.KAFKA_TOPIC_SUFFIX
        self.skill_monitoring_producer = KafkaAvroProducer(schema_file_name=skill_monitoring_schema_default,  # TODO
                                                           schema_registry_client=self.schema_registry_client,
                                                           topic=skill_monitoring_topic,
                                                           kafka_bootstrap_server=self.config.KAFKA_BOOTSTRAP_SERVER)

        # TODO module producer

    async def _process_asset(self, asset: 'BaseAsset'):
        await self._add_skills(asset.skills)
        for name, subcomponent in asset.components.items():
            self.logger.info(f"Processing subcomponent {name}...")
            await self._process_asset(subcomponent)

    async def _add_skills(self, skills: dict[str, 'BaseSkill']):
        for name, skill in skills.items():
            if name in self.config.KAFKA_BLACKLIST_SKILLS:
                self.logger.info(f"Skipping skill '{name}'!")
                continue
            self.logger.info(f"Adding SkillPublisher for Skill '{name}'...")
            self.skill_publisher.append(
                await KafkaSkillPublisher(self.module.server, skill, self.skill_producer).init())
            self.skill_monitoring_publisher.append(
                await KafkaSkillMonitoringPublisher(self.module.server, skill, self.skill_monitoring_producer).init())

    async def after_module_init(self):
        await self._process_asset(self.module)
