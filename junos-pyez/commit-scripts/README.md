# Junos Configuration Change
This script applies configuration changes to Junos devices. 

## Overview

This script uses `set` commands to apply configuration changes to the Junos device. There are other methods of applying configuration changes such as XML, .conf files, YAML and Jinja2 Templates but for simplicity this particular script only uses Junos `set` commands.

The "_junos-config-change.py_" file has `#comments` throughout the entire script that briefly explain the purpose of the various commands. 

Below is an example of the standard structure that every script follows.

## Steps
The script loops over a list of IPs and follows these steps to apply configuration changes:

+ Opens a connection to the Junos device using the provided credentials
+ Locks the configuration (`configure exclusive`)
+ Checks for uncommitted changes (`show | compare`)
    - If uncommitted changes are found it clears them (`rollback 0`)
    - After clearing it checks again to ensure there are no pending changes
+ Loads the configuration changes
+ Tests the configuration for obvious syntax errors (`commit check`) 
+ Commits the configuration with 1 minute to confirm (`commit confirm 1`)
+ Tests the connectivity to the Junos device
    - If it has connectivity (the changes didn't break anything) it confirms the commit (`commit`)
    - If it has no connectivity it exits the device and the Junos device will rollback in 1 minute
+ Unlocks the configuration 
+ Closes connection to the Junos device

## Results
The results of the script are printed on the console screen and are also logged to a file. The results file will be named according to what you entered in the `location` variable. The 'Results' folder contains subfolders that hold the results of a particular script and the IR that it relates to.
```python
log = open('junos-config-change-results-{0}.txt'.format(location), 'w') 
```
An error file is also generated at the start of every script run. When a script finishes running it checks the error file to see if it is empty. If the error file is empty the script automatically deletes it. 

The code responsible for creating the error file:
```python
fail_log = 'junos-config-change-error-report-{0}.txt'.format(location)
```
An example of the script output can be viewed by clicking on the "_junos-config-change-results.txt_" file

## Precautions
**This script uses several different safety precautions and has exception handling at every step.**


* The biggest concern is making a configuration change that brings down the Junos device or causes it to lose connection. To safeguard against this the script applies a `commit confirm 1` command. The `commit confirm 1` command applies the configuration changes but sets a rollback timer for 1 minute. If 1 minute passes and you have not issued a `commit` command the Junos device will automatically rollback to the previous configuration. 


* The script also checks to ensure that there are no pending configuration changes before applying it's own configuration changes. 


* It also locks the configuration for a `configure exclusive`. This keeps users from applying changes at the same time the script is applying changes.


* The script also issues a `commit check` command before attempting to commit any changes. The `commit check` command checks the candidate configuration for any obvious syntax errors (it does not safeguard against stupid, yet valid, configuration changes).  


* If the script encounters any major errors it writes the error to the error file and moves on to the next IP address in the IP list. 




