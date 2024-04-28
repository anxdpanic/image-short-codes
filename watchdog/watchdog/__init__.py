__version__ = '0.1.1'
__name__ = 'watchdog-imgshort'
__author__ = 'anxdpanic'
__email__ = 'anxdpanic@@users.noreply.github.com'
__license__ = 'GPL-3.0-or-later'
__github__ = 'https://github.com/anxdpanic/image-short-codes'

__short_description__ = ('A watchdog that monitors a directory for changes to image files, mirrors changes to a '
                         'remote sftp server, when necessary generates a shortcode url using a Cloudflare worker, '
                         'then sends a Discord notification with the generated shortcode url.')

with open("README.md", "r", encoding="utf-8") as fh:
    __long_description__ = fh.read()

with open('requirements.txt') as f:
    __requirements__ = f.read().splitlines()

__all__ = ['__version__', '__name__', '__author__', '__email__', '__license__', '__github__',
           '__short_description__', '__long_description__', '__requirements__']
