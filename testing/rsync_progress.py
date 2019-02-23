from subprocess import Popen, PIPE, STDOUT, DEVNULL;

cmd = ['rsync', '-av', '--stats', '--progress', '--exclude=.*', '/home/kyle', '/mnt/BackUps/'];
proc = Popen( cmd , stdout = PIPE, stderr = STDOUT, 
  universal_newlines = True );
line = proc.stdout.readline();
while line:
  if '100%' in line:
    fsize = int( line.split()[0].replace(',','') )
    print( fsize )
  line = proc.stdout.readline();
proc.communicate();

