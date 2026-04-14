from __future__ import annotations

import base64
import datetime
import json

import structlog
from asyncua import Server

from pyuaadapter.server.base_skill import BaseSkill
from pyuaadapter.server.plugins.skill_publisher import SkillPublisher


def json_compatible(_dict: dict) -> dict:
    """ Makes the given dictionary json-compatible by converting all bytes to base64-encoded strings. """
    ret = {}
    for key, value in _dict.items():
        if isinstance(value, dict):
            ret[key] = json_compatible(value)
        elif isinstance(value, bytes):
            ret[key] = base64.b64encode(value).decode('utf-8')
        else:
            ret[key] = value
    return ret


class CsvSkillPublisher(SkillPublisher):
    """ Publishes all data from the SkillPublisher to CSV. """

    logger = structlog.getLogger("sf.server.plugins.csv")

    def __init__(self, ua_server: Server, skill: BaseSkill, csv_writer):
        super().__init__(ua_server, skill)
        self.csv_writer = csv_writer

    async def publish(self, value_dict):
        self.csv_writer.writerow([datetime.datetime.now().timestamp(), self._skill.name,
                                  json.dumps(json_compatible(value_dict))])
