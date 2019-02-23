import logging
import os, shutil;

from PyQt5.QtWidgets import QMainWindow, QWidget, QFileDialog, QLabel;
from PyQt5.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QMessageBox;
from PyQt5.QtGui import QPixmap;

class disabledMessage( QMessageBox ):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs);
    self.setText( 'Option not available, must run as root!' );
  def check(self):
    return self.clickedButton() == self.accept;

from pyBackup.rsyncBackup import rsyncBackup;
from pyBackup import utils;

# Set up some directory paths
_home     = os.path.expanduser('~');
_desktop  = os.path.join( _home, 'Desktop' );

#############################################
class pyBackupSettings( rsyncBackup, QMainWindow ):
  def __init__(self, *args, **kwargs):
    super().__init__( *args, **kwargs );                                        # Initialize the base class
    self.log = logging.getLogger( __name__ )
    self.setWindowTitle('pyBackup');                                            # Set the window title
    self.backupDisk  = None;                                                    # Set attribute for destination data directory to None
    self.dst_dirFull = None;                                                    # Set attribute for destination data directory to None
    self.config      = utils.loadConfig();
    self.is_root     = os.geteuid() == 0;                                       # Determine if running as root
    self.initUI();                                                              # Run method to initialize user interface
  ##############################################################################
  def initUI(self):
    '''
    Method to setup the buttons/entries of the Gui
    '''
    self.destButton   = QPushButton('Set Backup Disk');                         # Initialize button for selecting the destination directory
    self.destPath     = QLineEdit('');                                          # Initialize entry widget that will display the destination directory path
    self.destPath.setEnabled( False );                                          # Disable the destPath widget; that way no one can manually edit it
    self.destButton.clicked.connect(   self.select_dest   );                    # Set method to run when the destination button is clicked
    if self.config['disk_UUID']:                                                # If the UUID is set in the config dictionary
      self.backupDisk = utils.get_MountPoint( self.config['disk_UUID'] );
      self.destPath.setText( self.backupDisk );
      self.destPath.show();
    else:
      self.destPath.hide();                                                       # Hide the destination directory path

    
    txt = 'Last Backup: {}'
    if self.config['last_backup'] == "":
      txt = txt.format( 'Never' );
    else:
      txt = txt.format( '{} days ago'.format( self.config['last_backup'] ) );
    self.lastLabel = QLabel( txt );


    self.backupButton   = QPushButton('Backup now!');                           # Initialize button for selecting the destination directory
    self.backupButton.clicked.connect(   self.backup   );                       # Set method to run when the destination button is clicked

    layout = QVBoxLayout();                                                       # Initialize grid layout
    
    layout.addWidget( self.destButton);                           # Place a widget in the grid
    layout.addWidget( self.destPath  );                           # Place a widget in the grid

    layout.addWidget( self.lastLabel  );                           # Place a widget in the grid

    layout.addWidget( self.backupButton );                           # Place a widget in the grid

    centralWidget = QWidget();                                                  # Create a main widget
    centralWidget.setLayout( layout );                                            # Set the main widget's layout to the grid
    self.setCentralWidget(centralWidget);                                       # Set the central widget of the base class to the main widget
    
    self.show( );                                                               # Show the main widget
  ##############################################################################
  def select_dest(self, *args):
    '''
    Method for selecting the destination directory of the
    sounding data that was collected
    '''
    self.log.info('Setting the destination directory')
    backupDisk = QFileDialog.getExistingDirectory( directory = _desktop); # Open a selection dialog
    self.backupDisk = None if backupDisk == '' else backupDisk;                 # Update the dst_dir attribute based on the value of dst_dir
                                                                                
    if self.backupDisk is None:                                                 # If the dst_dir attribute is None
      self.log.warning( 'No destination directory set' )                        # Log a warning
    else:                                                                       # Else
      UUID = utils.get_UUID( backupDisk );                                      # Get the disk UUID
      if UUID:                                                                  # If valud UUID
        total, used, free = shutil.disk_usage( self.backupDisk );               # Get disk information
        self.config['disk_size'] = int( total * 0.9 );                          # Set disk size to 90% of the total disk size
        self.config['disk_UUID'] = UUID;                                        # Set disk_UUID in the config file
        utils.saveConfig( self.config );                                        # Update the config data

      self.destPath.setText( self.backupDisk );                                 # Show the destPath label
      self.destPath.show()                                                      # Show the destSet icon

