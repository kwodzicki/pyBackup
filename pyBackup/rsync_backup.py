#!/usr/bin/env python3
#+
# Name:
#   rsync_backup
# Purpose:
#   A python program to create a back up of the system using rsync. 
#   A symbolic link to the latest backup is also created. Hard links to the
#   most recent back up are used to reduce space required, i.e., incremental
#   backups.
# Inputs:
#   dst_dir  : The path to the top level of the backup directory.
#   max_size : The maximum size, in gigabytes, of the backup directory.
# Outputs:
#   Some log files in the backup directory.
# Keywords:
#   verbose : Set to True to increase verbosity. Default is False.
# Author and History:
#   Kyle R. Wodzicki     Created 01 Oct. 2016
#-

import os, struct, time;
from shutil     import disk_usage, rmtree;
from datetime   import datetime;
from subprocess import Popen, PIPE;
from threading  import Thread

delay = 60
home = os.path.expanduser('~/');
struct_fmt = '<LL';

################################################################################
def rsync_exit_code( status ):	
	if status == 0:
		return 'Success';
	elif status == 1:
		return 'Syntax or usage error';
	elif status == 2:
		return 'Protocol incompatibility';
	elif status == 3:
		return 'Errors selecting input/output files, dirs';
	elif status == 4:
		return 'Requested action not supported: an attempt was made to\n'+\
		       'manipulate 64-bit files on a platform that cannot support\n'+\
		       'them; or an option was specified that is supported by the\n'+\
		       'client and not by the server.';
	elif status == 5:
		return 'Error starting client-server protocol';
	elif status == 6:
		return 'Daemon unable to append to log-file';
	elif status == 10:
		return 'Error in socket I/O';
	elif status == 11:
		return 'Error in file I/O';
	elif status == 12:
		return 'Error in rsync protocol data stream';
	elif status == 13:
		return 'Errors with program diagnostics'
	elif status == 14:
		return 'Error in IPC code';
	elif status == 20:
		return 'Received SIGUSR1 or SIGINT';
	elif status == 21:
		return 'Some error returned by waitpid()';
	elif status == 22:
		return 'Error allocating core memory buffers';
	elif status == 23:
		return 'Partial transfer due to error';
	elif status == 24:
		return 'Partial transfer due to vanished source files';
	elif status == 25:
		return 'The --max-delete limit stopped deletions';
	elif status == 30:
		return 'Timeout in data send/receive';

################################################################################
def input_with_timeout(prompt, timeout):
	'''A function to add a time out to the input function.'''
	def user_input(prompt, answer): answer[0] = input(prompt);                    # Function to be run as a thread that prompts user for input
	answer  = [None];                                                             # Initialize answer as list with None as only element
	endtime = time.time() + timeout;                                              # Set endtime to current time plus timeout
	thread  = Thread(target = user_input, args = (prompt, answer), daemon = True);# Initialize the thread to as for user input
	thread.start();                                                               # Start the thread
	while thread.is_alive() and time.time() < endtime: time.sleep(0.05);          # While the thread is alive and the current time is less than the endtime, sleep for 50 milliseconds
	if thread.is_alive():                                                         # If the thread is still alive after the endtime
		print( '' );                                                                # Print an empty string to return from the input() command which stays on same line
		return None;                                                                # Return None from the function
	else:                                                                         # Else, input was entered so
		thread.join();                                                              # Join the thread so that it closes completely
		return answer[0];	                                                          # Return the answer, which is the zeroth element of the answer list

