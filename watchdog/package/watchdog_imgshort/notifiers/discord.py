import logging

from discord_webhook import DiscordWebhook, DiscordEmbed

from .base import BaseNotifier
from .. import __logger__

logger = logging.getLogger(__logger__)


class Discord(BaseNotifier):
    def __init__(self, webhook, author, author_icon, embed_title, embed_color):
        self._url = webhook
        self._name = author
        self._icon = author_icon
        self._title = embed_title
        self._color = embed_color
        self._id_file = 'webhook_ids.json'
        self._webhook_ids = self._load_json(self._id_file)

    @property
    def name(self):
        return self._name

    @property
    def icon(self):
        return self._icon

    @property
    def title(self):
        return self._title

    @property
    def color(self):
        return self._color

    @property
    def ids(self):
        return self._webhook_ids

    def _get_shortcode_embed(self, shortcode, image_url, image_filename, description):
        embed = DiscordEmbed(title=self.title, description=description, color=self.color)

        embed.set_author(name=self.name, icon_url=self.icon)

        embed.set_image(url=image_url)
        embed.set_thumbnail(url=image_url)

        embed.set_timestamp()

        embed.add_embed_field(name="Shortcode", value=shortcode)
        embed.add_embed_field(name="Image", value=image_filename)
        return embed

    def notify(self, shortcode, image_url, image_filename, description):
        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        embed = self._get_shortcode_embed(shortcode, image_url, image_filename, description)
        webhook.add_embed(embed)

        logger.debug('Notifying Discord')
        response = webhook.execute()
        logger.debug(f'Discord response: {response.status_code}')
        logger.debug(f'Discord webhook id: {webhook.id}')

        if webhook.id:
            self.ids[shortcode] = webhook.id
            self._save_json(self._id_file, self.ids)
            logger.debug(f'Discord webhook ids updated with {webhook.id} for {shortcode}')

    def edit(self, shortcode, image_url, image_filename, description):
        if shortcode not in self.ids.keys():
            logger.debug(f'Discord webhook id for {shortcode} not found')
            return

        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        embed = self._get_shortcode_embed(shortcode, image_url, image_filename, description)
        webhook.add_embed(embed)
        webhook.id = self.ids[shortcode]

        logger.debug(f'Editing Discord webhook id {webhook.id}')
        response = webhook.edit()
        logger.debug(f'Discord response: {response.status_code}')

    def delete(self, shortcode):
        if shortcode not in self.ids.keys():
            logger.debug(f'Discord webhook id for {shortcode} not found')
            return

        webhook = DiscordWebhook(url=self._url, username=self.name, rate_limit_retry=True)
        webhook.id = self.ids[shortcode]

        logger.debug(f'Deleting Discord webhook id {webhook.id}')
        response = webhook.delete()
        logger.debug(f'Discord response: {response.status_code} Id: {webhook.id}')
        if 200 <= response.status_code < 300:
            del self.ids[shortcode]
            self._save_json(self._id_file, self.ids)
            logger.debug(f'Discord webhook id removed {webhook.id} for {shortcode}')
