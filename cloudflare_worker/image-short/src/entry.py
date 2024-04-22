from db.schema import shortcodes_schema
from static.message import message_template

from js import Response


def message_response(title, message):
    message_body = message_template
    for key, value in locals().items():
        message_body = message_body.replace(f'%%{key}%%', value)

    return message_body


async def prepare_database(env):
    result = await env.image_db.prepare(shortcodes_schema).run()
    if not result.success:
        payload = message_response('Error', 'Failed to create table in database')
        response = Response.new(payload, {'status': 500})
        response.headers.set('Content-Type', 'text/html')
        return response


async def on_fetch(request, env):
    await prepare_database(env)
    payload = message_response('Success', 'Successful')
    response = Response.new(payload, {'status': 200})
    response.headers.set('Content-Type', 'text/html')

    return response
