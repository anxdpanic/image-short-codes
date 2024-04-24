from static.message import message_template

# noinspection PyUnresolvedReferences
from js import Response


def message_response(title, message):
    message_body = message_template
    for key, value in locals().items():
        message_body = message_body.replace(f'%%{key}%%', value)

    return message_body


class Responses:
    @staticmethod
    def status_200(json_data=None):
        body = ''
        content_type = 'text/plain'
        if json_data:
            body = json_data
            content_type = 'application/json'

        response = Response.new(body, {'status': 200})
        response.headers.set('Content-Type', content_type)
        return response

    @staticmethod
    def status_400():
        payload = message_response('Error', 'Invalid Request')
        response = Response.new(payload, {'status': 400})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_401():
        payload = message_response('Error', 'Unauthorized')
        response = Response.new(payload, {'status': 401})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_404():
        payload = message_response('Error', 'Not Found')
        response = Response.new(payload, {'status': 404})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_409():
        payload = message_response('Error', 'Conflict')
        response = Response.new(payload, {'status': 409})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_500():
        payload = message_response('Error', 'Failed to create table in database')
        response = Response.new(payload, {'status': 500})
        response.headers.set('Content-Type', 'text/html')
        return response
