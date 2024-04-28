import argparse
import logging
import logging.handlers
import os
import shutil

from . import __logger__
from .config import Config
from .file_monitor import Watchdog
from .handlers import FileMonitorHandler

logger = logging.getLogger(__logger__)


def enable_logging(debug=False):
    global logger

    def _logger_configured():
        for _handler in logger.handlers:
            if isinstance(_handler, logging.handlers.RotatingFileHandler):
                return True
        return False

    logging_format = logging.Formatter(
        fmt='%(asctime)s.%(msecs)03d %(name)s %(levelname)s %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    if not _logger_configured():
        if os.path.isfile('debug.log'):
            shutil.move('debug.log', 'debug.log.1')

        logger.setLevel(level=logging.INFO)
        handler = logging.handlers.RotatingFileHandler('debug.log', maxBytes=5242880, backupCount=1)
        handler.setFormatter(logging_format)
        logger.addHandler(handler)

    if debug:
        logger.setLevel(level=logging.DEBUG)
        handler = logging.StreamHandler()
        handler.setFormatter(logging_format)
        logger.addHandler(handler)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--settings', help='Path to settings file', default='config.json')
    parsed_args = parser.parse_args()

    settings = Config(parsed_args.settings).settings

    enable_logging(debug=settings.get('debug', False))

    logger.info(
        f'Watchdog is running with:\n\t'
        f'SFTP Config:\n\t\t'
        f'host:             {settings["sftp"]["host"]}\n\t\t'
        f'port:             {settings["sftp"]["port"]}\n\t\t'
        f'username:         {settings["sftp"]["username"]}\n\t\t'
        f'local directory:  {settings["sftp"]["local_path"]}\n\t\t'
        f'remote directory: {settings["sftp"]["remote_path"].rstrip("/")}\n\t'
        f'Cloudflare Config:\n\t\t'
        f'worker url:       {settings["cloudflare"]["worker_url"].rstrip("/")}\n\t'
        f'Discord Config:\n\t\t'
        f'author:           {settings["discord"]["author"]}\n\t\t'
        f'author icon:      {settings["discord"]["author_icon"]}\n\t\t'
        f'embed title:      {settings["discord"]["embed_title"]}\n\t\t'
        f'embed color:      {settings["discord"]["embed_color"]}\n\t'
        f'Debug:                    {settings.get("debug", False)}'
    )

    settings['sftp']['local_path'] = settings['sftp']['local_path'].replace('\\\\', '\\')
    settings['sftp']['remote_path'] = settings['sftp']['remote_path'].rstrip('/')
    settings["cloudflare"]['worker_url'] = settings["cloudflare"]['worker_url'].rstrip('/')

    watchdog = Watchdog(
        settings['sftp']['local_path'],
        FileMonitorHandler(
            patterns=['*.webp', '*.jpg', '*.jpeg', '*.png', '*.apng', '*.gif', '*.svg',
                      '*.bmp', '*.ico', '*.tiff', '*.pdf', '*.jpg2', '*.jxr'],
            ignore_directories=True,
            settings=settings
        )
    )
    watchdog.run()


if __name__ == '__main__':
    main()
