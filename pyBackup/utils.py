import os, sys, shutil, json
from subprocess import check_output

from . import CONFIGFILE

DISKUTIL   = ['diskutil', 'info'] 

class Config( object ):
  def __init__(self):
    self.file  = CONFIGFILE 
    self._data = {}
    self.loadConfig()
  def __getitem__(self, key):
    return self._data.get(key, None)
  def __setitem__(self, key, val):
    self._data[key] = val
  def keys(self):
    return self._data.keys()
  def get(self, *args, **kwargs):
    return self._data.get(*args, **kwargs)
  def pop(self, *args, **kwargs):
    return self._data.pop(*args, **kwargs)
  def loadConfig(self):
    with open(self.file, 'r') as fid:
      self._data.update( json.load( fid ) )
    if not self._data['disk_UUID']:                                                   # If the disk UUID is NOT defined
      host = check_output( 'hostname' ).decode().rstrip()
      self._data['backup_dir'] = os.path.join( self._data['backup_dir'], host )
  def saveConfig(self):
      with open(self.file, 'w') as fid:
        json.dump( self._data, fid, indent = 4 );

CONFIG = Config()

def diskutil(val):                                                                                                                                                                                       
  data = {}  
  if isinstance(val, str) and val != '':
    try:
      lines = check_output( DISKUTIL+[val] ).decode().splitlines() 
    except:
      return data
    for line in lines:
      try:
        key, val = line.split(':')
      except:
        pass
      else:
        data[ key.strip() ] = val.strip()
  return data

def get_UUID( mnt_point ):
  '''
  Purpose:
    A function to determine the UUID of a hard drive
    given its mount point
  Inputs:
    mnt_point : Path to mount point
  Outputs:
    Returns UUID
  '''
  if mnt_point[-1] == os.sep: mnt_point = mnt_point[:-1];                       # If the last character in the mount point is directory separator, remove it

  if 'linux' in sys.platform:
    data = json.loads( check_output( ['lsblk', '--fs', '--json'] ) );             # Run lsblk command to get information about block devices
    for device in data['blockdevices']:                                           # Iterate over all the devicies
      if ('children' in device) and device['children']:                           # If the device has children
        for child in device['children']:                                          # Iterate over all the children
          if ('mountpoint' in child) and child['mountpoint']:                     # If the child has a mount point
            if mnt_point in child['mountpoint']:                                  # If the child's mount point matches the user input mount point
              return child['uuid'];                                               # Return the UUID
  elif 'darwin' in sys.platform:
    data = diskutil( mnt_point )
    return data.get('Disk / Partition UUID', None)

  return None;                                                                  # Not found, so return None

def get_MountPoint( UUID ):
  '''
  Purpose:
    A function to determine the UUID of a hard drive
    given its mount point
  Inputs:
    mnt_point : Path to mount point
  Outputs:
    Returns UUID
  '''
  if 'linux' in sys.platform:
    data = json.loads( check_output( ['lsblk', '--fs', '--json'] ) );             # Run lsblk command to get information about block devices
    for device in data['blockdevices']:                                           # Iterate over all the devicies
      if ('children' in device) and device['children']:                           # If the device has children
        for child in device['children']:                                          # Iterate over all the children
          if ('uuid' in child) and (child['uuid'] == UUID):                       # If the child has a UUID
            return child['mountpoint'];                                           # If the child's mount point matches the user input mount point
  elif 'darwin' in sys.platform:
    data = diskutil( UUID )
    return data.get('Mount Point', None)
  return None                                                                   # Not found, so return None

def setBackupDir( path ):
  '''
  Purpose:
    A function to set the backup directory information 
    given its mount point
  Inputs:
    path : Path to mount point
  Outputs:
    Returns True if set information, False otherwise
  '''
  UUID = get_UUID( path )
  if UUID and os.path.isdir( path ):
    total, used, free = shutil.disk_usage( path )
    CONFIG['disk_size'] = int(free * 0.9)
    CONFIG['disk_UUID'] = UUID
    CONFIG.saveConfig()
    return True
  return False
