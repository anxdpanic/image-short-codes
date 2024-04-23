import json

from db import statements
from db.schema import shortcodes_schema
from responses import Responses

from js import console
from js import fetch

RESPONSES = Responses()


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
        authenticate(request, env)
        data = await request.text()
        data = json.loads(data)

        image_filename = data.get('shortcode')
        if image_filename and not data.get('image'):
            image_filename = img_url + image_filename
            # return shortcode for image if exists
            result = await env.image_db.prepare(statements.select_url).bind(image_filename).first()
            if hasattr(result, 'shortcode') and result.shortcode:
                return RESPONSES.status_200(json.dumps({'shortcode': result.shortcode}))

            return RESPONSES.status_404()

        shortcode = data.get('shortcode')
        image_filename = data.get('image')

        if shortcode and image_filename:
            result = await env.image_db.prepare(statements.exists).bind(shortcode).raw()
            if result[0][0] == 1:
                return RESPONSES.status_409()

            # add image entry to shortcode database
            result = await (env.image_db.prepare(statements.insert)
                            .bind(shortcode, img_url + image_filename).run())
            if result.success and result.meta.changes > 0:
                return RESPONSES.status_200()

            return RESPONSES.status_500()

        return RESPONSES.status_400()

    elif request.method == 'PUT':
        # modify image entry in shortcode database
        authenticate(request, env)
        data = await request.text()
        data = json.loads(data)

        shortcode = data.get('shortcode')
        image_filename = data.get('image')

        if shortcode and image_filename:
            result = await env.image_db.prepare(statements.exists).bind(shortcode).raw()
            if result[0][0] == 0:
                return RESPONSES.status_404()

            result = await env.image_db.prepare(statements.update).bind(shortcode, img_url + image_filename).run()
            if result.success and result.meta.changes > 0:
                return RESPONSES.status_200()

            return RESPONSES.status_500()

        return RESPONSES.status_400()

    elif request.method == 'DELETE':
        # delete image entry from shortcode database
        authenticate(request, env)

        if not request_path:
            return RESPONSES.status_404()

        result = await env.image_db.prepare(statements.exists).bind(request_path).raw()
        if result[0][0] == 0:
            return RESPONSES.status_404()

        result = await (env.image_db.prepare(statements.delete)
                        .bind(request_path).run())
        if result.success and result.meta.changes > 0:
            return RESPONSES.status_200()

        return RESPONSES.status_500()

    return RESPONSES.status_404()
