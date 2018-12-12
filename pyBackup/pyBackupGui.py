import logging
import os, shutil;

from PySide.QtGui import QMainWindow, QWidget, QFileDialog, QPixmap, QLabel;
from PySide.QtGui import QLineEdit, QPushButton, QGridLayout;

# Imports for SHARPpy
# from .widgets import QLogger, dateFrame, indicator;
# from messageBoxes import criticalMessage, saveMessage, confirmMessage;
# import settings;

# Set up some directory paths
# _home     = os.path.expanduser('~');
# _desktop  = os.path.join( _home, 'Desktop' );

#############################################
class pyBackupGui( QMainWindow ):
  def __init__(self, parent = None):
    QMainWindow.__init__(self);                                                 # Initialize the base class
    self.setWindowTitle('pyBackup');                                            # Set the window title
    self.src_dir     = None;                                                    # Set attribute for source data directory to None
    self.dst_dir     = None;                                                    # Set attribute for destination data directory to None
    self.dst_dirFull = None;                                                    # Set attribute for destination data directory to None
    self.log = logging.getLogger( __name__ )
    self.initUI();                                                              # Run method to initialize user interface

  ##############################################################################
  def initUI(self):
    '''
    Method to setup the buttons/entries of the Gui
    '''
    self.iopLabel     = QLabel('IOP Number');                                   # Initialize Entry widget for the IOP name
    self.iopName      = QLineEdit();                                            # Initialize Entry widget for the IOP name
    self.stationLabel = QLabel('Station Name');                                 # Initialize Entry widget for the IOP name
    self.stationName  = QLineEdit();                                            # Initialize Entry widget for the IOP name
    self.sourceButton = QPushButton('Source Directory');                        # Initialize button for selecting the source directory
    self.destButton   = QPushButton('Destination Directory');                   # Initialize button for selecting the destination directory
    self.sourcePath   = QLineEdit('');                                          # Initialize entry widget that will display the source directory path
    self.destPath     = QLineEdit('');                                          # Initialize entry widget that will display the destination directory path
    
    self.sourcePath.setEnabled( False );                                        # Disable the sourcePath widget; that way no one can manually edit it
    self.destPath.setEnabled(   False );                                        # Disable the destPath widget; that way no one can manually edit it

    self.sourcePath.hide();                                                     # Hide the source directory path
    self.destPath.hide();                                                       # Hide the destination directory path

    self.sourceButton.clicked.connect( self.select_source );                    # Set method to run when the source button is clicked 
    self.destButton.clicked.connect(   self.select_dest   );                    # Set method to run when the destination button is clicked

    self.copyButton = QPushButton( 'Copy Files' );                              # Create 'Copy Files' button
    self.copyButton.clicked.connect( self.copy_files );                         # Set method to run when 'Copy Files' button is clicked
    self.copyButton.setEnabled(False);                                          # Set enabled state to False; cannot click until after the source and destination directories set

    self.procButton = QPushButton( 'Process Files' );                           # Create 'Process Files' button
    self.procButton.clicked.connect( self.proc_files );                         # Set method to run when 'Process Files' button is clicked
    self.procButton.setEnabled(False);                                          # Set enabled state to False; cannot click until after 'Copy Files' completes

    
