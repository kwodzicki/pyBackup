import logging;
from logging.handlers import RotatingFileHandler;

import os, sys, time, shutil, re, signal;
from datetime import datetime;
from subprocess import Popen, PIPE, STDOUT, DEVNULL;

from . import LOGDIR, utils

LINESEP      = str.encode( os.linesep )
CARRET       = str.encode( '\r' )
BUFFER       = 1024 * 4 
rsync_errors = [1, 2, 3, 4, 5, 6, 10, 11, 12, 13, 14, 20, 21, 22, 25, 30, 35]
part_regex   = re.compile( r'\s*((?:\d{1,3},?)+)\s+(?:\d{1,3}\%)');
trans_regex  = re.compile( r'\s*((?:\d{1,3},?)+)\s+(?:\d{1,3}\%).+\(.+\)');
size_regex   = re.compile( r'Total transferred file size:\s((?:\d{1,3},?)+)\sbytes' )

def readLines( pipe, previous = None ):
  data = pipe.read(BUFFER).replace(CARRET, LINESEP)
  if previous: data = previous + data
  try:
    index = data.index( LINESEP )
  except:
    return None, data
  else:
    return data[:index+1], data[index+1:]

class rsyncBackup( object ):
  def __init__(self, src_dir = '/', loglevel = logging.DEBUG):
    super().__init__();
    self.log         = logging.getLogger(__name__);
    self.loglevel    = loglevel;
    self.log_file    = os.path.join(LOGDIR, 'pyBackup_rsync.log')
    rotFile  = RotatingFileHandler(self.log_file,
      maxBytes = 10 * 1024**2, backupCount = 4, encoding = 'utf8' );            # Initialize rotating file handler
    rotFile.setFormatter( logging.Formatter( '%(asctime)s [%(levelname)s] %(message)s' ) )
    rotFile.setLevel( self.loglevel );                                          # Set level to INFO
    self.log.addHandler( rotFile );                                             # Add file handler to logger

    self.cmd         = ['rsync', '-a', '--stats'];                              # Base command for rsync
    self.__updateLastBackup()
    self.mountPoint  = None;                                                    # Get the backup disk mount point
    self.backup_dir  = None;                                                    # Full path to top-level backup directory
    self.exclude_dir = None;                                                    #
    self.latest_dir  = None;                                                    # Set the Latest link path in the backup directory

    self.backups     = {'full' : [], 'partial' : [], 'cancelled' : []};          # Dictionary with lists of various backup directories
    self.dst_dir     = None;
    self.prog_dir    = None;
    self.src_dir     = src_dir;
    self.link_dir    = None;
    self.backup_size = None;
    self.progress    = 0.0;
    self.lock_file   = '/tmp/pyBackup.lock'
    self.statusTXT   = '';
    self.rsyncStatus = -1;
    self.__cancel    = False;
    for sig in [signal.SIGTERM, signal.SIGINT, signal.SIGHUP, signal.SIGQUIT]:
      signal.signal(sig, self.cancel);

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
  def cancel(self, *args):
    self.log.error( args )
    self.statusTXT = 'Canceling backup'
    self.__cancel  = True;
  
  ##############################################################################
  def backup(self):
   # Check for lock file
    if os.path.isfile( self.lock_file ):                                        # If lock file exists
      self.log.debug('Lock file exists, is there a backup running?')
      return;                                                                   # Return from method
    else:
      self.log.debug('Creating lock file')
      open( self.lock_file, 'w' ).close();                                      # Create lock file
 
    # Check backup disk set
    if not utils.CONFIG['disk_UUID']:                                            # If the backup disk has not been setup yet
      self.log.error( 'Backup disk NOT set!' )
      self.__removeLock();
      return 1

    # Check backup disk mounted
    self.mountPoint = utils.get_MountPoint( utils.CONFIG['disk_UUID'] );         # Get the backup disk mount point
    if not self.mountPoint:                                                     # If no mount point found, i.e, not mounted
      self.log.info( 'Backup disk NOT mounted!' )
      self.__removeLock();
      return 1

    ## Exclude directories
    cmd = self.cmd + [ '--exclude={}'.format( self.mountPoint) ];               # Append src directory path as exclude
    # Backing up!
    self.backup_dir  = os.path.join(self.mountPoint, utils.CONFIG['backup_dir']);# Full path to top-level backup directory
    for dir in utils.CONFIG['exclude']:
      cmd.append( '--exclude={}'.format( dir ) );      
    for dir in utils.CONFIG['user_exclude']: 
      cmd.append( '--exclude={}'.format( dir ) );

    self.latest_dir  = os.path.join( self.backup_dir, 'Latest' );               # Set the Latest link path in the backup directory
    date             = datetime.utcnow();                                       # Get current UTC date
    date_str         = date.strftime( utils.CONFIG['date_FMT']    );             # Format date to string

    self.__getDirList( self.backup_dir );                                       # Get list of vaild backup directories
    self.dst_dir  = os.path.join(  self.backup_dir, date_str );                 # Set up destination directory
    self.prog_dir = self.dst_dir + '.inprogress';                               # Set up progress directory
    if len( self.backups['partial'] ) > 0:                                      # If there are canceled backups still hanging around
      self.log.info('Using latested canceled backup, should save some time.')
      os.rename( self.backups['partial'][-1], self.prog_dir );                  # Rename the newest canceled backup to match the current .inprogress directory, this may save some time
      cmd.append( '--delete' );                                                 # Append delete option to cmd; there may be flies in the canceled backup that no longer exists on the computer
    self.backups['partial'].append( self.prog_dir );                            # Append current in progress directory to that list

    # Link directory to reduce backup size
    self.link_dir = self.__getLinkDir();
    if self.link_dir: cmd.append( '--link-dest={}'.format( self.link_dir ) );   # If a directory is returned, add link directory to cmd

    self.backup_size = self.__getTransferSize( cmd );
    if self.backup_size == 0:                                                   # If nothing has changed:
      self.log.info('No files have changed, skipping backup');
      self.__removeLock();
      return 0;

    self.__removeDirs( );
    self.rsyncStatus = self.__transfer( cmd );
    if (self.rsyncStatus not in rsync_errors) and (not self.__cancel):          # If no bad error has ben returned from rsync AND backup has NOT been canceled
      self.log.info( 'Moving : {} ---> {}'.format(self.prog_dir, self.dst_dir ) )
      os.rename(  self.prog_dir, self.dst_dir );                                # Move the .inprogress directory to normal name
      if os.path.exists( self.latest_dir):
        os.remove(  self.latest_dir );                                          # Delete the 'Latest' link
      os.symlink( self.dst_dir, self.latest_dir );                              # Create 'Latest' link pointed at newest backup
      utils.CONFIG['backup_size'] += self.backup_size;
      utils.CONFIG['last_backup']  = date_str;                                  # Update the last backup date string
      utils.CONFIG['days_since_last_backup'] = 0;                               # Update days since last backup
      utils.CONFIG.saveConfig( )                                                # Update the config file
      self.__cleanUp();
      self.statusTXT   = 'Finished'
      self.rsyncStatus = 0
      return 0
    elif (self.rsyncStatus != 0):
      self.log.critical('Backup failed! Return code : {}'.format(self.rsyncStatus) )
    self.__removeLock();
    self.rsyncStatus = 1
    return 1
  
  ##############################################################################
  def __removeLock(self):
    if os.path.isfile( self.lock_file ): 
      self.log.debug('Removing lock file');
      os.remove( self.lock_file );                                              # Delete lock file
  
  ##############################################################################
  def __cleanUp(self):
    self.statusTXT = 'Cleaning up'
    for dir in self.backups['partial']:                                         # Iterate over directories where backup was in progress
      if os.path.isdir( dir ):
        shutil.rmtree( dir );                                                   # Delete the directory
    for dir in self.backups['cancelled']:                                       # Iterate over directories where backup was in progress
      if os.path.isdir( dir ):
        shutil.rmtree( dir );                                                   # Delete the directory
    if not os.path.lexists( self.latest_dir ):                                  # If the 'Latest' directory does NOT exists
      if self.link_dir:                                                         # If the link_dir attribute is set
        os.symlink( self.link_dir, self.latest_dir );                           # Create symlink to link-dest dir
    self.__removeLock();
  
  ##############################################################################
  def __getTransferSize(self, cmd):
    self.statusTXT = 'Calculating backup size'
    proc = Popen( cmd + ['-n', self.src_dir, self.prog_dir], 
      stdout = PIPE, stderr = STDOUT) 

    lines = proc.stdout.read( BUFFER ).splitlines(True)
    while lines and (not self.__cancel):
      line = lines.pop(0)
      if not line.endswith(LINESEP):                                            # If line not end in line separater
        lines = line + b''.join(lines) + proc.stdout.read(BUFFER)               # Join lines list on '', prepend line, and append another read
        lines = lines.splitlines(True)
      else:
        line       = line.decode()
        trans_size = size_regex.findall( line );
        if len(trans_size) == 1:
          backup_size = int( trans_size[0].replace(',','') );
          self.log.info( 'Backup size: {}'.format(backup_size) )
          break
    if self.__cancel:
      proc.terminate();
      backup_size = None;
    proc.communicate();
    return backup_size;
  
  ##############################################################################
  def __transfer(self, cmd):
    self.statusTXT = 'Backing up {}'.format(self.__size_fmt(self.backup_size));
    cmd  = cmd + ['--progress', self.src_dir, self.prog_dir]
    self.log.info( 'Full rsync cmd : {}'.format(cmd) )
    proc = Popen( cmd, stdout=PIPE, stderr=STDOUT )    # Run rsync command
    transfered = 0;                                                             # Initialize total transferd size
    line, remain = readLines( proc.stdout )                                     # Read first line form stdout
    while (line or remain) and (not self.__cancel):                             # While line is NOT empty
      if line and line.endswith(LINESEP):                                       # If line not end in line separater
          line = line.decode()
          trans_size = part_regex.findall( line )                               # Try to find total size of transfered file
          if len(trans_size) == 0 and (line != os.linesep):                     # If no number found, assume it is a file path
            self.log.debug( line.rstrip() )                                     # Log the file being backed up
          elif len(trans_size) == 1:                                            # If only one number found
            trans_size    = int( trans_size[0].replace(',','') )                # Convert file size to integer
            self.progress = 100 * (transfered + trans_size) / self.backup_size  # Set progress to fraction of transfered file size
            if '(' in line: transfered += trans_size;                           # If there is a '(' in file, it means file finished transfering
      line, remain = readLines( proc.stdout, previous = remain )      

    self.progress = 100;                                                        # Ensure that percentage is 100
    if self.__cancel:
      proc.terminate();

    proc.communicate();                                                         # Close the PIPEs and everything
    return proc.returncode

  ##############################################################################
  def __getDirList( self, backup_dir ):
    '''Function to get list of directories in a directory.'''
    self.log.debug('Getting list of backups')
    listdir      = os.listdir( backup_dir );                                    # Get list of all files in directory and initialize dirs as list
    self.backups = {'full' : [], 'partial' : [], 'cancelled' : []};             # Dictionary with lists of various backup directories
    for dir in listdir:                                                         # Iterate over directories in listdir
      tmp = os.path.join( backup_dir, dir);                                     # Generate full file path
      if os.path.isdir(tmp) and ( not os.path.islink(tmp) ):                    # If the path is a directory and is NOT a symbolic link
        if '.inprogress' in dir:                                                # If the directory has '.inprogress' in the name
          self.backups['partial'].append( tmp );                                # Directory is in progress
        else:                                                                   # Else, normal full backup
          self.backups['full'].append( tmp )                                    # Append to dirs list
    for key in self.backups: self.backups[key].sort();                          # Sort the various lists

  ##############################################################################
  def __getLinkDir(self):
    self.log.debug( 'Latest dir : {}'.format(self.latest_dir) )
    self.log.debug( "Finding 'Latest' link destination")
    if os.path.lexists( self.latest_dir ):                                      # If the latest directory exists
      link_dir = os.readlink( self.latest_dir );                                # Read the link to the latest directory; will be used as linking directory. 
    elif len(self.backups['full']) > 0:                                         # If there are directories in the dir_list attribute
      link_dir = self.backups['full'][-1];                                      # Set link_dir to empty string and set the link age to 52 weeks. If an existing directory is newer than 52 weeks, this variable is updated to the shorter time
    else:                                                                       # Else
      self.log.debug("'Latest' link either does not exist or destination not found!" )
      return None;                                                              # Return None value
    if not os.path.isabs( link_dir ):
      link_dir = os.path.realpath( os.path.join( self.backup_dir, link_dir ) )

    self.log.debug('Latest dir : {}'.format( link_dir ) )
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
      used = utils.CONFIG['backup_size']+self.backup_size;                       # Compute diskspace used by current backups and current one
      while used > utils.CONFIG['disk_size']:                                    # While the size of the current backup plus all other backups is larger than the drive size
        for root, dirs, files in os.walk( self.backups['full'].pop(0), topdown=False ):# Walk the directory tree
          for file in files:                                                    # Iterate over all files
            if self.__cancel: return;                                           # If __cancel is set, return
            path = os.path.join( root, file );                                  # Build the full file path
            info = os.lstat( path );                                            # Get information about file
            if info.st_nlink == 1: utils.CONFIG['backup_size'] -= info.st_size;  # If file has only one (1) inode link, then subtract file size from config backup size
            os.remove( path );                                                  # Delete the file
          for dir in dirs:                                                      # Iterate over directories in root path
            if self.__cancel: return;                                           # If __cancel is set, return
            path = os.path.join( root, dir );                                   # Generate path to directory in root path
            try:                                                                # Try to...
              os.rmdir( path );                                                 # Remove directory
            except:                                                             # on exception
              os.remove( path );                                                # Try to remove file; may be symlink
        os.rmdir( dirPath );                                                    # Remove the top level (input) directory
        used = utils.CONFIG['backup_size']+self.backup_size;                     # Compute diskspace used by current backups and current one      
        self.log.debug( 'Deleted: {}'.format(dirPath) )
    self.statusTXT = 'Deleting old backups'
    localRemove();
    utils.CONFIG.saveConfig(  );                                            # Update the configuration file

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

  ########################################################
  def __updateLastBackup(self, days = None):
    last_backup = utils.CONFIG.get('last_backup', '')
    if days is None and last_backup != '':
      last_backup = datetime.strptime( last_backup, utils.CONFIG['date_FMT'] )   # Convert last backup date string to datetime object
      days = (datetime.utcnow() - last_backup).days                             # Compute days since last backp
      self.log.info( 'Days since last backup: {}'.format(days) )
    utils.CONFIG['days_since_last_backup'] = days;                               # Update days since last backup
    utils.CONFIG.saveConfig( );                                          # Update config settings
