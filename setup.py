#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages

setup(name='drcsim',
      version='1.1',
      description='Wii U gamepad simulator.',
      install_requires=['construct<2.8', 'Pillow==3.4.2', 'cffi==1.9.1'],
      packages=find_packages(),
      include_package_data=True,
      data_files=[('/usr/share/drc-sim/config', ['resources/config/get_psk.conf'])],
      scripts=['drc-sim-backend.py', 'drc-sim-helper.py', 'drc-sim-frontend.py']
      )
