import os
import time
from pathlib import Path
from typing import List

from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)


class TempDirCleaner:

    def __init__(self, dir_paths: List[Path], age_limit_seconds: int = 3600, interval_minutes: int = 10):
        self.dir_paths = dir_paths
        self.age_limit_seconds = age_limit_seconds
        self.interval_minutes = interval_minutes
        self.scheduler = BackgroundScheduler()

        # create the directories if they do not exist
        for dir_path in self.dir_paths:
            dir_path.mkdir(parents=True, exist_ok=True)

        # perform initial cleanup
        self.cleanup()

    def cleanup(self):
        now = time.time()
        for dir_path in self.dir_paths:
            for filename in os.listdir(dir_path):
                file_path = dir_path / filename
                if file_path.is_file():
                    file_age = now - file_path.stat().st_mtime
                    if file_age > self.age_limit_seconds:
                        os.remove(file_path)
                        logger.info('Removed %s', file_path)

    def start(self):
        self.scheduler.add_job(self.cleanup, 'interval', minutes=self.interval_minutes)
        self.scheduler.start()
        logger.info('Started temp dir cleaner with interval %d minutes', self.interval_minutes)

    def stop(self):
        self.scheduler.shutdown()
        logger.info('Stopped temp dir cleaner')
