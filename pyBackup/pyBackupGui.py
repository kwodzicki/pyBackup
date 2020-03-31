import logging
import os, shutil, time;
from crontab import CronTab;
from threading import Thread;

from PyQt5.QtWidgets import QMainWindow, QWidget, QFileDialog, QLabel;
from PyQt5.QtWidgets import QLineEdit, QPushButton, QVBoxLayout, QMessageBox;
from PyQt5.QtWidgets import QProgressBar;
from PyQt5.QtGui import QPixmap;
from PyQt5 import QtCore;

class disabledMessage( QMessageBox ):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs);
    self.setText( 'Option not available, must run as root!' );
  def check(self):
    return self.clickedButton() == self.accept;

from pyBackup.version import __version__
from pyBackup.rsyncBackup import rsyncBackup;
from pyBackup import utils;

# Set up some directory paths
_home     = os.path.expanduser('~');
_desktop  = os.path.join( _home, 'Desktop' );

#############################################
class pyBackupSettings( rsyncBackup, QMainWindow ):
  statusSignal    = QtCore.pyqtSignal(str);
  butTxtSignal    = QtCore.pyqtSignal(str)
  lastLabelSignal = QtCore.pyqtSignal(str)
  pBarSignal      = QtCore.pyqtSignal(int);
  pBarTxtSignal   = QtCore.pyqtSignal(bool);
  def __init__(self, *args, **kwargs):
    super().__init__( *args, **kwargs );                                        # Initialize the base class
    self.setWindowTitle('pyBackup');                                            # Set the window title
    self.backupDisk    = None;                                                  # Set attribute for destination data directory to None
    self.dst_dirFull   = None;                                                  # Set attribute for destination data directory to None
    self.autoBackupFMT = 'Automatic Backup: {}';                                # Formatter for automatic backup
    self.lastBackupFMT = 'Last Backup: {}';
    self.statusFMT     = 'Status: {}';
    self._running      = False;
    self.is_root       = os.geteuid() == 0;                                     # Determine if running as root
    self.backupThread  = None;
    self.monitorThread = None
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
    if utils.CONFIG['disk_UUID']:                                                # If the UUID is set in the config dictionary
      self.backupDisk = utils.get_MountPoint( utils.CONFIG['disk_UUID'] );
      self.destPath.setText( self.backupDisk );
    self.destPath.show();
    
    # Text labels
    if utils.CONFIG['days_since_last_backup'] == "":
      txt = self.lastBackupFMT.format( 'Never' );
    else:
      txt = self.lastBackupFMT.format( 
        '{} days ago'.format( utils.CONFIG['days_since_last_backup'] )
      );
    self.lastLabel    = QLabel( txt );
    self.statusLabel  = QLabel( self.statusFMT.format('') );
    self.lastLabelSignal.connect( self.lastLabel.setText );                     # Connect this signal to setText method of statusLabel
    self.statusSignal.connect(    self.statusLabel.setText );                   # Connect this signal to setText method of statusLabel
    
    # Progress bar
    self.pBar         = QProgressBar()
    self.pBar.setRange(0, 100);
    self.pBar.setGeometry( 30, 40, 200, 24 );
    self.pBarSignal.connect( self.pBar.setValue );
    self.pBarTxtSignal.connect( self.pBar.setTextVisible );
    # Auto backup button
    self.autoButton   = QPushButton();                                          # Initialize button for selecting the destination directory
    self.autoButton.clicked.connect( self.autoBackup );                         # Set method to run when the destination button is clicked
    if utils.CONFIG['auto_backup']:
      self.autoButton.setText( self.autoBackupFMT.format('Enabled') )
    else:
      self.autoButton.setText( self.autoBackupFMT.format('Disabled') )

    # Backup now button
    self.backupButton   = QPushButton('Backup now!');                           # Initialize button for selecting the destination directory
    self.backupButton.clicked.connect(   self.backup   );                       # Set method to run when the destination button is clicked
    self.butTxtSignal.connect( self.backupButton.setText )

    layout = QVBoxLayout();                                                       # Initialize grid layout
    
    layout.addWidget( self.destButton);                                         # Place a widget in the grid
    layout.addWidget( self.destPath  );                                         # Place a widget in the grid
    layout.addWidget( self.lastLabel  );                                        # Place a widget in the grid
    layout.addWidget( self.statusLabel );                                       # Place a widget in the grid
    layout.addWidget( self.pBar );
    layout.addWidget( self.autoButton );                                        # Place a widget in the grid
    layout.addWidget( self.backupButton );                                      # Place a widget in the grid
    layout.addWidget( QLabel( 'version {}'.format(__version__) ) )

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
      utils.setBackupDir( backupDisk )

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
      return;
    if not self.backupThread:                                                   # If there is NOT a backup thread running
      self.backupThread  = Thread( target = super().backup      )               # Initialize new thread
      self.monitorThread = Thread( target = self._monitorStatus )
      self.backupThread.start();                                                # Start the thread
      self.monitorThread.start()
    else:
      self.cancel()
      self.backupThread = None

  ##############################################################################
  def _monitorStatus(self, *args, **kwargs):
    self.butTxtSignal.emit( 'Cancel' )
    self.statusSignal.emit( self.statusFMT.format('Backing up') )
    self.pBarTxtSignal.emit(True)

    while self.backupThread and self.backupThread.is_alive():
      self.statusSignal.emit( self.statusFMT.format( self.statusTXT ) )
      self.pBarSignal.emit(   int( self.progress ) )
      time.sleep(1.0);

    time.sleep(2.0)
    if (self.rsyncStatus == 0): 
      self.lastLabelSignal.emit( self.lastBackupFMT.format('0 days ago') )
    else:
      self.lastLabelSignal.emit( 'Failed!' )

    self.statusSignal.emit( self.statusFMT.format('') )
    self.pBarTxtSignal.emit( False )
    self.pBarSignal.emit( 0 )
    self.butTxtSignal.emit( 'Backup now!' )
    self.backupThread = None

  ##############################################################################
  def autoBackup(self):
    if not self.is_root:                                                        # If not running as root
      disabledMessage().exec_();                                                # Display a dialog saying cannot do unles root
      return;
    my_cron = CronTab( user = os.environ['LOGNAME'] );
    utils.CONFIG['auto_backup'] = not utils.CONFIG['auto_backup'];                # Set to opposit value
    if utils.CONFIG['auto_backup']:
      self.autoButton.setText( self.autoBackupFMT.format('Enabled') )
      cmd = os.path.join( utils._dir, utils.CONFIG['cron_cmd'] );
      cmd = "/usr/bin/env python3 {}".format( cmd )
      job = my_cron.new( command = cmd, comment = utils.CONFIG['cron_cmt'] )
      job.every(1).hour();
      my_cron.write();
    else:
      self.autoButton.setText( self.autoBackupFMT.format('Disabled') )
      for job in my_cron:
        if job.comment == utils.CONFIG['cron_cmt']:
          my_cron.remove(job);
          my_cron.write();
          break;
    utils.CONFIG.saveConfig( )                                            # Update config file

  ##############################################################################
  def closeEvent(self, event):
    self.cancel()
    self.log.info('Quitting')
    event.accept()
