from pathlib import Path
from pathlib import PurePath

import setuptools

from watchdog.__init__ import *

__short_description__ = ('A watchdog that monitors a directory for changes to image files, mirrors changes to a '
                         'remote sftp server, when necessary generates a shortcode url using a Cloudflare worker, '
                         'then sends a Discord notification with the generated shortcode url.')

with Path(PurePath(Path(__file__).cwd()).parent, 'README.md').open() as file_handle:
    __long_description__ = file_handle.read()

with Path('requirements.txt').open() as file_handle:
    __requirements__ = file_handle.read().splitlines()

setuptools.setup(
    name=__name__,
    version=__version__,
    author=__author__,
    author_email=__email__,
    description=__short_description__,
    long_description=__long_description__,
    long_description_content_type='text/markdown',
    url=__github__,
    project_urls={
        'Bug Tracker': f'{__github__}/issues',
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Operating System :: OS Independent',
    ],
    packages=setuptools.find_packages(),
    python_requires='>=3.6',
    install_requires=__requirements__,
    entry_points={'console_scripts': ['watchdog-imgshort=watchdog.__main__:main']},
)
