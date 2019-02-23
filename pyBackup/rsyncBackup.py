import os, sys, shutil, json;
from datetime import datetime;
from subprocess import Popen, PIPE, STDOUT, DEVNULL;

from . import utils;


class rsyncBackup( object ):
  def __init__(self):
    super().__init__();
    self.config      = utils.loadConfig();                                      # Load configuration file
    self.mountPoint  = utils.get_MountPoint( self.config['disk_UUID'] );        # Get the backup disk mount point
    self.cmd         = ['rsync', '-a', '--stats'];                              # Base command for rsync
    self.backup_dir  = os.path.join(self.mountPoint, self.config['backup_dir']);# Full path to top-level backup directory
    self.exclude_dir = self.config['exclude'];
    self.latest_dir  = os.path.join( self.backup_dir, 'Latest' );                # Set the Latest link path in the backup directory

    self.dir_list    = None;
    self.dst_dir     = None;
    self.prog_dir    = None;
    self.src_dir     = '/';
    self.backup_size = None;
    self.progress    = 0.0;
    self.lock_file   = '/tmp/pyBackup.lock'
  def test(self):
    print( 'This is a test from rsyncBackup' )
  ##############################################################################
  def backup(self):
    # Check if the 'Latest' link exists in the backup directory
    if not self.config['disk_UUID']:                                            # If the backup disk has not been setup yet
      raise Exception( 'Backup disk NOT set!' );                                # Raise exception
    elif not self.mountPoint:                                                   # If no mount point found, i.e, not mounted
        last_backup = datetime.strptime( 
          self.config['last_backup'], self.config['dateFMT']
        );                                                                      # Convert last backup date string to datetime object
        days_since = (datetime.utcnow() - last_backup).days;                    # Compute days since last backp
        self.config['days_since_last_backup'] = days_since;                     # Update days since last backup
        utils.saveConfig( self.config );                                        # Update config settings
        raise Exception( 'Backup disk NOT mounted!' );                          # Raise exception

    if not os.path.isfile( self.lock_file ):
      open( self.lock_file, 'w' ).close();                                      # Create lock file
      date          = datetime.utcnow();                                        # Get current UTC date
      date_str      = date.strftime( self.config['dateFMT']    );               # Format date to string
      self.dir_list = self.__getDirList( self.backup_dir )
      self.dst_dir  = os.path.join(  self.backup_dir, date_str );               # Set up destination directory
      self.prog_dir = self.dst_dir + '.inprogress';                             # Set up progress directory

      cmd      = self.cmd;
      link_dir = self.__getLinkDir();
      cmd.append( '--link-dest={}'.format( link_dir ) );                        # Add link directory to cmd

      ## Exclude directories
      for dir in self.exclude_dir: cmd.append( '--exclude={}'.format( dir ) );  # Iterate over all exlude directories and append to cmd
      cmd.append( '--exclude={}'.format( self.backup_dir) );                    # Append src directory path as exclude

      self.backup_size = self.__getTransferSize( cmd );
      self.__removeDirs( );
      self.__transfer( cmd );
      os.rename( self.prog_dir, self.dist_dir );
      os.symlink( self.dst_dir, self.latest_dir );
      self.config['backup_size'] += self.backup_size;
      self.config['last_backup']  = date_str;                                   # Update the last backup date string
      self.config['days_since_last_backup'] = 0;                                # Update days since last backup
      utils.saveConfig( self.config );                                          # Update the config file
      os.remove( self.lock_file );                                              # Delete lock file
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
  def __getDirList( self, backup_dir ):
    '''Function to get list of directories in a directory.'''
    listdir, dirs = os.listdir( backup_dir ), [];                               # Get list of all files in directory and initialize dirs as list
    for dir in listdir:                                                         # Iterate over directories in listdir
      tmp = os.path.join( backup_dir, dir);                                     # Generate full file path
      if os.path.isdir(tmp) and not os.path.islink(tmp): dirs.append( tmp );    # If the path is a directory and it is NOT a link, then append it to the dirs list
    dirs.sort();                                                                # Sort the dirs list
    return dirs;                                                                # Return the dirs list
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
    utils.saveConfig( self.config );                                            # Update the configuration file