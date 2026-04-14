from __future__ import annotations

import structlog
from asyncua import Server

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.plugins.skill_monitoring_publisher import SkillMonitoringPublisher


class KafkaSkillMonitoringPublisher(SkillMonitoringPublisher):
    """ Publishes all data from the SkillPublisher to Kafka. """

    logger = structlog.getLogger("sf.server.plugins.kafka")

    def __init__(self, ua_server: Server, skill: BaseSkill, kafka_producer):
        super().__init__(ua_server, skill)
        self.kafka_producer = kafka_producer

    async def publish(self, value_dict):
        self.kafka_producer.publish(self._skill.name, value=value_dict)
