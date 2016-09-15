#This is a list of script specific modules that we are importing
import os
import sys
import getpass
import datetime
import pyping
import colorama

from termcolor import colored
from termcolor import cprint
from lxml import etree

from jnpr.junos import Device
from jnpr.junos.utils.config import Config
from jnpr.junos.exception import *
from jnpr.junos.facts import *

# This points to the location of an IP list
location = raw_input("""

Select location: """)


# Used to bring color to the sad/dead console of a windows machine
colorama.init()

def bold_green(x):
	""" prints the contents of 'x' in bold green color """
	return cprint(x, 'green', attrs=['bold'])
def green(x):
	""" prints the contents of 'x' in light green color """
	return cprint(x, 'green')
def yellow(x):
	""" prints the contents of 'x' in bold yellow color """
	return cprint(x, 'yellow', attrs=['bold'])
def red(x):
	""" prints the contents of 'x' in bold red color """
	return cprint(x, 'red', attrs=['bold'], file=sys.stderr)

#The username is specified here and you will be prompted for a password.
#getpass.getuser
username = raw_input('Username:')
password = getpass.getpass("Password:")

fail_log = 'junos-config-change-error-report-{0}.txt'.format(location)

#This is the 'out-file' that the script writes results to
f = open('junos-config-change-results-{0}.txt'.format(location), 'w')

fail = open(fail_log, 'a')

