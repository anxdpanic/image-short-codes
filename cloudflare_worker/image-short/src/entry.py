import json

from db import statements
from db.schema import shortcodes_schema
from responses import Responses

from js import console
from js import fetch
from js import Response

RESPONSES = Responses()


async def get_shortcode_and_filename(request):
    put_data = await request.text()
    put_data = json.loads(put_data)

    shortcode = put_data.get('shortcode')
    image_filename = put_data.get('image')

    if not shortcode or not image_filename:
        return RESPONSES.status_400()

    return shortcode, image_filename


def authenticate(request, env):
    header_value = request.headers.get('X-Auth-PSK')

    if not header_value or (header_value and header_value != env.AUTHENTICATION_TOKEN):
        return RESPONSES.status_401()


async def prepare_database(env):
    result = await env.image_db.prepare(shortcodes_schema).run()
    if not result.success:
        return RESPONSES.status_500()


async def on_fetch(request, env):
    await prepare_database(env)

    cf_url = f'{env.CF_WORKER_BASE_URL.rstrip("/")}/'
    img_url = f'{env.RAW_IMG_BASE_URL.rstrip("/")}/'

    request_url = request.url
    request_path = request_url.replace(cf_url, '')

    console.info(f'Request URL: {request_url}')
    console.info(f'Request Path: {request_path}')

    if '/' in request_path:
        return RESPONSES.status_404()

    if request.method == 'GET':
        if not request_path:
            return RESPONSES.status_404()

        result = await env.image_db.prepare(statements.select).bind(request_path).run()
        if not result.results:
            return RESPONSES.status_404()

        console.info(f'Fetching image at url: {result.results[0].url}')
        return fetch(result.results[0].url)

    elif request.method == 'POST':
        # add image entry to shortcode database
        authenticate(request, env)
        shortcode, image_filename = await get_shortcode_and_filename(request)

        result = await (env.image_db.prepare(statements.insert)
                        .bind(shortcode, img_url + image_filename).run())

        status = 200 if result.success and result.meta.changes > 0 else 500
        response = Response.new('', {'status': status})
        return response

    elif request.method == 'PUT':
        # modify image entry in shortcode database
        authenticate(request, env)
        shortcode, image_filename = await get_shortcode_and_filename(request)

        result = await (env.image_db.prepare(statements.update)
                        .bind(shortcode, img_url + image_filename).run())

        status = 200 if result.success and result.meta.changes > 0 else 500
        response = Response.new(result.meta.changes, {'status': status})
        return response

    elif request.method == 'DELETE':
        # delete image entry from shortcode database
        authenticate(request, env)

        if not request_path:
            return RESPONSES.status_404()

        result = await (env.image_db.prepare(statements.delete)
                        .bind(request_path).run())

        status = 200 if result.success and result.meta.changes > 0 else 500
        response = Response.new('', {'status': status})
        return response

    return RESPONSES.status_404()
