#!/usr/bin/python3

#
#   Developer : Philippe Piatkiewitz (philippe.piatkiewitz@vectioneer.com)
#   All rights reserved. Copyright (c) 2019 VECTIONEER.
#

from setuptools import setup

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(name='motorcortex-python-tools',
      version='1.3.8',
      description='Python tools for Motorcortex Engine',
      author='Philippe Piatkiewitz',
      author_email='philippe.piatkiewitz@vectioneer.com',
      url='https://www.motorcortex.io',
      packages=['motorcortex_tools'],
      license='MIT',
      scripts=['mcx-datalogger.py','mcx-dataplot.py'],
      install_requires=['pandas>0.22','matplotlib>2.1','motorcortex-python>0.20.1'],
      )

