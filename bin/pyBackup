#!/usr/bin/env python
import logging;
import sys;
from PySide.QtGui import QApplication;
from pyBackup.pyBackupGui import pyBackupGui;

log    = logging.getLogger( 'pyBackup' );
log.setLevel( logging.DEBUG );
qt_app = QApplication( sys.argv )
inst   = pyBackupGui( );

qt_app.exec_();