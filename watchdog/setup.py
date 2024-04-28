import setuptools

from watchdog.__init__ import *


setuptools.setup(
    name=__name__,
    version=__version__,
    author=__author__,
    author_email=__email__,
    description=__short_description__,
    long_description=__long_description__,
    long_description_content_type="text/markdown",
    url=__github__,
    project_urls={
        "Bug Tracker": f"{__github__}/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
    packages=setuptools.find_packages(),
    python_requires=">=3.6",
    install_requires=__requirements__,
    entry_points={'console_scripts': ['watchdog-imgshort=watchdog.__main__:main']},
)
