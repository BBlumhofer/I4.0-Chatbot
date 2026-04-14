from __future__ import annotations

import csv
import logging
from typing import List

import structlog

from pyuaadapter.server.base_module import BaseModule
from pyuaadapter.server.plugins.base_plugin import BasePlugin

from .csv_skill_monitoring_publisher import CsvSkillMonitoringPublisher
from .csv_skill_publisher import CsvSkillPublisher


class Plugin(BasePlugin):
    """ This plugin provides automatic module and skill data recording to csv files. """
    logger = structlog.getLogger("sf.server.plugins.csv")
    module: BaseModule

    skill_publisher: List[CsvSkillPublisher] = []
    skill_monitor_publisher: List[CsvSkillMonitoringPublisher] = []

    @property
    def is_enabled(self) -> bool:
        return hasattr(self.config, "CSV_ENABLE") and self.config.CSV_ENABLE

    async def init(self, module: BaseModule) -> None:
        self.module = module

        self.skill_csv_file = open(self.config.CSV_SKILL_FILENAME, 'w', newline='')
        self.skill_csv_writer = csv.writer(self.skill_csv_file, quotechar="'")
        self.skill_csv_writer.writerow(["timestamp", "name", "value"])  # write header

        self.logger.setLevel(logging.DEBUG if self.config.DEBUG else logging.INFO)

        # TODO module producer

    def writerow(self, row: list) -> None:
        self.skill_csv_writer.writerow(row)
        self.skill_csv_file.flush()  # otherwise data might not be writen in certain cases

    async def _process_asset(self, asset: 'BaseAsset'):
        await self._add_skills(asset.skills)
        for name, subcomponent in asset.components.items():
            self.logger.info(f"Processing subcomponent {name}...")
            await self._process_asset(subcomponent)

    async def _add_skills(self, skills: dict[str, 'BaseSkill']):
        for name, skill in skills.items():
            self.logger.info(f"Adding SkillPublisher for Skill '{name}'...")
            self.skill_publisher.append(
                await CsvSkillPublisher(self.module.server, skill, self).init())
            self.skill_monitor_publisher.append(
                await CsvSkillMonitoringPublisher(self.module.server, skill, self).init())

    async def after_module_init(self):
        await self._process_asset(self.module)