################################################################################
def getBackupSizes( file, maxSize = None ):
	freeSpace = disk_usage(backup_dir).free;                                      # Get free space, in bytes, on the disk
	if os.path.isfile( file ):                                                    # If the file exists
		with open( file, 'rb' ) as fid:                                             # Open the settings file for reading
			tmp, curSize = struct.unpack(struct_fmt, fid.read(16));                   # Read in the old maximum size and the current size
		maxSize = tmp if maxSize is None else maxSize *1.0E9;                       # If the maxSize keyword is None, set maxSize to the old maximum size, else set to maxSize in bytes
	else:                                                                         # Else, the file does NOT exist
		if maxSize is None:                                                         # If the maxSize keyword is None
			prompt = "Please enter maximum size for backups in gigabytes: ";          # Set prompt for maximum backup size
			curSize   = 0;                                                            # Set current size of the backup to zero
			maxSize   = input_with_timeout(prompt, delay);                            # Ask user for maximum backup size with delay time of 'delay' seconds
		try:                                                                        # Try to convert the response to a float
			maxSize = float(maxSize) * 1.0E9                                          # Try to convert maxSize to a float and convert from gigabytes to bytes
		except:                                                                     # If the conversion to a float fails
			maxSize = freeSpace * 0.9;                                                # Default is to use 90% of free space on disk
	if maxSize > freeSpace * 0.9:                                                 # If the requested/default maximum size is greater than 90% of the available disk space
		maxSize = int( freeSpace * 0.9E-9 );                                        # Set maximum size to 90% of the available disk space in full gigabytes
		print( 'Requested maximum size is larger than available disk space!' );     # Print information
		print( 'New maximum size is: {:10.3f} GB'.format( maxSize ) );              # Print information
		maxSize *= 10**9;                                                           # Convert maxSize from gigabytes to bytes
	maxSize = int(maxSize);                                                       # Convert maximum size to integer
	msg = 'Using {:10.3f} GB of {:10.3f} GB for backups';                         # Format string for message
	print( msg.format(maxSize*1.0E-9, freeSpace*1.0E-9) );                        # Print information
	return maxSize, curSize;

################################################################################
def getDirList( in_dir ):
	'''Function to get list of directories in a directory.'''
	listdir, dirs = os.listdir( in_dir ), [];                                     # Get list of all files in directory and initialize dirs as list
	for dir in listdir:                                                           # Iterate over directories in listdir
		tmp = os.path.join(in_dir, dir);                                            # Generate full file path
		if os.path.isdir(tmp) and not os.path.islink(tmp): dirs.append( tmp );      # If the path is a directory and it is NOT a link, then append it to the dirs list
	dirs.sort();                                                                  # Sort the dirs list
	return dirs;                                                                  # Return the dirs list

################################################################################
def noRoomMessage(size1, size2):
	print( 'Backup is larger than allotted space!!!' );                           # Print a warning
	print( 'Backup size:  {:10.3f}'.format(size1*1.0E-9) );
	print( 'Maximum size: {:10.3f}'.format(size2*1.0E-9) );
	print( 'Increase maximum size on next run (-s, --size) or use larger drive!');
	print( 'Doing nothing!' );                                                    # Print a message

