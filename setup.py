from setuptools import setup, find_packages

import re

def readme():
    with open('README.md') as f:
	return f.read()

setup(name='rowsberrypi',

      version=re.search(

	  '^__version__\s*=\s*"(.*)"',
	  open('rowsberrypi/rowsberrypi.py').read(),
	  re.M

	  ).group(1),

      description='The rowsberrypi library to connect to your Concept2 rower',

      long_description=readme(),

      url='http://rowsandall.com',

      author='UVD',

      author_email='info@uvd.co.uk',

      license='MIT',

      # packages=['rowsberrypi'],
      packages = find_packages(),

      keywords = 'rowing ergometer concept2',
      
      install_requires=[
	  'pyusb',
          'yamjam',
	  ],

      zip_safe=False,
      include_package_data=True,
      # relative to the rowsberrypi directory
      package_data={
	  },

      entry_points = {
	  "console_scripts": [
	      'strokelog = rowsberrypi.strokelog:main',
              'workoutlogger = rowsberrypi.workoutlogger:main',
	      ]
	  },

      scripts=[
	  'rowsberrypi/strokelog.py',
          'rowsberrypi/workout_logger.py',
	  ]

      )
