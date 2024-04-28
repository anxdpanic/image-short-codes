import os

import setuptools

from watchdog.__init__ import *

short_description = ('A watchdog for monitoring a directory for changes to image files, '
                     'and mirroring changes to a remote sftp server')
long_description = short_description
if os.path.isfile("README.md"):
    with open("README.md", "r", encoding="utf-8") as fh:
        long_description = fh.read()

with open('requirements.txt') as f:
    required = f.read().splitlines()

setuptools.setup(
    name="watchdog-imgshort",
    version=__version__,
    author=__author__,
    author_email=__email__,
    description=short_description,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/anxdpanic/image-short-codes",
    project_urls={
        "Bug Tracker": "https://github.com/anxdpanic/image-short-codes/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=required,
    entry_points={'console_scripts': ['watchdog-imgshort=watchdog.__main__:main']},
)
