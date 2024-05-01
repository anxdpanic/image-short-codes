import json
import logging
import os

from jsonschema import validate

from . import __logger__

logger = logging.getLogger(__logger__)


class Config:
    def __init__(self, config_file):
        self._filename = config_file
        self._settings = self._load()

    @property
    def settings(self):
        return self._settings

    @property
    def schema(self):
        # noinspection HttpUrlsUsage
        return {
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

    def _validate(self, data):
        validate(data, self.schema)

    def _load(self):
        if not os.path.isfile(self._filename):
            raise FileNotFoundError(f'Settings file does not exist. "{self._filename}"')

        with open(self._filename, 'r') as _file:
            payload = json.load(_file)

        self._validate(payload)
        return payload
