import os, sys, json;
from subprocess import check_output;

_dir        = os.path.dirname( os.path.realpath(__file__) );
_configFile = os.path.join( _dir, 'config.json' );
DISKUTIL    = ['diskutil', 'info'] 
def loadConfig():
  with open(_configFile, 'r') as fid:
    config = json.load( fid );
  if not config['disk_UUID']:                                                   # If the disk UUID is NOT defined
    host = check_output( 'hostname' ).decode().rstrip();
    config['backup_dir'] = os.path.join( config['backup_dir'], host )
  return config;

def saveConfig( config ):
    with open(_configFile, 'w') as fid:
      json.dump( config, fid, indent = 4 );

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

