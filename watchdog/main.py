import json
import logging
import os
import sys
import time

import argparse
import paramiko
import shortuuid
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
console_format = logging.Formatter('%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s')
console_handler = logging.StreamHandler()
console_handler.setFormatter(console_format)
logger.addHandler(console_handler)

REQUIRED_SETTINGS = ['host', 'port', 'username', 'password', 'local', 'remote']


def load_settings(filename):
    if os.path.isfile(filename):
        with open(filename, 'r') as settings_file:
            payload = json.load(settings_file)

        for setting in REQUIRED_SETTINGS:
            if setting not in payload.keys():
                logger.error(f'Required setting "{setting}" missing in {filename}')
                return None

        return payload

    return None


def generate_shortcode():
    return shortuuid.uuid()[:8]


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
            logger.info('SFTP session connected')

    def put(self, filename, remote_path):
        self.connect()
        shortcode = generate_shortcode()
        remote_filename = '/'.join([remote_path, os.path.basename(filename)])
        logger.info(f'Uploading {filename} to {remote_filename} with {shortcode}')
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
        logger.info(f'Removing {remote_filename}')
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
        logger.info(f'Renaming {old_filename} to {remote_filename}')
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
            logger.info('SFTP session terminated')


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
        logger.info(f'Observer Running in {self.directory}')
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()
        logger.info('Observer Terminated')


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

    def on_any_event(self, event):
        if event.is_directory:
            return

        logger.info(f'File event occurred:\n\t{event}')

        if event.event_type == 'created':
            self.sftp.put(event.src_path, self.connection_details['remote'])
        elif event.event_type == 'modified':
            self.sftp.put(event.src_path, self.connection_details['remote'])
        elif event.event_type == 'moved':
            self.sftp.rename(event.src_path, event.dest_path, self.connection_details['remote'])
        elif event.event_type == 'deleted':
            self.sftp.remove(event.src_path, self.connection_details['remote'])

    def __del__(self):
        self.sftp.disconnect()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-i', '--host', help='SFTP server hostname/ip')
    parser.add_argument('-p', '--port', help='SFTP server port', type=int)
    parser.add_argument('-u', '--username', help='SFTP username')
    parser.add_argument('-x', '--password', help='SFTP password')
    parser.add_argument('-s', '--local', help='Local directory to monitor')
    parser.add_argument('-d', '--remote', help='Remote directory to keep in sync')
    parser.add_argument('-f', '--settings',
                        help='Path to settings file. If set, this will be used in place of supplied arguments.')
    parsed_args = parser.parse_args()

    settings = None
    if parsed_args.settings:
        settings = load_settings(parsed_args.settings)

    if settings:
        logger.info(
            f'Watchdog is running with:\n\t'
            f'host: {settings["host"]}\n\t'
            f'port: {settings["port"]}\n\t'
            f'username: {settings["username"]}\n\t'
            f'local directory: {settings["local"]}\n\t'
            f'remote directory: {settings["remote"].rstrip("/")}'
        )

        connection_details = {
            'host': settings['host'],
            'port': int(settings['port']),
            'username': settings['username'],
            'password': settings['password'],
            'local': settings['local'].replace('\\\\', '\\'),
            'remote': settings['remote'].rstrip('/')
        }
    else:
        for setting in REQUIRED_SETTINGS:
            if not hasattr(parsed_args, setting):
                logger.error(f'Missing required argument "--{setting}" or "-f/--settings"')
                sys.exit()

            if hasattr(parsed_args, setting) and not getattr(parsed_args, setting):
                logger.error(f'Missing required argument "--{setting}" or "-f/--settings"')
                sys.exit()

        logger.info(
            f'Watchdog is running with:\n\t'
            f'host: {parsed_args.host}\n\t'
            f'port: {parsed_args.port}\n\t'
            f'username: {parsed_args.username}\n\t'
            f'local directory: {parsed_args.local}\n\t'
            f'remote directory: {parsed_args.remote.rstrip("/")}'
        )

        connection_details = {
            'host': parsed_args.host,
            'port': parsed_args.port,
            'username': parsed_args.username,
            'password': parsed_args.password,
            'local': parsed_args.local,
            'remote': parsed_args.remote.rstrip('/')
        }

    watchdog = Watchdog(
        connection_details['local'],
        FileMonitorHandler(
            patterns=['*.jpg', '*.jpeg', '*.png', '*.gif', '*.bmp', '*.webp'],
            ignore_directories=True,
            connection_details=connection_details
        )
    )
    watchdog.run()
