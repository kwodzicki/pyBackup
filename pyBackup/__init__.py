import logging
import os, shutil
log = logging.getLogger(__name__);
log.setLevel( logging.DEBUG );

DIR    = os.path.dirname( os.path.realpath(__file__) )
APPDIR = os.path.join(
        os.path.expanduser('~'), 
        'Library', 
        'Application Support',
        __name__
)
LOGDIR     = os.path.join( APPDIR, 'logs' )
CONFIGFILE = os.path.join( APPDIR, 'config.json' )
os.makedirs( LOGDIR, exist_ok=True )

if not os.path.isfile( CONFIGFILE ):
  shutil.copy( os.path.join(DIR, 'config.json'), CONFIGFILE )


