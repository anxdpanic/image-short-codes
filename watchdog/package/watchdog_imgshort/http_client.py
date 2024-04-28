import json
import logging
from urllib.request import Request, urlopen

from . import __logger__

logger = logging.getLogger(__logger__)


# noinspection PyPep8Naming
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
