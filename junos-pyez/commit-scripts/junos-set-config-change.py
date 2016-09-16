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

# This points to the location of an IP list. See line 272
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
username = raw_input('Username:')
password = getpass.getpass("Password:")

fail_log = 'junos-config-change-error-report-{0}.txt'.format(location)

#This is the 'out-file' that the script writes results to
log = open('junos-config-change-results-{0}.txt'.format(location), 'w')

fail = open(fail_log, 'a')

#The main function 'update_config' is defined below
def update_config(host):
	""" This is our main function """

	def date_time():
		""" this function returns a readable time stamp """
		date = str(datetime.datetime.now())
		return date

	def error_message():
		""" this function displays an error message """
		return "Error: {0}".format(err)

	# This function has been known to cause timeout errors and is probably not the best way to get the location
	def snmp_location():
		""" this function grabs the location information from SNMP """ 
		data = dev.rpc.get_config()
		location = data.xpath('//location')
		locationstring = etree.tostring(location[0])
		locationstrip = locationstring.replace("<location>", "").replace("</location>\n", "")
		return locationstrip

	model = dev.facts['model']

	log.write("-_-_-_-_-_-_-_\nWorking on: " + host + '\nLocation :' + snmp_location() + '\n')
	log.write("Timestamp: " + date_time() + "\nModel: " + model + '\n')
	print("Working on: " + host)
	print("Location: " + snmp_location())
	print("Timestamp: " + date_time())
	print("Model: " + model) 

	#This binds Config to dev
	cu = Config(dev)

	hostname = dev.facts['hostname']

	#This is where the ping function is defined. This function is used later in the script to test connectivity to the SRX
	def pingtest(host):
		""" this function pings a host and returns true or false (response or drop) """
		r = pyping.ping(host.strip())
		if r.ret_code is 0:
			return True
		else:
			return False
	
    #This is where the Juniper 'set' commands are defined. These are used to apply the configuration changes
	set_commands = """
	set system scripts op file sit.slax description "null"
	"""

	log.write("Locking the configuration..." + '\n')
	print("Locking the configuration...")
    
	#This command locks the configuration for a 'configure exclusive'
	try:
		cu.lock()
		log.write("Configuration locked" + '\n')
		green("Configuration locked")
	except (KeyboardInterrupt, SystemExit):
		raise
	except LockError as err:
		log.write(error_message() + '\n')
		red(error_message())

	log.write("Checking for uncommitted configuration changes..." + '\n')
	print("Checking for uncommitted configuration changes...")

	#This command is the equivilant of 'show | compare'
	if cu.diff() == None:
		log.write("There are no uncommitted changes" + '\n')
		green("There are no uncommitted changes")
	else:
		log.write("There are uncommitted changes...rolling back..." + '\n')
		yellow("There are uncommmitted changes...rolling back...")
		try:
			cu.rollback(rb_id=0) #This command issues a rollback. 'rb_id=' is the rollabck number: 0 - 5
			log.write("Configuration has been rolled back to 0\nLocking configuration...\n")
			green("Configuration has been rolled back!")
			try:
				log.write("Double checking 'show | compare'\n")
				print("Double checking 'show | compare'")
				if cu.diff() == None:
					try:
						print("Locking configuration...")
						cu.lock() #This command is used to lock the configuration in the event that the first
						log.write("Configuration locked\n") #configuiration lock failed due to uncommitted configuration changes
						print("Configuration locked") 
					except (KeyboardInterrupt, SystemExit):
						raise
					except LockError as err:
						log.write(error_message() + '\n')
						red(error_message())
						log.write(error_message() + '\n')
						print(error_message())
						return
				else:
					fail.write("There were problems removing the pending configuration changes on " + hostname + '\n')
					log.write("There were problems removing the pending configuration changes\nExiting now...\n")
					print("There were problems removing the pending configuration changes")
					print("Exiting now")
					return

			except (KeyboardInterrupt, SystemExit):
				raise
			except Exception as err:
				fail.write(error_message() + '\n')
				log.write(error_message() + "\nExiting device immediately\n")
				print(error_message() + "\nExiting now")
				return

		except (KeyboardInterrupt, SystemExit):
			raise
		except Exception as err:
			fail.write(error_message() + '\n')
			log.write(error_message() + "\nExiting device immediately\n")
			print(error_message() + "\nExiting now")
			dev.close()
			return

	log.write("Loading the configuration changes..." + '\n')
	print("Loading the configuration changes...")

	#This command loads the configuration changes. The 'merge=False' parameter means it will overwrite existing configurations
	try:
		cu.load(set_commands,format='set',merge=False)
	except (KeyboardInterrupt, SystemExit):
		raise
	except ValueError as err:  
		fail.write(error_message() + '\n')                         
		log.write(error_message() + "\nExiting device immediately\n")                        
		red(error_message()) 
		return

	try:
		log.write("Checking commit...\n")
		print("Checking commit...")
		cu.commit_check()
		log.write("Commit check passed\n")
		print("Commit check passed with 0 errors")
	except CommitError as err:
		fail.write(error_message() + '\n')
		log.write(error_message() + '\n')
		print(error_message())
		return
	except RpcError as err:
		fail.write(error_message() + '\n')
		log.write(error_message() + '\n')
		print(error_message())
		return

	log.write("Committing the configuration...\n")
	print("Committing the configuration changes...")

	#This command commits the config with a comment and 1 minute to confirm
	try:
		cu.commit(confirm=1)
		log.write("Commit confirm 1 successful!\n")
		bold_green("Commit confirm 1 successful!"),
		print("Verifying connectivity...")
	except (KeyboardInterrupt, SystemExit):
		raise
	except CommitError as err:
		fail.write(error_message() + '\n')
		log.write(error_message() + "\nPinging to verify...\n")
		red(error_message())
		print("Pinging to verify...")
	except RpcTimeoutError as err:
		fail.write(error_message() + '\n')
		log.write(error_message() + "\nPinging to verify...\n")
		red(error_message())
		print("Pinging to verify...")

	#This command is used to ping the host to see if applying the configuration broke the connectivity
	if pingtest(host) is True:  
		log.write(host.strip() + " looks up from here\nConfirming the configuration...\n")
		print(host.strip() + " looks UP from here\nConfirming the configuration...")
		try:
			cu.commit(comment="junos-rootpswd-change") #If the ping succeeds it issues a 'commit confirm'
			log.write("Configuration was confirmed!\nUnlocking the configuration...\n")
			bold_green("Configuration was confirmed!") 
			print("Unlocking the configuration...")                                          
			try:
				cu.unlock() #This command unlocks the configuration
			except (KeyboardInterrupt, SystemExit):
				raise
			except UnlockError as err:
				log.write(error_message() + '\n')
				red(error_message())

			log.write("Closing connection to " + hostname + '\n')
			print("Closing the connection to " + hostname)
			try:
				dev.close() #This command closes the device connection 
			except (KeyboardInterrupt, SystemExit):
				raise
			except:
				log.write("Failed to close " + hostname + '\n')
				print("Failed to close " + hostname)

		except (KeyboardInterrupt, SystemExit):
			raise
		except CommitError as err:
			fail.write(error_message() + '\n')
			log.write(error_message() + '\n')
			print(error_message())
		except RpcTimeoutError as err:
			print(error_message())
			log.write(error_message() + '\n')
			fail.write(error_message() + '\n')
	else:  #This detects ping failure. If the ping fails, the script will exit the current host without confirming
		log.write(host.strip() + " looks DOWN from here...\n") #the commit and the configuration will rollback in 1 minute
		fail.write(host + "looks down from here\n")
		log.write("Moving on to the next host...\n")        
		print(host + " looks down from here...")
		print("Moving on to the next host...")

	log.write("Completed: " + hostname + '\n' )
	log.write("-_-_-_-_-_-_-_\n\n")
	print("Completed: " + hostname + "\n\n") 

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
			fail.write(error_message() + '\n')                                           
			log.write(error_message() + '\n')
			yellow(error_message())
			continue
		update_config(host)

log.close()
fail.close()

if os.path.getsize(fail_log) == 0:
	os.remove(fail_log)
