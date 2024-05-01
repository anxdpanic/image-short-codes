import json
import os


class BaseNotifier:
    @staticmethod
    def description(shortcode, shortcode_url):
        return f'Shortcode "{shortcode}" created for filename, and is now available at {shortcode_url}'

    @staticmethod
    def _load_json(filename):
        if not os.path.isfile(filename):
            return {}

        with open(filename, 'r') as _file:
            return json.load(_file)

    @staticmethod
    def _save_json(filename, data):
        with open(filename, 'w') as _file:
            json.dump(data, _file)

    def notify(self, shortcode, image_url, image_filename, description):
        raise NotImplemented

    def edit(self, shortcode, image_url, image_filename, description):
        raise NotImplemented

    def delete(self, shortcode):
        raise NotImplemented
