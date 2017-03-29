from setuptools import setup, find_packages

import re

def readme():
    with open('README.md') as f:
	return f.read()

setup(name='pyrow',

      version=re.search(

	  '^__version__\s*=\s*"(.*)"',
	  open('pyrow/pyrow.py').read(),
	  re.M

	  ).group(1),

      description='The pyrow library to connect to your Concept2 rower',

      long_description=readme(),

      url='http://rowsandall.com',

      author='UVD',

      author_email='info@uvd.co.uk',

      license='MIT',

      # packages=['pyrow'],
      packages = find_packages(),

      keywords = 'rowing ergometer concept2',
      
      install_requires=[
	  'pyusb',
          'yamjam',
	  ],

      zip_safe=False,
      include_package_data=True,
      # relative to the pyrow directory
      package_data={
	  },

      entry_points = {
	  "console_scripts": [
	      'strokelog = pyrow.strokelog:main',
              'workoutlogger = pyrow.workoutlogger:main',
	      ]
	  },

      scripts=[
	  'pyrow/strokelog.py',
          'pyrow/workoutlogger.py',
	  ]

      )