#     log_handler = QLogger( );                                                   # Initialize a QLogger logging.Handler object
#     logging.getLogger('pyBackup').addHandler( log_handler );                    # Get the Meso1819 root logger and add the handler to it

    grid = QGridLayout();                                                       # Initialize grid layout
    grid.setSpacing(10);                                                        # Set spacing to 10
    for i in range(4): 
      grid.setColumnStretch(i,  0);                                             # Set column stretch for ith column
      grid.setColumnMinimumWidth(i,  60);                                       # Set column min width for ith column
    grid.setColumnStretch(4,  0);                                               # Set column stretch for 5th column
    grid.setColumnMinimumWidth(4,  20);                                         # Set column min width for 5th column

    grid.setRowStretch(1,  0);                                                  # Set column stretch for 5th column
    grid.setRowStretch(3,  0);                                                  # Set column stretch for 5th column
    grid.setRowMinimumHeight(1,  25);                                           # Set column min width for 5th column
    grid.setRowMinimumHeight(3,  25);                                          # Set column min width for 5th column
    
    grid.addWidget( self.sourceButton,  0, 0, 1, 4 );                           # Place a widget in the grid
    grid.addWidget( self.sourcePath,    1, 0, 1, 5 );                           # Place a widget in the grid

    grid.addWidget( self.destButton,    2, 0, 1, 4 );                           # Place a widget in the grid
    grid.addWidget( self.destPath,      3, 0, 1, 5 );                           # Place a widget in the grid

    grid.addWidget( self.iopLabel,      4, 0, 1, 2 );                           # Place a widget in the grid
    grid.addWidget( self.iopName,       5, 0, 1, 2 );                           # Place a widget in the grid

    grid.addWidget( self.stationLabel,  4, 2, 1, 2 );                           # Place a widget in the grid
    grid.addWidget( self.stationName,   5, 2, 1, 2 );                           # Place a widget in the grid

    grid.addWidget( self.copyButton,    7, 0, 1, 4 );                           # Place a widget in the grid
    grid.addWidget( self.procButton,    8, 0, 1, 4 );                           # Place a widget in the grid

