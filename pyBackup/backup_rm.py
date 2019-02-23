#!/usr/bin/env python
import os;

def backup_rm( dirPath ):
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
  fSize = 0;                                                                    # Variable to track size of directory excluding hard/symlinks
  for root, dirs, files in os.walk( dirPath, topdown = False ):                 # Walk the directory tree
    for file in files:                                                          # Iterate over all files
      path = os.path.join( root, file );                                        # Build the full file path
      info = os.lstat( path );                                                  # Get information about file
      if info.st_nlink == 1: fSize += info.st_size;                             # If file has only one (1) inode link, then add file size to fSize variable
      os.remove( path );                                                        # Delete the file
    for dir in dirs:                                                            # Iterate over directories in root path
      path = os.path.join( root, dir );                                         # Generate path to directory in root path
      try:                                                                      # Try to...
        os.rmdir( path );                                                       # Remove directory
      except:                                                                   # on exception
        os.remove( path );                                                      # Try to remove file; may be symlink
  os.rmdir( dirPath );                                                          # Remove the top level (input) directory
  return fSize;                                                                 # Return the size of files delete; hard links only counted once


if __name__ == "__main__":
  path = '/Volumes/ExtraHDD/test';
  n = backup_rm( path );
  if n > 1.0E12:
    n    = n * 1.0E-12
    unit = 'TB'
  elif n > 1.0E9:
    n    = n * 1.0E-9
    unit = 'GB'
  elif n > 1.0E6:
    n    = n * 1.0E-6
    unit = 'MB'
  elif n > 1.0E3:
    n    = n * 1.0E-3
    unit = 'KB'
  else:
    unit = 'Bytes';
  print( 'Removed {:6.2f} {}'.format( n, unit ) );