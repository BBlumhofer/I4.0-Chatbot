from __future__ import annotations

import datetime
import json

import structlog
from asyncua import Server

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.plugins.skill_monitoring_publisher import SkillMonitoringPublisher


class CsvSkillMonitoringPublisher(SkillMonitoringPublisher):
    """ Publishes all data from the SkillPublisher to CSV. """

    logger = structlog.getLogger("sf.server.plugins.csv")

    def __init__(self, ua_server: Server, skill: BaseSkill, csv_writer):
        super().__init__(ua_server, skill)
        self.csv_writer = csv_writer

    async def publish(self, value_dict):
        self.csv_writer.writerow([ datetime.datetime.now().timestamp(), self._skill.name, json.dumps(value_dict)])

