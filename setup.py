#!/usr/bin/env python
from setuptools import setup
import setuptools


setuptools.setup(
  name                 = "pyBackup",
  description          = "A program for OS X Time Machine like backups",
  url                  = "https://github.com/kwodzicki/pyBackup",
  author               = "Kyle R. Wodzicki",
  author_email         = "krwodzicki@gmail.com",
  version              = "0.0.12",
  packages             = setuptools.find_packages(),
  install_requires     = ['PyQt5', 'python-crontab'],
  scripts              = ['bin/pyBackup'],
  package_data         = {'pyBackup' : ['config.json']},
  include_package_data = True,
  zip_safe             = False
);
