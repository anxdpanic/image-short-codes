import json
import logging
import os
import sys
import time

from pathlib import Path
from urllib.request import Request, urlopen

import argparse
import paramiko
import shortuuid

from discord_webhook import DiscordWebhook, DiscordEmbed
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler

logging.basicConfig(
    filename='debug.log',
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger('Watchdog')

REQUIRED_SETTINGS = ['host', 'port', 'username', 'password', 'local', 'remote',
                     'worker_url', 'worker_psk']


def load_settings(filename):
    if not os.path.isfile(filename):
        logger.error(f'Settings file does not exist. "{filename}"')
        return None

    with open(filename, 'r') as settings_file:
        payload = json.load(settings_file)

    for setting in REQUIRED_SETTINGS:
        if setting not in payload.keys():
            logger.error(f'Required setting "{setting}" missing in {filename}')
            return None

    return payload


def generate_shortcode():
    return shortuuid.uuid()[:8]


def notify_discord(webhook_url, webhook_name, shortcode, image_url, image_filename, description):
    webhook = DiscordWebhook(url=webhook_url, username=webhook_name, rate_limit_retry=True)
    embed = DiscordEmbed(title="Shortcode Update", description=description, color="03b2f8")

    embed.set_author(name=webhook_name, icon_url=image_url)

    embed.set_image(url=image_url)
    embed.set_thumbnail(url=image_url)

    embed.set_timestamp()

    embed.add_embed_field(name="Shortcode", value=shortcode)
    embed.add_embed_field(name="Image", value=image_filename)

    webhook.add_embed(embed)
    logger.debug('Notifying Discord')
    response = webhook.execute()
    logger.debug(f'Discord Response: {response.status_code}')


class HTTPRequest:
    def __init__(self, worker_url, worker_psk):
        self.worker_url = worker_url
        self.worker_psk = worker_psk
        self.auth_header = 'X-Auth-PSK'
        self.user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                           'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

    def POST(self, data):
        data = json.dumps(data)
        data = str(data)
        data = data.encode('utf-8')
        request = Request(self.worker_url, data=data, method='POST')
        request.add_header(self.auth_header, self.worker_psk)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Referrer', self.worker_url)
        request.add_header('User-Agent', self.user_agent)

        logger.debug(f'POST request: {data.decode("utf-8")}')
        with urlopen(request) as response:
            status_code = response.status
            if status_code == 200 and 'application/json' in response.headers.get('Content-Type'):
                payload = json.loads(response.read().decode('utf-8'))
                logger.debug(f'POST response: {payload}')
                return payload

        logger.debug(f'POST response: {status_code}')
        return None

    def PUT(self, data):
        data = json.dumps(data)
        data = str(data)
        data = data.encode('utf-8')
        request = Request(self.worker_url, data=data, method='PUT')
        request.add_header(self.auth_header, self.worker_psk)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Referrer', self.worker_url)
        request.add_header('User-Agent', self.user_agent)

        logger.debug(f'PUT request: {data.decode("utf-8")}')
        with urlopen(request) as response:
            logger.debug(f'PUT response: {response.status}')

    def DELETE(self, shortcode):
        request = Request(f'{self.worker_url}/{shortcode}', method='DELETE')
        request.add_header(self.auth_header, self.worker_psk)
        request.add_header('Referrer', self.worker_url)
        request.add_header('User-Agent', self.user_agent)

        logger.debug(f'DELETE request: {shortcode}')
        with urlopen(request) as response:
            logger.debug(f'DELETE response: {response.status}')


class SFTP:
    def __init__(self, host, user, password, port=22, **kwargs):
        self.host = host.rstrip('/')
        self.username = user
        self.password = password
        self.port = port
        self.connection = None
        self.transport = None
        for key, value in kwargs.items():
            setattr(self, key, value)

    def connect(self):
        if self.connection is None:
            if self.transport is not None:
                self.transport.close()
            self.transport = paramiko.Transport((self.host, self.port))
            self.transport.connect(username=self.username, password=self.password)
            self.connection = paramiko.SFTPClient.from_transport(self.transport)
            logger.debug('SFTP session connected')

    def put(self, filename, remote_path):
        self.connect()
        remote_filename = '/'.join([remote_path, os.path.basename(filename)])
        logger.debug(f'Uploading {filename} to {remote_filename}')
        try:
            self.connection.put(filename, remote_filename)
        except FileNotFoundError:
            logger.error('File not found')
        except PermissionError:
            logger.error('Permission denied uploading file')
        except OSError:
            logger.error('Failure')

    def remove(self, filename, remote_path):
        self.connect()
        remote_filename = '/'.join([remote_path, os.path.basename(filename)])
        logger.debug(f'Removing {remote_filename}')
        try:
            self.connection.remove(remote_filename)
        except FileNotFoundError:
            logger.error('File not found on SFTP server')
        except PermissionError:
            logger.error('Permission denied removing file')
        except OSError:
            logger.error('Failure')

    def rename(self, filename, new_filename, remote_path):
        self.connect()
        remote_filename = '/'.join([remote_path, os.path.basename(new_filename)])
        old_filename = '/'.join([remote_path, os.path.basename(filename)])
        logger.debug(f'Renaming {old_filename} to {remote_filename}')
        try:
            self.connection.rename(old_filename, remote_filename)
        except FileNotFoundError:
            logger.error('File not found')
        except PermissionError:
            logger.error('Permission denied uploading file')
        except OSError:
            logger.error('Failure')

    def disconnect(self):
        if self.connection is not None:
            self.connection.close()
            self.transport.close()
            self.connection = None
            self.transport = None
            logger.debug('SFTP session terminated')


class Watchdog:

    def __init__(self, directory, handler):
        self.observer = Observer()
        self.handler = handler
        self.directory = directory

    def run(self):
        self.observer.schedule(
            self.handler, self.directory, recursive=False
        )
        self.observer.start()
        logger.debug(f'Observer Running in {self.directory}')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
        logger.debug('Observer Terminated')


class FileMonitorHandler(PatternMatchingEventHandler):
    def __init__(self, *args, **kwargs):
        self.connection_details = kwargs.pop('connection_details')
        super(FileMonitorHandler, self).__init__(*args, **kwargs)

        self.sftp = SFTP(
            host=self.connection_details['host'],
            user=self.connection_details['username'],
            password=self.connection_details['password'],
            port=self.connection_details['port']
        )

        self.request = HTTPRequest(self.connection_details['worker_url'], self.connection_details['worker_psk'])

    def on_any_event(self, event):
        if event.is_directory:
            return

        logger.debug(f'File event occurred:\n\t{event}')

        if event.event_type == 'modified':
            data = self.request.POST({'shortcode': Path(event.src_path).name})
            if not data:
                data = {}
            shortcode = data.get('shortcode')
            if not shortcode:
                logger.debug(f'No shortcode for {event.src_path}')
                shortcode = generate_shortcode()
                filename = Path(event.src_path).name
                remote_filename = '/'.join([self.connection_details['worker_url'], shortcode])

                self.request.POST({'shortcode': shortcode, 'image': filename})
                self.sftp.put(event.src_path, self.connection_details['remote'])
                logger.info(f'{filename} is uploaded to {remote_filename}')

                if 'discord_webhook' in self.connection_details and 'webhook_name' in self.connection_details:
                    notify_discord(
                        self.connection_details['discord_webhook'],
                        self.connection_details['webhook_name'],
                        shortcode,
                        remote_filename,
                        filename,
                        f'Shortcode "{shortcode}" created for filename, '
                        f'and is now available at {remote_filename}'
                    )
                return

            self.request.PUT({'shortcode': shortcode, 'image': Path(event.src_path).name})
            self.sftp.put(event.src_path, self.connection_details['remote'])
        elif event.event_type == 'moved':
            data = self.request.POST({'shortcode': Path(event.src_path).name})
            if not data:
                data = {}

            shortcode = data.get('shortcode')
            if not shortcode:
                logger.error(f'No shortcode for {event.src_path}')
                return

            self.request.PUT({'shortcode': shortcode, 'image': Path(event.dest_path).name})
            self.sftp.rename(event.src_path, event.dest_path, self.connection_details['remote'])
        elif event.event_type == 'deleted':
            data = self.request.POST({'shortcode': Path(event.src_path).name})
            if not data:
                data = {}

            shortcode = data.get('shortcode')
            if not shortcode:
                logger.error(f'No shortcode for {event.src_path}')
                return

            self.request.DELETE(shortcode)
            self.sftp.remove(event.src_path, self.connection_details['remote'])

    def __del__(self):
        self.sftp.disconnect()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-f', '--settings', help='Path to settings file', default='config.json')
    parsed_args = parser.parse_args()

    settings = None
    if parsed_args.settings:
        settings = load_settings(parsed_args.settings)

    if not settings:
        logger.error('Failed to load settings')
        sys.exit()

    logger.info(
        f'Watchdog is running with:\n\t'
        f'host: {settings["host"]}\n\t'
        f'port: {settings["port"]}\n\t'
        f'username: {settings["username"]}\n\t'
        f'local directory: {settings["local"]}\n\t'
        f'remote directory: {settings["remote"].rstrip("/")}\n\t'
        f'worker url: {settings["worker_url"].rstrip("/")}\n\t'
        f'webhook name: {settings["webhook_name"]}\n\t'
        f'debug: {settings.get("debug", False)}'
    )

    connection_details = {
        'host': settings['host'],
        'port': int(settings['port']),
        'username': settings['username'],
        'password': settings['password'],
        'local': settings['local'].replace('\\\\', '\\'),
        'remote': settings['remote'].rstrip('/'),
        'worker_url': settings['worker_url'].rstrip('/'),
        'worker_psk': settings['worker_psk'],
        'webhook_name': settings.get('webhook_name', ''),
        'discord_webhook': settings.get('discord_webhook', '')
    }

    if settings.get('debug', False):
        logger.setLevel(level=logging.DEBUG)
        console_format = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    watchdog = Watchdog(
        connection_details['local'],
        FileMonitorHandler(
            patterns=['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp'],
            ignore_directories=True,
            connection_details=connection_details
        )
    )
    watchdog.run()


if __name__ == '__main__':
    main()
