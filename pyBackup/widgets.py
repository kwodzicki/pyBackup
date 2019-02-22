import logging
from PySide.QtGui  import QWidget, QPainter, QFrame, QLabel, QCheckBox;
from PySide.QtGui  import QTextEdit, QLineEdit, QFont;
from PySide.QtGui  import QVBoxLayout, QHBoxLayout, QGridLayout;
from PySide.QtCore import Qt, QPoint;
from datetime      import datetime;
from Meso1819      import settings;
from messageBoxes  import criticalMessage, confirmMessage;

class QLogger(logging.Handler):
  '''Code from:
  https://stackoverflow.com/questions/28655198/best-way-to-display-logs-in-pyqt
  '''
  def __init__(self, parent = None, format = settings.log_fmt, level = logging.INFO):
    logging.Handler.__init__(self);                                             # Initialize a log handler as the super class
    self.setFormatter( logging.Formatter( format ) );                           # Set the formatter for the logger
    self.setLevel( level );                                                     # Set the logging level
    self.frame = QFrame(parent);                                                # Initialize a QFrame to place other widgets in
         
    self.frame2 = QFrame(parent);                                               # Initialize frame2 for the label and checkbox
    self.label  = QLabel('Logs');                                               # Define a label for the frame
    self.check  = QCheckBox('Debugging');                                       # Checkbox to enable debugging logging
    self.check.clicked.connect( self.__changeLevel );                           # Connect checkbox clicked to the __changeLevel method
    
    self.log_widget = QTextEdit();                                              # Initialize a QPlainTextWidget to write logs to
    self.log_widget.verticalScrollBar().minimum();                              # Set a vertical scroll bar on the log widget
    self.log_widget.horizontalScrollBar().minimum();                            # Set a horizontal scroll bar on the log widget
    self.log_widget.setLineWrapMode( self.log_widget.NoWrap );                  # Set line wrap mode to no wrapping
    self.log_widget.setFont( QFont("Courier", 12) );                            # Set the font to a monospaced font
    self.log_widget.setReadOnly(True);                                          # Set log widget to read only
    
    layout = QHBoxLayout();                                                     # Initialize a horizontal layout scheme for the label and checkbox frame
    layout.addWidget( self.label );                                             # Add the label to the layout scheme
    layout.addWidget( self.check );                                             # Add the checkbox to the layout scheme
    self.frame2.setLayout( layout );                                            # Set the layout for frame to the horizontal layout
    
    layout = QVBoxLayout();                                                     # Initialize a layout scheme for the widgets
    layout.addWidget( self.frame2 );                                            # Add the label/checkbox frame to the layout scheme
    layout.addWidget( self.log_widget );                                        # Add the text widget to the layout scheme

    self.frame.setLayout( layout );                                             # Set the layout of the fram to the layout scheme defined
  ##############################################################################
  def emit(self, record):
    '''
    Overload the emit method so that it prints to the text widget
    '''
    msg = self.format(record);                                                  # Format the message for logging
    if record.levelno >= logging.CRITICAL:                                      # If the log level is critical
      self.log_widget.setTextColor( Qt.red );                                   # Set text color to red
    elif record.levelno >= logging.ERROR:                                       # Elif level is error
      self.log_widget.setTextColor( Qt.darkMagenta );                           # Set text color to darkMagenta
    elif record.levelno >= logging.WARNING:                                     # Elif level is warning
      self.log_widget.setTextColor( Qt.darkCyan );                              # Set text color to darkCyan
    else:                                                                       # Else
      self.log_widget.setTextColor( Qt.black );                                 # Set text color to black
    self.log_widget.append(msg);                                                # Add the log to the text widget
  ##############################################################################
  def write(self, m):
    '''
    Overload the write method so that it does nothing
    '''
    pass;
  ##############################################################################
  def __changeLevel(self, *args):
    '''
    Private method to change logging level
    '''
    if self.check.isChecked():
      self.setLevel( logging.DEBUG );                                           # Get the Meso1819 root logger and add the handler to it
    else:
      self.setLevel( logging.INFO );                                            # Get the Meso1819 root logger and add the handler to it
################################################################################
class indicator( QWidget ): 
  '''
  A QWidget subclass to draw green indicators to signify that
  a step as been completed
  '''
  def __init__(self, parent = None):
    QWidget.__init__(self, parent)

  def paintEvent(self, event):
    '''
    Method to run on paint events
    '''
    painter = QPainter();                                                       # Get a QPainter object
    painter.begin(self);                                                        # Begin painting
    painter.setRenderHint( QPainter.Antialiasing );                             # Set a rendering option
    painter.setBrush( Qt.transparent );                                         # Set the paint brush to transparent
    painter.drawRect( 0, 0, 20, 20 );                                           # Draw a rectangle with width = height = 20
    painter.setBrush( Qt.green );                                               # Set the paint brush color to green
    painter.drawEllipse( QPoint(10, 10), 9, 9 );                                # Draw a circle that fills most of the rectangle
    painter.end();                                                              # End the painting

################################################################################
class dateFrame( QFrame ):
  def __init__(self, parent = None):
    QFrame.__init__(self, parent);
    self.log   = logging.getLogger( __name__ );
    self.year  = QLineEdit( )
    self.month = QLineEdit( )
    self.day   = QLineEdit( )
    self.hour  = QLineEdit( )
    
    year       = QLabel('Year')
    month      = QLabel('Month')
    day        = QLabel('Day')
    hour       = QLabel('Hour')
    
    grid = QGridLayout();
    grid.addWidget( year,   0, 0 );
    grid.addWidget( month,  0, 1 );
    grid.addWidget( day,    0, 2 );
    grid.addWidget( hour,   0, 3 );

    grid.addWidget( self.year,   1, 0 );
    grid.addWidget( self.month,  1, 1 );
    grid.addWidget( self.day,    1, 2 );
    grid.addWidget( self.hour,   1, 3 );
    self.setLayout(grid)
  ############################
  def getDate(self):
    '''Method to return datetime object and formatted date string'''
    try:
      date = datetime( int( self.year.text()  ),
                       int( self.month.text() ),
                       int( self.day.text()   ),
                       int( self.hour.text()  ) );
    except:
      self.log.error( 'Must set the date!' );                                   # Log an error
      criticalMessage( "Must set the date!!!" ).exec_();                        # Generate error message dialog
      return None, None;                                                        # Return None for the date and date string

    # Dialog to remind user to make sure date is entered correctly
    dial = confirmMessage( 
      "Are you sure you entered to date correctly?\n\n" + \
      "It MUST be in UTC time!"
    );                                                                          # Initialize confirmation dialog
    dial.exec_();                                                               # Execute the dialog; make it appear
    if not dial.check():                                                        # If the user clicked no
      self.log.warning('Canceled because incorrect date');                      # Log a warning
      return None, None;

    return date, date.strftime( settings.date_fmt );
  ##############################################################################
  def resetDate(self):
    '''Method to reset all date entry boxes'''
    self.log.debug( 'Resetting the date' );
    self.year.setText(  '' )
    self.month.setText( '' )
    self.day.setText(   '' )
    self.hour.setText(  '' ) 
