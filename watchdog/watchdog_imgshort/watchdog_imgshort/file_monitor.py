import logging
import time

from watchdog.observers import Observer

from . import __logger__

logger = logging.getLogger(__logger__)


class Watchdog:

    def __init__(self, directory, handler):
        self._observer = Observer()
        self._handler = handler
        self._directory = directory

    def run(self):
        self._observer.schedule(
            self._handler, self._directory, recursive=False
        )
        self._observer.start()
        logger.debug(f'Observer Running in {self._directory}')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self._observer.stop()
        self._observer.join()
        logger.debug('Observer Terminated')
