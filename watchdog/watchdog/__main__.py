import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen

import paramiko
import shortuuid
from discord_webhook import DiscordWebhook, DiscordEmbed
from jsonschema import validate
from watchdog.events import PatternMatchingEventHandler
from watchdog.observers import Observer

logging.basicConfig(
    filename='debug.log',
    filemode='a',
    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
    datefmt='%H:%M:%S',
    level=logging.INFO
)

logger = logging.getLogger('Watchdog')


def load_json(filename):
    if not os.path.isfile(filename):
        return {}

    with open(filename, 'r') as _file:
        return json.load(_file)


def save_json(filename, data):
    with open(filename, 'w') as _file:
        json.dump(data, _file)


def load_settings(filename):
    schema = {
        "$schema": "http://json-schema.org/schema#",
        "type": "object",
        "properties": {
            "sftp": {
                "type": "object",
                "properties": {
                    "host": {
                        "type": "string"
                    },
                    "port": {
                        "type": "integer"
                    },
                    "username": {
                        "type": "string"
                    },
                    "password": {
                        "type": "string"
                    },
                    "local_path": {
                        "type": "string"
                    },
                    "remote_path": {
                        "type": "string"
                    }
                },
                "required": [
                    "host",
                    "local_path",
                    "password",
                    "port",
                    "remote_path",
                    "username"
                ]
            },
            "cloudflare": {
                "type": "object",
                "properties": {
                    "worker_url": {
                        "type": "string"
                    },
                    "worker_psk": {
                        "type": "string"
                    }
                },
                "required": [
                    "worker_psk",
                    "worker_url"
                ]
            },
            "discord": {
                "type": "object",
                "properties": {
                    "webhook": {
                        "type": "string"
                    },
                    "author": {
                        "type": "string"
                    },
                    "author_icon": {
                        "type": "string"
                    },
                    "embed_title": {
                        "type": "string"
                    },
                    "embed_color": {
                        "type": "string"
                    }
                },
                "required": [
                    "webhook"
                ]
            },
            "debug": {
                "type": "boolean"
            }
        },
        "required": [
            "cloudflare",
            "sftp"
        ]
    }

    if not os.path.isfile(filename):
        logger.error(f'Settings file does not exist. "{filename}"')
        return None

    payload = load_json(filename)

    validate(instance=payload, schema=schema)

    return payload


def generate_shortcode():
    return shortuuid.uuid()[:8]


class Discord:
    def __init__(self, webhook, author, author_icon, embed_title, embed_color):
        self._url = webhook
        self._name = author
        self._icon = author_icon
        self._title = embed_title
        self._color = embed_color
        self._id_file = 'webhook_ids.json'
        self._webhook_ids = load_json(self._id_file)

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def title(self):
        return self._title

    @property
    def color(self):
        return self._color

    @property
    def ids(self):
        return self._webhook_ids

    def notify(self, shortcode, image_url, image_filename, description):
        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        embed = DiscordEmbed(title=self.title, description=description, color=self.color)

        embed.set_author(name=self.name, icon_url=self.icon)

        embed.set_image(url=image_url)
        embed.set_thumbnail(url=image_url)

        embed.set_timestamp()

        embed.add_embed_field(name="Shortcode", value=shortcode)
        embed.add_embed_field(name="Image", value=image_filename)

        webhook.add_embed(embed)
        logger.debug('Notifying Discord')
        response = webhook.execute()
        logger.debug(f'Discord response: {response.status_code}')
        logger.debug(f'Discord webhook id: {webhook.id}')

        if webhook.id:
            self.ids[shortcode] = webhook.id
            save_json(self._id_file, self.ids)
            logger.debug(f'Discord webhook ids updated with {webhook.id} for {shortcode}')

    def edit(self, shortcode, image_url, image_filename, description):
        if shortcode not in self.ids.keys():
            logger.debug(f'Discord webhook id for {shortcode} not found')
            return

        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        embed = DiscordEmbed(title=self.title, description=description, color=self.color)

        webhook.id = self.ids[shortcode]

        embed.set_author(name=self.name, icon_url=self.icon)

        embed.set_image(url=image_url)
        embed.set_thumbnail(url=image_url)

        embed.set_timestamp()

        embed.add_embed_field(name="Shortcode", value=shortcode)
        embed.add_embed_field(name="Image", value=image_filename)

        webhook.add_embed(embed)
        logger.debug(f'Editing Discord webhook id {webhook.id}')
        response = webhook.edit()
        logger.debug(f'Discord response: {response.status_code}')

    def delete(self, shortcode):
        if shortcode not in self.ids.keys():
            logger.debug(f'Discord webhook id for {shortcode} not found')
            return

        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        webhook.id = self.ids[shortcode]
        logger.debug(f'Deleting Discord webhook id {webhook.id}')
        response = webhook.delete()
        logger.debug(f'Discord response: {response.status_code} Id: {webhook.id}')
        if 200 <= response.status_code < 300:
            del self.ids[shortcode]
            save_json(self._id_file, self.ids)
            logger.debug(f'Discord webhook id removed {webhook.id} for {shortcode}')


