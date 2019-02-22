#!/usr/bin/env python
from setuptools import setup
import setuptools


setuptools.setup(
  name             = "pyBackup",
  description      = "A program for OS X Time Machine like backups",
  url              = "https://github.com/kwodzicki/pyBackup",
  author           = "Kyle R. Wodzicki",
  author_email     = "krwodzicki@gmail.com",
  version          = "0.0.1",
  packages         = setuptools.find_packages(),
  install_requires = ['Pillow', 'pystray', 'PySide'],
  scripts          = ['bin/pyBackup'],
  zip_safe         = False
);