################################################################################
def rsync_backup( src_dirs, backup_dir, exclude = None, verbose = False, maxSize = None ):
	''' Main function.'''
	date     = datetime.utcnow();																									# Get current UTC time
	date_str = date.strftime('%Y-%V-%m-%d-%H%M%S');																# Put time in format YYYY-WW-MM-DD-HHMNSC, or year-week-month-day-hourminsec
	date_fmt = '%Y-%m-%d %H:%M:%S';																								# Dat format for YYYY-MM-DD HR:MN:SC
	if not os.path.isdir( backup_dir ): os.makedirs( backup_dir );                # If the backup directory does NOT exist, create it
	dst_dir = os.path.join( backup_dir, date_str );															  # Set destination directory for backup
	settings = os.path.join(backup_dir, '.rsync_settings');                       # File that contains some settings for the rsync

	maxSize, curSize = getBackupSizes( settings, maxSize = maxSize );             # Read in the maximum size and the current size

	latest     = backup_dir + '/Latest';																					# Set the Latest link path in the backup directory
	backup_log = os.path.join(backup_dir, 'backup.log');													# Set path to backup log file
	backup_err = os.path.join(backup_dir, 'backup.err');													# Set path to backup error file

	dirs = getDirList( backup_dir );
	# Check if the 'Latest' link exists in the backup directory
	if os.path.lexists( latest ):																									# If the latest directory exists
		latest_exists = True;																												# Set latest_exists variable to True
		link_dir = os.readlink( latest );																						# Read the link to the latest directory; will be used as linking directory. 
		os.remove( latest );																										  	# Delete the link
	else:
		latest_exists = False;																											# Set latest_exists variable to False
		link_dir = dirs[-1];					                                							# Set link_dir to empty string and set the link age to 52 weeks. If an existing directory is newer than 52 weeks, this variable is updated to the shorter time

	opts = ['-an', '--stats', '--link-dest='+link_dir];
	if exclude is not None:
		for i in exclude: opts.append( '--exclude=/' + i );						  			      # Append all the folders to exclude to the rsync command
	cmd = ['rsync'] + opts + src_dirs + [dst_dir];                                # Full command for rsync
	with open(os.devnull, 'w') as devnull:
		proc = Popen( cmd, stdout = PIPE, stderr = devnull);                        # Run the command sending the standard output to the pipe and any errors to /dev/null
	for line in proc.stdout.readlines():                                          # Iterate over all lines in stdout
		line = line.decode('utf8').rstrip();                                        # Decode the string and strip off carriage returns
		if 'total transferred file size' in line.lower():                           # If 'total file size' is in the line
			newSize = int( line.split()[-2] );                                        # Get the size of the transfer from the line
			break;                                                                    # Break the for loop
	proc.communicate();                                                           # Wait for rsync to finish cleanly

	if verbose: 
		print( '{:24}: {}'.format('Linking Directory', link_dir ) );                # Print the linking directory path
		print( '{:24}: {}'.format('Destination Directory', dst_dir) );              # Print the destination directory path
	if newSize > maxSize:                                                         # If the size of the new data to be transfered is larger than the maximum size
		noRoomMessage(newSize, maxSize*1.0E-9);
		return 50;

	if verbose:
		strfmt = '{:24}: {:10.3f} GB';                                              # Set format for printing
		print( strfmt.format('Current Size',  curSize * 1.0E-9) );                  # Print current size of the directory
		print( strfmt.format('Transfer Size', newSize * 1.0E-9) );                  # Print the size of the transfer
	to_delete, delSize, diffSize = [], 0, (curSize + newSize - maxSize);          # Set up some variables
	if (curSize + newSize) > maxSize:                                             # If the current size plus the size of the transfer is larger than the maximum size allowed
		for dir in dirs:                                                            # Iterate over all directories in the dirs list
			if dir == link_dir: continue;                                             # Skip the directory if it is the linking directory; i.e., Don't ever delete the linking directory
			to_delete.append( dir );                                                  # Add the directory to the to_delete list
			for root, directories, files in os.walk(dir):                             # Walk the entire directory
				for file in files:                                                      # Iterate over all files in the directory
					file_info = os.stat( os.path.join(root, file) );                      # Generate the full file path
					if file_info.st_nlink == 1: delSize += file_info.st_size;             # If the file has only one hard link, removing it will reduce the size of the directory so add the file size to the delSize variable
			if delSize >= diffSize: break;                                            # If the total size of files to be delete meets/exceeds the difference between the new size and the current size, break the look
	curSize = curSize - delSize + newSize;                                        # Compute new current size after directory deletions and add new transfer
	if curSize > maxSize:                                                         # If the new current size is still too large
		noRoomMessage(newSize, maxSize*1.0E-9);
		return 51;                                                                   # Return code two (2)
	for dir in to_delete:                                                         # Iterate over all directories in the to_delete list
		if verbose: print( 'Deleteing: ', dir, end='...');                          # Print message IF verbose
		try:																											                  # Try to delete the directory
			shutil.rmtree( dir );																											# Delete the old directory
			if verbose: print('Success!');                                            # Print success IF verbose
		except:																											                # If deletion fails
			if verbose: print( 'Error deleting!' );																    # Print error deleting IF verbose
	if verbose:																											              # Some verbose output
		print( strfmt.format('Size of deletion', delSize * 1.0E-9) );               # Size of the delete directories
		print( strfmt.format('Size after backup', curSize * 1.0E-9) );              # New size after the backup and deletions


	# Set up options for the rsync command
	opts = ['-avh', '--progress', '--stats', '--link-dest='+link_dir ];
	if exclude is not None:
		for i in exclude: opts.append( '--exclude=/' + i );						  			      # Append all the folders to exclude to the rsync command

	cmd = ['rsync'] + opts + src_dirs + [dst_dir];                                # Full command for rsync

	# Open log and error directories and write some information
	log, err = open( backup_log, 'w' ), open( backup_err, 'w' );									# Open the log and error files of writing
	log.write( 'Backup started: '						+ date.strftime(date_fmt)	+ '\n\n' );	# Write start date to backup file
	log.write( 'Destination Directory:\n  '	+ dst_dir									+ '\n\n' );	# Print the destination directory for the current backup to the log file
	log.write( 'Link Directory:\n  '				+ link_dir								+ '\n\n' );	# Print the link directory for the current backup to the log file
	log.flush();																																	# Flush the text to the log file

	# Run the rsync command and check the return status
	proc = Popen( cmd, stdout = log, stderr = err );															# Run the command with output going to log and error files
	proc.wait();																  																# Wait for the command to finish
	if proc.returncode != 0:																											# If rsync command did not finish cleanly
		err.write('\nError backing up...Current backup will be removed!');					# Write a message to the error file
		err.write('\n'+rsync_exit_code( proc.returncode ));

	# Close log and error files, create link to latest backup
	log.write( '\nBackup finished: '+datetime.utcnow().strftime(date_fmt)+'\n' );	# Write start date to backup file
	log.close(); 																																	# Close the log file
	err.close();																																	# Close the error file
	if os.path.isdir( dst_dir ):
		os.symlink(dst_dir, latest);																								# Recreate 'Latest' that existed at start of backup
	else:
		os.symlink(link_dir, latest);																								# Recreate 'Latest' that existed at start of backup

	with open( settings, 'wb' ) as fid:
		fid.write( struct.pack(struct_fmt, maxSize, curSize) );
	return proc.returncode;