class HTTPRequest:
    def __init__(self, worker_url, worker_psk):
        self._worker_url = worker_url
        self._worker_psk = worker_psk
        self._auth_header = 'X-Auth-PSK'
        self._user_agent = ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')

    @staticmethod
    def _encode_request_data(data):
        data = json.dumps(data)
        data = str(data)
        return data.encode('utf-8')

    def POST(self, data):
        data = self._encode_request_data(data)
        request = Request(self._worker_url, data=data, method='POST')
        request.add_header(self._auth_header, self._worker_psk)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Referrer', self._worker_url)
        request.add_header('User-Agent', self._user_agent)

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
        data = self._encode_request_data(data)
        request = Request(self._worker_url, data=data, method='PUT')
        request.add_header(self._auth_header, self._worker_psk)
        request.add_header('Content-Type', 'application/json')
        request.add_header('Referrer', self._worker_url)
        request.add_header('User-Agent', self._user_agent)

        logger.debug(f'PUT request: {data.decode("utf-8")}')
        with urlopen(request) as response:
            logger.debug(f'PUT response: {response.status}')

    def DELETE(self, shortcode):
        request = Request(f'{self._worker_url}/{shortcode}', method='DELETE')
        request.add_header(self._auth_header, self._worker_psk)
        request.add_header('Referrer', self._worker_url)
        request.add_header('User-Agent', self._user_agent)

        logger.debug(f'DELETE request: {shortcode}')
        with urlopen(request) as response:
            logger.debug(f'DELETE response: {response.status}')


class SFTP:
    def __init__(self, host, user, password, port=22, **kwargs):
        self._host = host.rstrip('/')
        self._port = port
        self._username = user
        self._password = password
        self._connection = None
        self._transport = None
        for key, value in kwargs.items():
            setattr(self, key, value)

        self._idle_timestamp_default = -1.0
        self._idle_timestamp = self._idle_timestamp_default

    @property
    def host(self):
        return self._host

    @property
    def port(self):
        return self._port

    @property
    def username(self):
        return self._username

    @property
    def connection(self):
        return self._connection

    @connection.setter
    def connection(self, value):
        self._connection = value

    @connection.deleter
    def connection(self):
        if self.connection:
            self.connection.close()
        self._connection = None

    @property
    def timestamp(self):
        return self._idle_timestamp

    @timestamp.setter
    def timestamp(self, value):
        if value == 'now':
            self._idle_timestamp = time.monotonic()
        else:
            del self.timestamp

    @timestamp.deleter
    def timestamp(self):
        self._idle_timestamp = self._idle_timestamp_default

    def connect(self, reconnect=False):
        if reconnect:
            logger.debug('SFTP session reconnecting')
            self.disconnect()
            del self.timestamp

        if self.timestamp == self._idle_timestamp_default:
            self.timestamp = 'now'
        else:
            old_timestamp = self.timestamp
            self.timestamp = 'now'
            running_minutes, running_seconds = divmod(self.timestamp - old_timestamp, 60)
            logger.debug(f'SFTP has been idle for {int(running_minutes)} minutes and {int(running_seconds)} seconds')
            if int(running_minutes) >= 5:
                self.disconnect()
                del self.timestamp

        if self.connection is None:
            for retry in range(5):
                try:
                    logger.debug('SFTP attempting to connect')
                    if self._transport is not None:
                        self._transport.close()
                    self._transport = paramiko.Transport((self.host, self.port))
                    self._transport.set_keepalive(5)
                    self._transport.connect(username=self.username, password=self._password)
                    break
                except (ConnectionError, EOFError):
                    if retry < 4:
                        logger.error('SFTP connection failed, retrying in 5 seconds')
                        time.sleep(5)
                    else:
                        raise

            self.connection = paramiko.SFTPClient.from_transport(self._transport)
            logger.debug('SFTP session connected')

    def put(self, filename, remote_path):
        self.connect()
        remote_filename = '/'.join([remote_path, os.path.basename(filename)])
        logger.debug(f'Uploading {filename} to {remote_filename}')
        try:
            self.connection.put(filename, remote_filename)
            if self._transport.get_exception():
                self.connect(reconnect=True)
                self.connection.put(filename, remote_filename)
            self.timestamp = 'now'
        except ConnectionError:
            self.connect(reconnect=True)
            self.connection.put(filename, remote_filename)
            self.timestamp = 'now'
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
            if self._transport.get_exception():
                self.connect(reconnect=True)
                self.connection.remove(remote_filename)
            self.timestamp = 'now'
        except ConnectionError:
            self.connect(reconnect=True)
            self.connection.remove(remote_filename)
            self.timestamp = 'now'
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
            if self._transport.get_exception():
                self.connect(reconnect=True)
                self.connection.rename(old_filename, remote_filename)
            self.timestamp = 'now'
        except ConnectionError:
            self.connect(reconnect=True)
            self.connection.rename(old_filename, remote_filename)
            self.timestamp = 'now'
        except FileNotFoundError:
            logger.error('File not found')
        except PermissionError:
            logger.error('Permission denied uploading file')
        except OSError:
            logger.error('Failure')

    def disconnect(self):
        if self.connection is not None:
            self._transport.close()
            self._transport = None
            del self.connection
            logger.debug('SFTP session terminated')


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


