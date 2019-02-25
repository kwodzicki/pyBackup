import logging;
from logging.handlers import RotatingFileHandler;

import os, sys, shutil, re;
from datetime import datetime;
from subprocess import Popen, PIPE, STDOUT, DEVNULL;

from pyBackup import utils;

part_regex  = re.compile( r'\s*((?:\d{1,3},?)+)\s+(?:\d{1,3}\%)');
trans_regex = re.compile( r'\s*((?:\d{1,3},?)+)\s+(?:\d{1,3}\%).+\(.+\)');
size_regex  = re.compile( r'Total transferred file size:\s((?:\d{1,3},?)+)\sbytes' )
class rsyncBackup( object ):
  def __init__(self, src_dir = '/', loglevel = logging.INFO):
    super().__init__();
    self.log         = logging.getLogger(__name__);
    self.loglevel    = loglevel;
    self.cmd         = ['rsync', '-a', '--stats'];                              # Base command for rsync
    self.config      = utils.loadConfig();                                      # Load configuration file
    self.mountPoint  = None;                                                    # Get the backup disk mount point
    self.backup_dir  = None;                                                    # Full path to top-level backup directory
    self.exclude_dir = None;                                                    #
    self.latest_dir  = None;                                                    # Set the Latest link path in the backup directory

    self.dir_list    = [];
    self.inProg_list = [];
    self.dst_dir     = None;
    self.prog_dir    = None;
    self.src_dir     = src_dir;
    self.link_dir    = None;
    self.backup_size = None;
    self.progress    = 0.0;
    self.lock_file   = '/tmp/pyBackup.lock'
    self.log_file    = '/var/logs/pyBackup_rsync.log'
    self.statusTXT   = '';
    self.__cancel    = False;
  ##############################################################################
  @property
  def backup_dir(self):
    return self.__backup_dir;
  @backup_dir.setter
  def backup_dir(self, value):
    if value is not None:
      if not os.path.isdir( value ): 
        os.makedirs( value );                                                   # If dirctory does NOT exist, create it
    self.__backup_dir = value;                                                  # Set private variable
  #########
  @property
  def statusTXT(self):
    return self.__statusTXT;
  @statusTXT.setter
  def statusTXT(self, value):
    if value != '': self.log.info( value );
    self.__statusTXT = value;                                                  # Set private variable
  ##############################################################################
  def cancel(self):
    self.statusTXT = 'Canceling backup'
    self.__cancel  = True;
  ##############################################################################
  def backup(self):
    # Check for lock file
    if os.path.isfile( self.lock_file ):                                        # If lock file exists
      return;                                                                   # Return from method
    else:
      open( self.lock_file, 'w' ).close();                                      # Create lock file
    rotFile  = RotatingFileHandler(self.log_file,
      maxBytes = 10 * 1024**2, backupCount = 4, encoding = 'utf8' );            # Initialize rotating file handler
    rotFile.setLevel( self.loglevel );                                          # Set level to INFO
    self.log.addHandler( rotFile );                                             # Add file handler to logger

    # Check backup disk set
    if not self.config['disk_UUID']:                                            # If the backup disk has not been setup yet
      self.log.error( 'Backup disk NOT set!' )
      self.log.debug('Removing lock file.')
      os.remove( self.lock_file)
      return

    # Check backup disk mounted
    self.mountPoint = utils.get_MountPoint( self.config['disk_UUID'] );         # Get the backup disk mount point
    if not self.mountPoint:                                                     # If no mount point found, i.e, not mounted
      self.log.info( 'Backup disk NOT mounted!' )
      last_backup = datetime.strptime( 
        self.config['last_backup'], self.config['date_FMT']
      );                                                                        # Convert last backup date string to datetime object
      days_since = (datetime.utcnow() - last_backup).days;                      # Compute days since last backp
      self.log.info( 'Days since last backup: {}'.foramt(days_since) );
      self.config['days_since_last_backup'] = days_since;                       # Update days since last backup
      utils.saveConfig( self.config );                                          # Update config settings
      self.log.debug('Removing lock file.')
      os.remove( self.lock_file)
      return

    # Backing up!
    self.backup_dir  = os.path.join(self.mountPoint, self.config['backup_dir']);# Full path to top-level backup directory
    self.exclude_dir = self.config['exclude'];
    self.latest_dir  = os.path.join( self.backup_dir, 'Latest' );                # Set the Latest link path in the backup directory
    date             = datetime.utcnow();                                       # Get current UTC date
    date_str         = date.strftime( self.config['date_FMT']    );             # Format date to string

    self.dir_list, self.inProg_list = self.__getDirList( self.backup_dir );     # Get list of vaild backup directories and those inprogress
    self.dst_dir  = os.path.join(  self.backup_dir, date_str );                 # Set up destination directory
    self.prog_dir = self.dst_dir + '.inprogress';                               # Set up progress directory
    self.inProg_list.append( self.prog_dir );                                   # Append current in progress directory to that list

    ## Exclude directories
    cmd = self.cmd + [ '--exclude={}'.format( self.mountPoint) ];               # Append src directory path as exclude
    for dir in self.exclude_dir: cmd.append( '--exclude={}'.format( dir ) );    # Iterate over all exlude directories and append to cmd

    # Link directory to reduce backup size
    self.link_dir = self.__getLinkDir();
    if self.link_dir: cmd.append( '--link-dest={}'.format( self.link_dir ) );   # If a directory is returned, add link directory to cmd

    self.backup_size = self.__getTransferSize( cmd );
    self.__removeDirs( );
    self.__transfer( cmd );
    if not self.__cancel:                                                       # If backup has NOT been canceled
      os.rename( self.prog_dir, self.dst_dir );
      os.symlink( self.dst_dir, self.latest_dir );
      self.config['backup_size'] += self.backup_size;
      self.config['last_backup']  = date_str;                                   # Update the last backup date string
      self.config['days_since_last_backup'] = 0;                                # Update days since last backup
      utils.saveConfig( self.config );                                          # Update the config file
    self.__cleanUp();
    self.statusTXT   = 'Finished'
  ##############################################################################
  def __cleanUp(self):
    self.statusTXT = 'Cleaning up'
    for dir in self.inProg_list:                                                # Iterate over directories where backup was in progress
      shutil.rmtree( dir );                                                     # Delete the directory
    if not os.path.lexists( self.latest_dir ):                                  # If the 'Latest' directory does NOT exists
      if self.link_dir:                                                         # If the link_dir attribute is set
        os.symlink( self.link_dir, self.latest_dir );                           # Create symlink to link-dest dir
    if os.path.isfile( self.lock_file ): os.remove( self.lock_file );           # Delete lock file
  ##############################################################################
  def __getTransferSize(self, cmd):
    self.statusTXT = 'Calculating backup size'
    proc = Popen( cmd + ['-n', self.src_dir, self.prog_dir], 
      stdout = PIPE, stderr = STDOUT, 
      universal_newlines = True );
    line = proc.stdout.readline();
    while line and (not self.__cancel):
      trans_size = size_regex.findall( line );
      if len(trans_size) == 1:
        backup_size = int( trans_size[0].replace(',','') );
        break;
      line = proc.stdout.readline();
    if self.__cancel:
      proc.terminate();
      backup_size = None;
    proc.communicate();
    return backup_size;
  ##############################################################################
  def __transfer(self, cmd):
    self.statusTXT = 'Backing up {}'.format(self.__size_fmt(self.backup_size));
    proc = Popen( cmd + ['--progress', self.src_dir, self.prog_dir], 
      stdout = PIPE, stderr = STDOUT, 
      universal_newlines = True );                                              # Run rsync command
    transfered = 0;                                                             # Initialize total transferd size
    line = proc.stdout.readline();                                              # Read first line form stdout
    while line and (not self.__cancel):                                         # While line is NOT empty
      trans_size = part_regex.findall( line );                                  # Try to find total size of transfered file
      if len(trans_size) == 0:                                                  # If no number found, assume it is a file path
        self.log.info( line.rstrip() );                                         # Log the file being backed up
      elif len(trans_size) == 1:                                                # If only one number found
        trans_size    = int( trans_size[0].replace(',','') );                   # Convert file size to integer
        self.progress = 100 * (transfered + trans_size) / self.backup_size;     # Set progress to fraction of transfered file size
        if '(' in line: transfered += trans_size;                               # If there is a '(' in file, it means file finished transfering
        self.progress  = 100 * transfered / self.backup_size;                   # Set progress to fraction of transfered file size
      line = proc.stdout.readline();                                            # Get another line from rsync command
    self.progress = 100;                                                        # Ensure that percentage is 100
    if self.cancel:
      proc.terminate();
    proc.communicate();                                                         # Close the PIPEs and everything
  ##############################################################################
  def __getDirList( self, backup_dir ):
    '''Function to get list of directories in a directory.'''
    self.log.debug('Getting list of backups')
    listdir, dirs, inprog = os.listdir( backup_dir ), [], [];                   # Get list of all files in directory and initialize dirs as list
    for dir in listdir:                                                         # Iterate over directories in listdir
      tmp = os.path.join( backup_dir, dir);                                     # Generate full file path
      if os.path.isdir(tmp) and (not os.path.islink(tmp)):
        if '.inprogress' in dir:
          inprog.append( tmp );
        else:
          dirs.append( tmp )
    dirs.sort();                                                                # Sort the dirs list
    return dirs, inprog;                                                        # Return the dirs list
  ##############################################################################
  def __getLinkDir(self):
    self.log.debug("Trying to find 'Latest' link")
    if os.path.lexists( self.latest_dir ):                                      # If the latest directory exists
      link_dir = os.readlink( self.latest_dir );                                # Read the link to the latest directory; will be used as linking directory. 
      os.remove( self.latest_dir );                                             # Delete the link
    elif len(self.dir_list) > 0:                                                # If there are directories in the dir_list attribute
      link_dir = self.dir_list[-1];                                             # Set link_dir to empty string and set the link age to 52 weeks. If an existing directory is newer than 52 weeks, this variable is updated to the shorter time
    else:                                                                       # Else
      return None;                                                              # Return None value
    return link_dir;                                                            # Return link_dir
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
    def localRemove():
      used = self.config['backup_size']+self.backup_size;                       # Compute diskspace used by current backups and current one
      while used > self.config['disk_size']:                                    # While the size of the current backup plus all other backups is larger than the drive size
        for root, dirs, files in os.walk( self.dir_list.pop(0), topdown=False ):# Walk the directory tree
          for file in files:                                                    # Iterate over all files
            if self.__cancel: return;                                           # If __cancel is set, return
            path = os.path.join( root, file );                                  # Build the full file path
            info = os.lstat( path );                                            # Get information about file
            if info.st_nlink == 1: self.config['backup_size'] -= info.st_size;  # If file has only one (1) inode link, then subtract file size from config backup size
            os.remove( path );                                                  # Delete the file
          for dir in dirs:                                                      # Iterate over directories in root path
            if self.__cancel: return;                                           # If __cancel is set, return
            path = os.path.join( root, dir );                                   # Generate path to directory in root path
            try:                                                                # Try to...
              os.rmdir( path );                                                 # Remove directory
            except:                                                             # on exception
              os.remove( path );                                                # Try to remove file; may be symlink
        os.rmdir( dirPath );                                                    # Remove the top level (input) directory
        used = self.config['backup_size']+self.backup_size;                     # Compute diskspace used by current backups and current one      
        self.log.debug( 'Deleted: {}'.format(dirPath) )
    self.statusTXT = 'Deleting old backups'
    localRemove();
    utils.saveConfig( self.config );                                            # Update the configuration file
  ########################################################
  def __size_fmt(self, num, suffix='B'):
    '''
    Purpose:
      Private method for determining the size of 
      a file in a human readable format
    Inputs:
      num  : An integer number file size
    Authors:
      Barrowed from https://github.com/ekim1337/PlexComskip
    '''
    for unit in ['','K','M','G','T','P','E','Z']:
      if abs(num) < 1024.0:
        return "{:3.1f}{}{}".format(num, unit, suffix)
      num /= 1024.0
    return "{:.1f}{}{}".format(num, 'Y', suffix);

# If run from command line
if __name__ == "__main__":
  inst = rsyncBackup();
  try:
    inst.backup();
  except:
    exit(1);
  exit(0);
