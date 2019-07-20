# pyBackup

A python for macOS Time Machine like backups. Provides GUI for setting up
automatic hourly backups, or for manual backups at any time.

## How it works

This package is a 'smart' wrapper for the `rsync` utility. When run, the newest
backup is located and used as a reference for the new backup using the 
`--link-dest` option of `rsync`. This allows current backups to simply link
to previously backed up files if no changes have been made, which greatly 
reduces the size of backups and the speed at which it takes to perform a backup.

This is incremental backups at its finest.

The directory structure for backups is much like that of Time Machine:
  
    /path/to/backupDisk/
        Backups.backupsdb/
            Name-of-Computer/
                YYYY-MM-DDThh_mm_ss/
                    /files
                YYYY-MM-DDThh_mm_ss
                    /files
                YYYY-MM-DDThh_mm_ss
                    /files
                Latest/
                    --Link to newest backup directory


where YYYY-MM-DDThh\_mm\_ss indicates the year, month, day, hour, minute, and
second of a given backup and Latest is a link to the newst backup.

When a backup is inprogress, the directory will have `.inprogress` appended to
the name. After backup is complete, `.inprogress` is removed.


## Automatic backups

To enable automatic backups, simply run the GUI program and click the button
that says `Automatic Backup: Disabled`. This will install a job to crontab that
runs every hour. The button label will switch to `Automatic Backup: Enabled`.

