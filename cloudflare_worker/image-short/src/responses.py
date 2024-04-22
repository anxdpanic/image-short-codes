from static.message import message_template

from js import Response


def message_response(title, message):
    message_body = message_template
    for key, value in locals().items():
        message_body = message_body.replace(f'%%{key}%%', value)

    return message_body


class Responses:
    @staticmethod
    def status_400():
        payload = message_response('Error', 'Invalid Request')
        response = Response.new(payload, {'status': 400})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_404():
        payload = message_response('Error', 'Not Found')
        response = Response.new(payload, {'status': 404})
        response.headers.set('Content-Type', 'text/html')
        return response

    @staticmethod
    def status_500():
        payload = message_response('Error', 'Failed to create table in database')
        response = Response.new(payload, {'status': 500})
        response.headers.set('Content-Type', 'text/html')
        return response
