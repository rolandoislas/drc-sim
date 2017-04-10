#!/usr/bin/env python

from distutils.core import setup

from setuptools import find_packages

from src.server.data import constants

setup(name='drcsim',
      version=constants.VERSION,
      description='Wii U gamepad simulator.',
      install_requires=['construct<2.8', 'Pillow==3.4.2', 'cffi==1.9.1', 'netifaces==0.10.5', 'pexpect==4.2.1'],
      packages=find_packages(),
      include_package_data=True,
      data_files=[('resources/config', ['resources/config/get_psk.conf']),
                  ('resources/image', [
                        'resources/image/clover.gif',
                        'resources/image/diamond.gif',
                        'resources/image/heart.gif',
                        'resources/image/spade.gif',
                        'resources/image/icon.gif'
                  ]),
                  ('resources/command', [
                        'resources/command/na.json'
                  ])],
      scripts=['drc-sim-backend.py']
      )