################################################################################
if __name__ == "__main__":
	import argparse
	parser = argparse.ArgumentParser(description='rsync Backups')
	parser.add_argument('src_dir',   metavar = '/path/to/src', type=str, nargs='+', help='Source directory(s) for backups')
	parser.add_argument('dst_dir',   metavar = '/path/to/dst', type=str, help='Destination directory for backups')
	parser.add_argument('--exclude', metavar = 'PATTERN',      type=str, nargs='?', action='append', help='exclude files matching PATTERN')
	parser.add_argument('-s', '--size', type=float, help='Set maximum size (GB) allotted for backups. Default is 90% of free disk space.')
	parser.add_argument('-v', '--verbose', action='store_true', help='Increase verbosity')
	args = parser.parse_args()
	# backup_dirs  = [home+'/Documents', home+'/idl', home+'/Library'];								# List of directories to backup; MUST BE LIST
# 	backup_dirs  = [home+'/Documents'];								# List of directories to backup; MUST BE LIST
# 	backup_dirs  = [home+'/Documents', home+'/idl'];								# List of directories to backup; MUST BE LIST
# 	exclude_dirs = ['dev', 'proc', 'sys', 'tmp', 'run', 'mnt', 'media', 'lost+found']; # Set the folders to exclude from rsync
	x = rsync_backup( 
	  args.src_dir, 
	  args.dst_dir, 
	  exclude = args.exclude, 
	  verbose = args.verbose, 
	  maxSize = args.size )
	exit( x );