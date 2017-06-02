#!/usr/bin/env python3

from distutils.core import setup, Command

from setuptools import find_packages

from src.server.data import constants


class CompileDrcSimC(Command):
    pass  # TODO compile drc_sim_c


class CompileWpaSupplicantDrc(Command):
    pass  # TODO compile wpa_supplicant_drc


setup(name='drcsim',
      version=constants.VERSION,
      description='Wii U gamepad simulator.',
      install_requires=['netifaces>=0.10.5', 'pexpect>=4.2.1'],
      packages=find_packages(),
      include_package_data=True,
      data_files=[
          ('resources/config', [
              'resources/config/get_psk.conf'
          ]),
          ('resources/image', [
              'resources/image/clover.gif',
              'resources/image/diamond.gif',
              'resources/image/heart.gif',
              'resources/image/spade.gif',
              'resources/image/icon.gif'
          ]),
          ('/usr/share/applications', [
              'resources/bin/drcsimbackend.desktop'
          ]),
          ('/usr/share/icons/hicolor/512x512/apps', [
              'resources/image/drcsimbackend.png'
          ])
      ],
      scripts=['drc-sim-backend'],
      cmdclass={
          "compile_drc_sim_c": CompileDrcSimC,
          "compile_wpa_supplicant_drc": CompileWpaSupplicantDrc
      }
      )
