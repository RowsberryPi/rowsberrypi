import re
from os import path

from setuptools import setup, find_packages

PACKAGE_NAME = 'rowsberrypi'
HERE = path.abspath(path.dirname(__file__))
with open(path.join(HERE, 'README.md'), encoding='utf-8') as fp:
    README = fp.read()
with open(path.join(HERE, PACKAGE_NAME, 'const.py'),
          encoding='utf-8') as fp:
    VERSION = re.search("__version__ = '([^']+)'", fp.read()).group(1)

setup(name=PACKAGE_NAME,
      description='The rowsberrypi library to connect to your Concept2 rower',
      long_description=README,
      url='http://rowsandall.com',
      license='Simplified BSD License',
      # packages=['rowsberrypi'],
      packages=find_packages(),
      keywords='rowing ergometer concept2',
      install_requires=[
          'pyrow >= 0.1.0',
          'pyusb >= 1.0.0',
          'pyyaml >= 3.12'
      ],
      include_package_data=True,
      entry_points={
          'console_scripts': [
              'workout_logger = rowsberrypi.workout_logger:main',
          ]
      },
      version=VERSION)