#The main function 'update_config' is defined below
def update_config(host):

	def date_time():
		date = str(datetime.datetime.now())
		return date

	# This function has been known to cause timeout errors and is probably not the best way to get the location
	def snmp_location():
		data = dev.rpc.get_config()
		location = data.xpath('//location')
		locationstring = etree.tostring(location[0])
		locationstrip = locationstring.replace("<location>", "").replace("</location>\n", "")
		return locationstrip

	model = dev.facts['model']

	f.write("-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-" + '\n')
	f.write("Working on: " + host + '\n')
	f.write(snmp_location() + '\n')
	print "Working on:", host
	print snmp_location()
	f.write(date_time() + '\n')
	print datetime.datetime.now()
	print "Model:", model 
	f.write("Model: " + model + '\n')

	#This binds Config to dev
	cu = Config(dev)

	hostname = dev.facts['hostname']

	#This is where the ping function is defined. This function is used later in the script to test connectivity to the SRX
	def pingtest(host):
		r = pyping.ping(host.strip())
		if r.ret_code is 0:
			return True
		else:
			return False
	
    #This is where the Juniper 'set' commands are defined. These are used to apply the configuration changes
	set_commands = """
	set system scripts op file sit.slax description "null"
	"""

	f.write("Locking the configuration..." + '\n')
	print "Locking the configuration..."
    
	#This command locks the configuration for a 'configure exclusive'
	try:
		cu.lock()
		f.write("Configuration locked" + '\n')
		green("Configuration locked")
	except (KeyboardInterrupt, SystemExit):
		raise
	except LockError as err:
		f.write("Error: Unable to lock configuration: {0} ".format(err) + '\n')
		red("Error: Unable to lock configuration...")

	f.write("Checking for uncommitted configuration changes..." + '\n')
	print "Checking for uncommitted configuration changes..."

	#This command is the equivilant of 'show | compare'
	if cu.diff() == None:
		f.write("There are no uncommitted changes" + '\n')
		green("There are no uncommitted changes")
	else:
		f.write("There are uncommitted changes...rolling back..." + '\n')
		yellow("There are uncommmitted changes...rolling back...")
		try:
			cu.rollback(rb_id=0) #This command issues a rollback. 'rb_id=' is the rollabck number: 0 - 5
			f.write("Configuration has been rolled back to 0" + '\n')
			f.write("Locking configuration..." + '\n')
			green("Configuration has been rolled back!")
			try:
				f.write("Double checking 'show | compare'" + '\n')
				print "Double checking 'show | compare'"
				if cu.diff() == None:
					try:
						print "Locking configuration..."
						cu.lock() #This command is used to lock the configuration in the event that the first
						f.write("Configuration locked" + '\n') #configuiration lock failed due to uncommitted configuration changes
						print "Configuration locked" 
					except (KeyboardInterrupt, SystemExit):
						raise
					except LockError as err:
						f.write("Unable to lock configuration: {0} ".format(err) + '\n')
						red("Error: Unable to lock configuration!")
						f.write("Exiting this device immediately!" + '\n')
						print "Exiting this device immediately!"
						return
				else:
					fail.write("There were problems removing the pending configuration changes on " + hostname + '\n')
					f.write("There were problems removing the pending configuration changes" + '\n')
					f.write("Exiting now..." + '\n')
					print "There were problems removing the pending configuration changes"
					print "Exiting now"
					return

			except (KeyboardInterrupt, SystemExit):
				raise
			except:
				fail.write("There were probelms running 'show | compare' on " + hostname + '\n')
				f.write("There were errors running 'show | compare' " + '\n')
				f.write("Exiting device immediately" + '\n')
				print "There were errors running 'show | compare' "
				print "Exiting now"
				return

		except (KeyboardInterrupt, SystemExit):
			raise
		except:
			fail.write("Failed to rollback on " + hostname + '\n')
			f.write("Failed to rollback..." + '\n')
			f.write("Exiting this device" + '\n')
			print "Failed to rollback..."
			print "Exiting this device"
			dev.close()
			return

	f.write("Loading the configuration changes..." + '\n')
	print "Loading the configuration changes..."

	#This command loads the configuration changes. The 'merge=False' parameter means it will overwrite existing configurations
	try:
		cu.load(set_commands,format='set',merge=False)
	except (KeyboardInterrupt, SystemExit):
		raise
	except ValueError as err:  
		fail.write("Failed to load configuration changes {0} ".format(err) + '\n')                         
		f.write("Loading the configuration changes failed: {0} ".format(err) + '\n') 
		f.write("Exiting the device" + '\n')                       
		red(err.message) 
		return

	try:
		f.write("Checking commit..." + '\n')
		print "Checking commit..."
		cu.commit_check()
		f.write("Commit check passed" + '\n')
		print "Commit check passed with 0 errors"
	except CommitError as err:
		fail.write("Commit check did NOT pass {0} ".format(err) + '\n')
		f.write("Commit check did NOT pass! {0} ".format(err) + '\n')
		print "Commit check did NOT pass! Check log file for more"
		return
	except RpcError as err:
		fail.write("Commit check did NOT pass {0} ".format(err) + '\n')
		f.write("Commit check did NOT pass! {0} ".format(err) + '\n')
		print "Commit check did NOT pass! Check log file for more"
		return

	f.write("Committing the configuration..." + '\n')
	print "Committing the configuration changes..."

	#This command commits the config with a comment and 1 minute to confirm
	try:
		cu.commit(confirm=1)
		f.write("Commit confirm 1 successful!" + '\n')
		bold_green("Commit confirm 1 successful!"),
		print "Verifying connectivity..."
	except (KeyboardInterrupt, SystemExit):
		raise
	except CommitError as err:
		fail.write("Commit failed or broke connectivity: {0} ".format(err) + '\n')
		f.write("Commit failed or broke conectivity: {0} ".format(err) + '\n')
		f.write("Pinging to verify..." + '\n')
		red("Commit failed or broke connectivity")
		print "Pinging to verify..."
	except RpcTimeoutError as err:
		fail.write("Commit failed or broke connectivity: {0} ".format(err) + '\n')
		f.write("Commit failed or broke conectivity: {0} ".format(err) + '\n')
		f.write("Pinging to verify..." + '\n')
		red("Commit failed or broke connectivity")
		print "Pinging to verify..."

	#This command is used to ping the host to see if applying the configuration broke the connectivity
	if pingtest(host) is True:  
		f.write(host.strip() + " looks up from here" + '\n')
		f.write("Confirming the configuration..." + '\n')
		print host.strip() ,"Looks UP from here"
		print "Confirming the configuration..."
		try:
			cu.commit(comment="junos-rootpswd-change") #If the ping succeeds it issues a 'commit confirm'
			f.write("Configuration was confirmed!" + '\n')
			f.write("Unlocking the configuration..." + '\n')
			bold_green("Configuration was confirmed!") 
			print "Unlocking the configuration..."                                          
			try:
				cu.unlock() #This command unlocks the configuration
			except (KeyboardInterrupt, SystemExit):
				raise
			except UnlockError as err:
				f.write("Unlocking the configuration failed: {0} ".format(err) + '\n')
				red("Unlocking the configuration failed")

			f.write("Closing connection to " + hostname + '\n')
			print "Closing the connection to", hostname
			try:
				dev.close() #This command closes the device connection 
			except (KeyboardInterrupt, SystemExit):
				raise
			except:
				f.write("Failed to close " + hostname + '\n')
				print "Failed to close", hostname

		except (KeyboardInterrupt, SystemExit):
			raise
		except CommitError as err:
			fail.write("Commit failed: {0} ".format(err) + '\n')
			f.write("Failed to commit changes: {0} ".format(err) + '\n')
			print "Failed to commit the changes"
		except RpcTimeoutError as err:
			print "RPC timeout error!"
			f.write("RPC timeout error!" + '\n')
			fail.write("RPC timeout error!" + '\n')
	else:  #This detects ping failure. If the ping fails, the script will exit the current host without confirming
		f.write(host.strip() + " looks DOWN from here..." + '\n') #the commit and the configuration will rollback in 1 minute
		fail.write(host + "looks down from here" + '\n')
		f.write("Moving on to the next host..." + '\n')        
		print host ,"looks down from here..."
		print "Moving on to the next host..."

	f.write("Completed: " + hostname + '\n' )
	f.write("-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-_-" + '\n')
	f.write('\n')
	print "Completed:", hostname 
	print ""

#This is used to loop through every host entry in the list specified
with open('C:\\ip_lists/{0}-list.txt'.format(location)) as infile:  
	for host in infile:

		#This is used to test connectivity to a host before attempting to connect
		dev = Device(host=host.strip(), user=username, password=password) #change pass function
		try:
			dev.open()                                                     
		except (KeyboardInterrupt, SystemExit):
			raise
		except ConnectError as err:
			fail.write("Error: Cannot connect to device {0} ".format(err) + '\n')                                           
			f.write("Error: Cannot connect to device: {0} ".format(err) + '\n')
			yellow("Error: Cannot connect to device: {0} ".format(err))
			continue
		update_config(host)

f.close()
fail.close()

if os.path.getsize(fail_log) == 0:
	os.remove(fail_log)
