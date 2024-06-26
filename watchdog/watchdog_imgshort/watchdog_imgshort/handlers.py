import hashlib
import logging
from pathlib import Path

import shortuuid
from watchdog.events import PatternMatchingEventHandler

from . import __logger__
from .http_client import HTTPRequest
from .notifiers.discord import Discord
from .sftp_client import SFTP

logger = logging.getLogger(__logger__)


class ImageHandler(PatternMatchingEventHandler):
    def __init__(self, settings):
        self._settings = settings
        super(ImageHandler, self).__init__(
            patterns=['*.webp', '*.jpg', '*.jpeg', '*.png', '*.apng', '*.gif', '*.svg',
                      '*.bmp', '*.ico', '*.tiff', '*.pdf', '*.jpg2', '*.jxr'],
            ignore_directories=True
        )

        self._sftp = SFTP(
            host=self._settings['sftp']['host'],
            user=self._settings['sftp']['username'],
            password=self._settings['sftp']['password'],
            port=self._settings['sftp']['port']
        )

        self._request = HTTPRequest(self._settings['cloudflare']['worker_url'],
                                    self._settings['cloudflare']['worker_psk'])

        self._notifiers = []

    @staticmethod
    def _generate_shortcode():
        return shortuuid.uuid()[:8]

    def _get_shortcode(self, filename_and_path):
        data = self._request.POST({'shortcode': Path(filename_and_path).name})
        if not data:
            data = {}

        shortcode = data.get('shortcode')
        if not shortcode:
            logger.error(f'No shortcode for {filename_and_path}')
            return None

        return shortcode

    def _enabled_notifier(self, notifier_class):
        for notifier in self._notifiers:
            if isinstance(notifier, notifier_class):
                return True
        return False

    def _enable_notifiers(self):
        if 'discord' in self._settings and 'webhook' in self._settings['discord']:
            if not self._enabled_notifier(Discord):
                self._notifiers.append(
                    Discord(
                        self._settings['discord']['webhook'],
                        self._settings['discord'].get('author', 'Shortcode Notifier'),
                        self._settings['discord'].get('author_icon'),
                        self._settings['discord'].get('embed_title', 'Shortcode Update'),
                        self._settings['discord'].get('embed_color', '03b2f8')
                    )
                )

    def _send_notifications(self, shortcode, shortcode_url, filename):
        self._enable_notifiers()
        for notifier in self._notifiers:
            notifier.notify(
                shortcode,
                shortcode_url,
                filename,
                notifier.description(shortcode, shortcode_url)
            )

    def _edit_notifications(self, shortcode, shortcode_url, filename):
        self._enable_notifiers()
        for notifier in self._notifiers:
            notifier.edit(
                shortcode,
                shortcode_url,
                filename,
                notifier.description(shortcode, shortcode_url)
            )

    def _delete_notifications(self, shortcode):
        self._enable_notifiers()
        for notifier in self._notifiers:
            notifier.delete(shortcode)

    def on_any_event(self, event):
        if event.is_directory:
            return

        event_hash = hashlib.md5(event.__str__().encode('utf-8')).hexdigest()
        logger.debug(f'File event occurred:\n\tevent: {event}\n\thash: {event_hash}')

        if event.event_type == 'modified':
            shortcode = self._get_shortcode(event.src_path)
            filename = Path(event.src_path).name

            if not shortcode:
                logger.debug(f'No shortcode for {event.src_path}')
                shortcode = self._generate_shortcode()
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.POST({'shortcode': shortcode, 'image': filename})
                self._sftp.put(event.src_path, self._settings['sftp']['remote_path'])
                logger.info(f'{filename} is uploaded to {shortcode_url}')

                logger.info(f'Sending notifications')
                self._send_notifications(shortcode, shortcode_url, filename)

            else:
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.PUT({'shortcode': shortcode, 'image': Path(event.src_path).name})
                self._sftp.put(event.src_path, self._settings['sftp']['remote_path'])
                logger.info(f'{filename} is uploaded to {shortcode_url}')

        elif event.event_type == 'moved':
            shortcode = self._get_shortcode(event.src_path)
            filename = Path(event.dest_path).name
            old_filename = Path(event.src_path).name

            if not shortcode:
                logger.debug(f'No shortcode for {event.src_path}')
                shortcode = self._generate_shortcode()
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.POST({'shortcode': shortcode, 'image': filename})
                self._sftp.put(event.dest_path, self._settings['sftp']['remote_path'])
                logger.info(f'{filename} is uploaded to {shortcode_url}')

                logger.info(f'Sending notifications')
                self._send_notifications(shortcode, shortcode_url, filename)
            else:
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.PUT({'shortcode': shortcode, 'image': filename})
                self._sftp.rename(event.src_path, event.dest_path, self._settings['sftp']['remote_path'])
                logger.info(f'Moved {old_filename} to {filename}')

                logger.info(f'Editing notifications')
                self._edit_notifications(shortcode, shortcode_url, filename)

        elif event.event_type == 'deleted':
            shortcode = self._get_shortcode(event.src_path)
            if shortcode:
                self._request.DELETE(shortcode)
                self._sftp.remove(event.src_path, self._settings['sftp']['remote_path'])
                logger.info(f'Deleted {Path(event.src_path).name}')

                logger.info(f'Deleting notifications')
                self._delete_notifications(shortcode)

        logger.debug(f'Response to file event completed.\n\thash: {event_hash}')

    def __del__(self):
        self._sftp.disconnect()
