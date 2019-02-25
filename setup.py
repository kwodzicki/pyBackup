#!/usr/bin/env python
import sys, os, importlib, json;
from setuptools import setup, find_packages;
from setuptools.command.install import install

pkg_name = "pyBackup";
pkg_desc = "A program for OS X Time Machine like backups";
pkg_url  = "https://github.com/kwodzicki/pyBackup";

tmp_config = '.{}_tmp.json'.format(pkg_name);                                   # Temporary config file; required when uninstall before install
tmp_config = os.path.join( os.path.expanduser( "~" ), tmp_config );             # Temporary config file; required when uninstall before install

sys.path.pop(0);                                                                # Pop off current directory from path
pkg_info = importlib.util.find_spec( pkg_name );                                # Look for the package; may be installed
if pkg_info:                                                                    # If the package is found
  pkg_dir    = os.path.dirname( pkg_info.origin );                              # Current package directory
  old_config = os.path.join( pkg_dir, 'config.json' );                          # Get current config.json file location
  if os.path.isfile( old_config ):                                              # If the config file exists
    with open( old_config, 'rb' ) as src:                                       # Open the old file in binary read mode
      with open( tmp_config, 'wb') as dst:                                      # Open temporary file in binary write mode
        dst.write( src.read() );                                                # Copy data from old to temporary file

class CustomInstall( install ):
  def _post_install( self ):
    '''
    Purpose:
      Post-installation method for keeping config settings
    Inputs:
      None
    '''
    def find_module_path():
      '''Local function for determining package installation directory'''
      for p in sys.path:                                                        # Iterate over all system paths
        if os.path.isdir(p) and pkg_name in os.listdir(p):                      # If the path is a directory and the package name is in the directory list
          print(p, pkg_name)
          return os.path.join(p, pkg_name);                                     # Return path to package
    install_path = find_module_path();                                          # Find the package path
    new_config   = os.path.join( install_path, 'config.json' );                 # Set path to new config file
    if os.path.isfile( tmp_config ):                                            # If the temprorary config file exists
      if os.path.isfile( new_config ):                                          # If the new config file exists
        with open( tmp_config, 'r' ) as fid:                                    # Open temporary file for reading
          old_data = json.load( fid );                                          # Read data from temporary file
        os.remove( tmp_config );                                                # Remove the temporary file
        with open(new_config, 'r') as fid:                                      # Open the file for reading 
          new_data = json.load( fid );                                          # Read in the new data
        for key in old_data:                                                    # Iterate over the keys in the old_data
          new_data[key] = old_data[key];                                        # Change new_data value at key to old_data value
      with open(new_config, 'w') as fid:                                        # Open new config file for writing
        json.dump( new_data, fid, indent = 4 );                                 # Write the new data
  def run( self ):
    install.run( self );
    self._post_install();


setup(
  name                 = pkg_name,
  description          = pkg_desc ,
  url                  = pkg_url,
  author               = "Kyle R. Wodzicki",
  author_email         = "krwodzicki@gmail.com",
  version              = "0.0.15",
  packages             = find_packages(),
  install_requires     = ['PyQt5', 'python-crontab'],
  scripts              = ['bin/pyBackup'],
  package_data         = {pkg_name : ['config.json']},
  include_package_data = True,
  zip_safe             = False,
  cmdclass             = {'install' : CustomInstall}
);
