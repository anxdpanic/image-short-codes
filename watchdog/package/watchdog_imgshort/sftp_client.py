import logging
import os
import time

import paramiko

from . import __logger__

logger = logging.getLogger(__logger__)


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