##############################################################################
  def backup(self):
    '''
    Purpose:
      Method to backup up right now
    Inputs:
      None
    '''
    if not self.is_root:                                                        # If not running as root
      disabledMessage().exec_();                                                # Display a dialog saying cannot do unles root
    else:                                                                       # Else
      super().backup();                                                         # Start backing up

  ##############################################################################
  def proc_files(self, *args):
    '''
    Method for processing sounding files;
      i.e., renaming and removing values where ballon is descending in
      sounding
    '''
    failed = False;                                                             # Initialize failed to False
    self.log.info( 'Processing files' );    
    files = os.listdir( self.dst_dirFull );                                     # Get list of all files in the directory
    for file in files:                                                          # Iterate over the list of files
      for key in settings.rename:                                               # Loop over the keys in the settings.rename dictionary
        if key in file:                                                         # If the key is in the source file name
          dst_file = settings.rename[key].format( self.date_str );              # Set a destination file name
          dst      = os.path.join( self.dst_dirFull, dst_file );                # Build the destination file path
          src      = os.path.join( self.dst_dirFull, file );                    # Set source file path
#           self.uploadFiles.append( dst );                                       # Append the file to the uploadFile list
          self.log.info( 'Moving file: {} -> {}'.format(src, dst) );            # Log some information
          os.rename( src, dst );                                                # Move the file
          if not os.path.isfile( dst ):                                         # If the renamed file does NOT exist
            self.log.error( 'There was an error renaming the file!' );          # Log an error
            failed = True;                                                      # Set failed to True
      for key in settings.convert:                                              # Loop over the keys in the settings.rename dictionary
        if key in file:                                                         # If the key is in the source file name
          dst_file = settings.convert[key].format( self.date_str );             # Set a destination file name
          self.sndDataFile = os.path.join( self.dst_dirFull, dst_file );        # Build the destination file path
          src              = os.path.join( self.dst_dirFull, file );            # Set source file path
#           self.uploadFiles.append( dst );                                        # Append the file to the uploadFile list
          
          self.log.info( 'Converting sounding data to SHARPpy format...' );     # Log some information
          res = iMet2SHARPpy( src, self.stationName.text().upper(), 
            datetime = self.date, output = self.sndDataFile);                   # Run function to convert data to SHARPpy format
          if res and os.path.isfile( self.sndDataFile ):                        # If function returned True and the output file exists
            self.ftpInfo['ucar']['files'].append( self.sndDataFile );
            self.ftpInfo['noaa']['files'].append( self.sndDataFile );
          else:
            failed = True;                                                      # Set failed to True
            self.sndDataFile = None;                                            # if the function failed to run OR the output file does NOT exist
            self.log.error( 'There was an error creating SHARPpy file!' );      # Log an error
            criticalMessage(
              'Problem converting the sounding data to SHARPpy format!'
            ).exec_();                                                          # Generate critical error message box
    if not failed:                                                              # If failed is False
      self.log.info( 'Ready to generate sounding image!' );                     # Log some info
      self.genButton.setEnabled( True );                                        # Enable the 'Generate Sounding' button

  ##############################################################################
  def reset_values(self, noDialog = False, noSRC = False, noDST = False):
    '''
    Method to reset all the values in the GUI
    Keywords:
       noDialog  : Set to true to disable the checking dialog
       noSRC     : Set to true so that all values BUT source directory info are cleared
       noDST     : Set to true so that all values BUT destination directory info are cleared
       
       Setting both noSRC and noDST will exclude the two directories
    '''
    check = False;                                                              # Dialog check value initialize to False
    if not noDialog:                                                            # If noDialog is False
      dial = confirmMessage( 'Are you sure you want to reset all values?' );    # Initialize confirmation dialog
      dial.exec_();                                                             # Display the confirmation dialog
      check = dial.check();                                                     # Check which button selected
    if check or noDialog:                                                       # If the check is True or noDialog is True
      self.log.debug( 'Resetting all values!' );                                # Log some information
      if not noSRC or not noDST:                                                # If noSRC is False OR noDST is false
        self.copyButton.setEnabled(False);                                      # Set enabled state to False; cannot click until after the source and destination directories set
      self.procButton.setEnabled(False);                                        # Set enabled state to False; cannot click until after 'Copy Files' completes
      self.genButton.setEnabled(False);                                         # Set enabled state to False; cannot click until after 'Process Files' completes
      self.uploadButton.setEnabled(False);                                      # Set enabled state to False; cannot click until after 'Generate Sounding' completes
      self.checkButton.setEnabled(False);                                       # Set enabled state to False; cannot click until after 'FTP Upload' completes
  
      if not noSRC:                                                             # If the noSRC keyword is NOT set
        self.sourcePath.hide();                                                 # Hide the source directory path
        self.sourceSet.hide();                                                  # Hide the source directory indicator
      if not noDST:                                                             # If the noDST keyword is NOT set
        self.destPath.hide();                                                   # Hide the destination directory path
        self.destSet.hide();                                                    # Hide the destination directory indicator
  
      self.dateFrame.resetDate();                                               # Reset all the dates
      self.iopName.setText(     '' );                                           # Initialize Entry widget for the IOP name
      self.stationName.setText( '' );                                           # Initialize Entry widget for the IOP name
      self.__reset_ftpInfo();
