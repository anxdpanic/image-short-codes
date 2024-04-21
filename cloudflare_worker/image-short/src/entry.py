from db.schema import shortcodes_schema

from js import Response


async def prepare_database(env):
    result = await env.image_db.prepare(shortcodes_schema).run()
    if not result.success:
        return Response.new('Failed to prepare database')


async def on_fetch(request, env):
    await prepare_database(env)

