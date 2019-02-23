#!/usr/bin/env python

import os, sys, shutil, json;
from datetime import datetime;
from subprocess import Popen, PIPE, STDOUT, DEVNULL;

dir = os.path.dirname( os.path.abspath( __file__ ) )
configFile = os.path.join(dir, 'config.json');

class pyBackup( object ):
  def __init__(self, config=None):
    super().__init__();
    if config is None:
      config = self.__initConfig();
    self.dateFMT     = "%Y-%V-%m-%d-%H%M%S";                                                 # Format for dates
    self.cmd         = ['rsync', '-a', '--stats'];                                           # Base command for rsync
    self.config      = config;
    self.backup_dir  = config['backup_dir'];
    self.exclude_dir = config['exclude'];
    self.latest_dir  = os.path.join( self.backup_dir, 'Latest' );                # Set the Latest link path in the backup directory
    self.date_str    = datetime.utcnow().strftime( self.dateFMT );                    # Get current UTC time
    self.dst_dir     = os.path.join( self.backup_dir, self.date_str )
    self.prog_dir    = self.dst_dir + '.inprogress';
    self.src_dir     = '/';
    self.dir_list    = self.__getDirList()
    self.backup_size = None;
    self.progress    = 0.0;
  ##############################################################################
  def run(self):
    # Check if the 'Latest' link exists in the backup directory
    cmd = self.cmd;
    link_dir = self.__getLinkDir();
    cmd.append( '--link-dest={}'.format( link_dir ) );                              # Add link directory to cmd

    ## Exclude directories
    for dir in self.exclude_dir: cmd.append( '--exclude={}'.format( dir ) );    # Iterate over all exlude directories and append to cmd
    cmd.append( '--exclude={}'.format( self.backup_dir) );                      # Append src directory path as exclude

    self.backup_size = self.__getTransferSize( cmd );
    self.__removeDirs( );
    self.__transfer( cmd );
    os.rename( self.prog_dir, self.dist_dir );
    os.symlink( self.dst_dir, self.latest_dir );
    self.__updateConfig();
  ##############################################################################
  def __getTransferSize(self, cmd):
    proc = Popen( cmd + ['-n', self.src_dir, self.prog_dir], 
      stdout = PIPE, stderr = STDOUT, 
      universal_newlines = True );
    line = proc.stdout.readline();
    while line:
      if 'total size is' in line.lower():
        backup_size = int( line.split()[3].replace(',','') )
        break;
      line = proc.stdout.readline();
    proc.communicate();
    return backup_size;
  ##############################################################################
  def __transfer(self, cmd):
    transfered = 0;
    proc = Popen( cmd + ['--progress', self.src_dir, self.prog_dir], 
      stdout = PIPE, stderr = STDOUT, 
      universal_newlines = True );
    line = proc.stdout.readline();                                              # Read first line form stdout
    while line:                                                                 # While line is NOT empty
      if '100%' in line:                                                        # Check for 100% in line
        transfered += int( line.split()[0].replace(',','') );                   # Get size of transfered file and subtract it from the remaining transfer size
        progress    = transfered / self.backup_size;
      line = proc.stdout.readline();                                            # Get another line from rsync command
    proc.communicate();                                                         # Close the PIPEs and everything
  ##############################################################################
  def __getDirList( self ):
    '''Function to get list of directories in a directory.'''
    listdir, dirs = os.listdir( self.backup_dir ), [];                            # Get list of all files in directory and initialize dirs as list
    for dir in listdir:                                                           # Iterate over directories in listdir
      tmp = os.path.join( self.backup_dir, dir);                                  # Generate full file path
      if os.path.isdir(tmp) and not os.path.islink(tmp): dirs.append( tmp );      # If the path is a directory and it is NOT a link, then append it to the dirs list
    dirs.sort();                                                                  # Sort the dirs list
    return dirs;                                                                  # Return the dirs list
  ##############################################################################
  def __getLinkDir(self):
    if os.path.lexists( self.latest_dir ):                                      # If the latest directory exists
      link_dir = os.readlink( self.latest_dir );                                # Read the link to the latest directory; will be used as linking directory. 
      os.remove( self.latest_dir );                                             # Delete the link
    else:
      link_dir = self.dir_list[-1];                                              # Set link_dir to empty string and set the link age to 52 weeks. If an existing directory is newer than 52 weeks, this variable is updated to the shorter time
    return link_dir;
  ##############################################################################
  def __removeDirs( self ):
    '''
    Purpose:
      A function to recursively delete a directory while tracking
      the size of the directory excluding all hard/symlink sizes.
      File size is track by ignoring multiply linked files because
      deleting one copy of a multiply hard linked file does NOT 
      reduce the size of the top level directory. Only when all
      copies are delete does the total size of the directory
      decrease.
    Inputs:
      dirPath  : Path to directory to clear out
    Outputs:
      Returns the size of files deleted.
    '''
    while (self.config['backup_size']+self.backup_size) > self.config['drive_size']: # While the size of the current backup plus all other backups is larger than the drive size
      for root, dirs, files in os.walk( self.dir_list.pop(0), topdown=False ):  # Walk the directory tree
        for file in files:                                                      # Iterate over all files
          path = os.path.join( root, file );                                    # Build the full file path
          info = os.lstat( path );                                              # Get information about file
          if info.st_nlink == 1: self.config['backup_size'] -= info.st_size;    # If file has only one (1) inode link, then subtract file size from config backup size
          os.remove( path );                                                    # Delete the file
        for dir in dirs:                                                        # Iterate over directories in root path
          path = os.path.join( root, dir );                                     # Generate path to directory in root path
          try:                                                                  # Try to...
            os.rmdir( path );                                                   # Remove directory
          except:                                                               # on exception
            os.remove( path );                                                  # Try to remove file; may be symlink
      os.rmdir( dirPath );                                                      # Remove the top level (input) directory
  ##############################################################################
  def __initConfig(self):
    with open(configFile, 'r') as fid:
      config = json.load( fid );
    config['backup_dir'] = input('Where do you want to backup to: ');
    total, used, free = shutil.disk_usage( config['backup_dir'] );
    config['drive_size'] = int( total * 0.9 );
    return config;
  ##############################################################################
  def __updateConfig(self):
    self.config['backup_size'] += self.backup_size;
    self.config['last_backup']  = self.date_str
    with open(configFile, 'w') as fid:
      json.dump( self.config, fid );

if __name__ == "__main__":
  inst = pyBackup();
  inst.run();