class FileMonitorHandler(PatternMatchingEventHandler):
    def __init__(self, *args, **kwargs):
        self._settings = kwargs.pop('settings')
        super(FileMonitorHandler, self).__init__(*args, **kwargs)

        self._sftp = SFTP(
            host=self._settings['sftp']['host'],
            user=self._settings['sftp']['username'],
            password=self._settings['sftp']['password'],
            port=self._settings['sftp']['port']
        )

        self._request = HTTPRequest(self._settings['cloudflare']['worker_url'],
                                    self._settings['cloudflare']['worker_psk'])

        self._discord = None
        if 'discord' in self._settings and 'webhook' in self._settings['discord']:
            self._discord = Discord(
                self._settings['discord']['webhook'],
                self._settings['discord'].get('author', 'Shortcode Notifier'),
                self._settings['discord'].get('author_icon', 'webhook-author.png'),
                self._settings['discord'].get('embed_title', 'Shortcode Update'),
                self._settings['discord'].get('embed_color', '03b2f8')
            )

    def _get_shortcode(self, filename_and_path):
        data = self._request.POST({'shortcode': Path(filename_and_path).name})
        if not data:
            data = {}

        shortcode = data.get('shortcode')
        if not shortcode:
            logger.error(f'No shortcode for {filename_and_path}')
            return None

        return shortcode

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
                shortcode = generate_shortcode()
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.POST({'shortcode': shortcode, 'image': filename})
                self._sftp.put(event.src_path, self._settings['sftp']['remote'])
                logger.info(f'{filename} is uploaded to {shortcode_url}')

                if self._discord:
                    self._discord.notify(
                        shortcode,
                        shortcode_url,
                        filename,
                        f'Shortcode "{shortcode}" created for filename, '
                        f'and is now available at {shortcode_url}'
                    )

            else:
                shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

                self._request.PUT({'shortcode': shortcode, 'image': Path(event.src_path).name})
                self._sftp.put(event.src_path, self._settings['sftp']['remote_path'])
                logger.info(f'{filename} is uploaded to {shortcode_url}')

        elif event.event_type == 'moved':
            shortcode = self._get_shortcode(event.src_path)

            filename = Path(event.dest_path).name
            old_filename = Path(event.src_path).name
            shortcode_url = '/'.join([self._settings['cloudflare']['worker_url'], shortcode])

            self._request.PUT({'shortcode': shortcode, 'image': filename})
            self._sftp.rename(event.src_path, event.dest_path, self._settings['sftp']['remote_path'])
            logger.info(f'Moved {old_filename} to {filename}')

            if self._discord:
                self._discord.edit(
                    shortcode,
                    shortcode_url,
                    filename,
                    f'Shortcode "{shortcode}" created for filename, '
                    f'and is now available at {shortcode_url}'
                )

        elif event.event_type == 'deleted':
            shortcode = self._get_shortcode(event.src_path)

            self._request.DELETE(shortcode)
            self._sftp.remove(event.src_path, self._settings['sftp']['remote_path'])
            logger.info(f'Deleted {Path(event.src_path).name}')

            if self._discord:
                self._discord.delete(shortcode)

        logger.debug(f'Response to file event completed.\n\thash: {event_hash}')

    def __del__(self):
        self._sftp.disconnect()


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

    if settings.get('debug', False):
        logger.setLevel(level=logging.DEBUG)
        console_handler = logging.StreamHandler()
        console_format = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
        console_handler.setFormatter(console_format)
        logger.addHandler(console_handler)

    debug_space = '               '
    if __name__ != '__main__':
        debug_space += '    '

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
        f'Debug: {debug_space}{settings.get("debug", False)}'
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