#     grid.addWidget( log_handler.frame, 0, 6, 13, 1);
    centralWidget = QWidget();                                                  # Create a main widget
    centralWidget.setLayout( grid );                                            # Set the main widget's layout to the grid
    self.setCentralWidget(centralWidget);                                       # Set the central widget of the base class to the main widget
    
    self.show( );                                                               # Show the main widget
  ##############################################################################
  def select_source(self, *args):
    '''
    Method for selecting the source directory of the
    sounding data that was collected
    '''
    self.log.info('Setting the source directory')
    src_dir = QFileDialog.getExistingDirectory( dir = _desktop );               # Open a selection dialog
    self.src_dir = None if src_dir == '' else src_dir;                          # Update the src_dir attribute based on the value of src_dir

    if self.src_dir is None:                                                    # If the src_dir attribute is None
      self.log.warning( 'No source directory set' );                            # Log a warning
      self.reset_values( noDialog = True );                                     # Reset all the values in the GUI with no confirmation dialog
    else:                                                                       # Else
      self.sourcePath.setText( src_dir );                                       # Set the sourcePath label text
      self.sourcePath.show();                                                   # Show the sourcePath label
      self.sourceSet.show();                                                    # Show the sourceSet icon
      if self.dst_dir is not None:                                              # If the dst_dir attribute is not None
        self.__init_ftpInfo();                                                  # Initialize ftpInfo attribute using method
        self.copyButton.setEnabled( True );                                     # Set the 'Copy Files' button to enabled
        self.reset_values(noDialog = True, noSRC = True, noDST = True);         # Reset all values excluding the src AND dst directory
      else:
        self.reset_values(noDialog = True, noSRC = True);                       # Reset all values excluding the src directory

  ##############################################################################
  def select_dest(self, *args):
    '''
    Method for selecting the destination directory of the
    sounding data that was collected
    '''
    self.log.info('Setting the destination directory')
    dst_dir = QFileDialog.getExistingDirectory( dir = _desktop);                # Open a selection dialog
    self.dst_dir = None if dst_dir == '' else dst_dir;                          # Update the dst_dir attribute based on the value of dst_dir
                                                                                
    if self.dst_dir is None:                                                    # If the dst_dir attribute is None
      self.log.warning( 'No destination directory set' )                        # Log a warning
      self.reset_values( noDialog = True )                                      # Reset all the values in the GUI with no confirmation dialog
    else:                                                                       # Else
      if 'IOP' in os.path.basename( self.dst_dir ).upper():                     # If an IOP directory was selected
        self.log.debug('Moved IOP# from directory path as it is append later'); # Log some debugging information
        self.dst_dir = os.path.dirname( self.dst_dir );                         # Remove the IOP directory from the destination directory
      self.destSet.show( );                                                     # Set the destPath label text
      self.destPath.setText( self.dst_dir )                                     # Show the destPath label
      self.destPath.show()                                                      # Show the destSet icon
      if self.src_dir is not None:                                              # If the src_dir attribute is not None
        self.__init_ftpInfo();                                                  # Initialize ftpInfo attribute using method
        self.copyButton.setEnabled( True );                                     # Set the 'Copy Files' button to enabled
        self.reset_values(noDialog = True, noSRC = True, noDST = True);         # Reset all values excluding the src AND dst directory
      else:
        self.reset_values(noDialog = True, noDST = True);                       # Reset all values excluding the dst directory
  ##############################################################################
  def copy_files(self, *args):
    '''
    Method for copying files from source to destination, renaming
    files along the way
    '''
    if self.dst_dir is None: 
      self.log.error( 'Destination directory NOT set!' );
      return;
    if self.src_dir  is None:
      self.log.error( 'Source directory NOT set!' );
      return;

    if self.iopName.text() == '':
      self.log.error( 'IOP Number NOT set!!!' )
      criticalMessage( "Must set the IOP Number!!!" ).exec_();
      return
    if self.stationName.text() == '':
      self.log.error( 'Station Name NOT set!!!' )
      criticalMessage( "Must set the Station Name!!!" ).exec_();
      return

    # Main copying code
    failed = False;                                                             # Initialize failed to False    
    self.__init_ftpInfo();                                                      # Initialize ftpInfo attribute using method
    self.date, self.date_str = self.dateFrame.getDate( );                       # Get datetime object and date string as entered in the gui
    if self.date is None: return;                                               # If the date variable is set to None
    self.dst_dirFull  = os.path.join( 
      self.dst_dir, 'IOP'+self.iopName.text(), self.date_str
    );                                                                          # Build destination directory using the dst_dir, iopName, and date string
    if not os.path.isdir( self.dst_dirFull ):                                   # If the output directory does NOT exist
      self.log.info( 'Creating directory: ' + self.dst_dirFull );               # Log some information
      os.makedirs( self.dst_dirFull );                                          # IF the dst_dir does NOT exist, then create it
    else:                                                                       # Else, the directory exists, so check to over write
      dial = confirmMessage( 
        "The destination directory exists!\n" + \
        "Do you want to overwrite it?\n\n" + \
        "YOU CANNOT UNDO THIS ACTION!!!" 
      );
      dial.exec_();                                                             # Generate the message window
      if dial.check():
        self.log.info( 'Removing directory: ' + self.dst_dirFull );             # Log some information
        shutil.rmtree( self.dst_dirFull );                                      # Delete the directory
        self.log.info( 'Creating directory: ' + self.dst_dirFull );             # Log some information
        os.makedirs( self.dst_dirFull );                                        # IF the dst_dir does NOT exist, then create it
      else:                                                                     # Else, don't do anything
        self.log.warning('Cannot over write data!');                            # Log a warning
        return;                                                                 # Return from function

    self.log.info( 'Source directory: {}'.format(self.src_dir) );               # Log some information
    self.log.info( 'Destination directory: {}'.format(self.dst_dirFull) );      # Log some information
    self.log.info( 'Copying directory' );                                       # Log some information
    for root, dirs, files in os.walk( self.src_dir ):                           # Walk over the source directory
      for file in files:                                                        # Loop over all files
        src = os.path.join( root, file );                                       # Set the source file path
        dst = os.path.join( self.dst_dirFull, file );                           # Set the destination path
        shutil.copy2( src, dst );                                               # Copy all data from the source directory to the dst_dir
        if not os.path.isfile( dst ):                                           # If the destination file does NOT exist
          self.log.error( 'There was an error copying file: {}'.format(file) ); # Log a warning
          failed = True;                                                        # Set failed to True
          break;                                                                # Break the for loop
    if not failed:
      self.log.info( 'Finished copying' );                                      # log some information
      self.log.info( 'Ready to process data files!' );                          # Log some info
      self.procButton.setEnabled( True );                                       # Enable the 'Process Files' button
    else:                                                                       # Else, something went wrong
      criticalMessage(
        "Something went wrong!\n\n" + \
        "There was an error copying a data file.\n" + \
        "Please check the logs and directories to see what happened."
      ).exec_(); 

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
