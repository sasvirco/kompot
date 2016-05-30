#!/usr/bin/python

import json
import logging
import yaml
import sys
import argparse
import time
import csaservice as csa


def main () :
	levels = {
		'debug': logging.DEBUG,
		'info': logging.INFO,
		'warning': logging.WARNING,
		'error': logging.ERROR,
		'critical': logging.CRITICAL
	}

	parser = argparse.ArgumentParser(description = 'Kompot - CSA Subscription tester')
	parser.add_argument('--loglevel', default = 'INFO', help='FATAL, ERROR, WARNING, INFO, DEBUG')
	parser.add_argument('--trustcert', action='store_true', help='Trust self-signed certs')
	parser.add_argument('--logfile', default = "kompot.log", help='Logfile to store messages (Default: kompot.log)')
	parser.add_argument('--exitonfail', action='store_true', help='Exit if one of the tests fail')
	parser.add_argument('--delay', default = 15, help='Delay in seconds between every request')
	parser.add_argument('--quiet', action='store_true', help="Don not print to stderr")
	parser.add_argument('--configfile', default="kompot.yaml", help="Config file in json format")
	parser.add_argument('--heartbeat', default=120, help="How often to query CSA for status")
	parser.add_argument('--timeout', default=3600, help="How long to wait for all subscription to finish")
	parser.add_argument('--configfmt', default="yaml", help="Config format - yaml, json")
	parser.add_argument('--delete', action='store_true', help='Delete all subscriptions')
	parser.add_argument('--outputfolder', default="/temp/tests", help='Folder to print instance document')

	args = parser.parse_args()

	loglevel = levels.get(args.loglevel, logging.NOTSET)
	logging.basicConfig(
		level= args.loglevel,
		format='%(asctime)s %(name)s %(levelname)s %(message)s',
		datefmt='%y-%m-%d %H:%M',
		filename= args.logfile,
		filemode='a')

	root = logging.getLogger()
	
	if args.quiet is not True :
		consoleHandler = logging.StreamHandler()
		consoleHandler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
		root.addHandler(consoleHandler)

	root.info('Brewing kompot')

	config = "" #config
	
	if args.configfile :
		config = parse_config(args.configfile, args.configfmt)
	
	config['general']['trustcert'] = args.trustcert
	config['general']['exitonfail'] = args.exitonfail
	config['general']['delete'] = args.delete

	services = {
		'pending' : [],
		'active' : [],
		'failed' : [],
		'canceled' : []
	}

	for order in config['orders'] :
		svc = csa.csaservice(config['general'], order)
		svc.subscribe()

		if svc.error is None :
			services['pending'].append(svc)
    
    	time.sleep(int(args.delay))

	timeout = int(args.timeout)
	heartbeat = int(args.heartbeat)
    
	while timeout >= heartbeat :
		root.info('Checking subscription status')
		for s in services['pending'][:] :
			status = s.get_subscription_status()
			
			if status == 'ACTIVE' :
				services['active'].append(s)
				services['pending'].remove(s)
				
			if status == 'FAILED' or status == 'TERMINATED' :
				services['failed'].append(s)
				services['pending'].remove(s)

			root.debug(services)
			root.info("Subscription %s status is %s", s.subscription_name, status)

		if len(services['pending']) == 0 :
			root.info("Subscription pending list is zero")
			break

		root.info('sleeping for %s seconds', str(heartbeat))
		timeout = timeout - heartbeat
		time.sleep(heartbeat)

	for svc in services['active'] :
		svc.cancel()
		time.sleep(int(args.delay))
		if args.delete is True:
			svc.delete()

	for svc in services['failed'] :
		svc.cancel()
		time.sleep(int(args.delay))
		if args.delete is True :
			svc.delete()

	if len(services['failed']) > 0 and args.exitonfail is True:
		root.error("Some services had failed and exitonfail is %s", str(args.exitonfail))
		sys.exit(2)

def parse_config(configfile, configfmt) :
	log = logging.getLogger()
	log.info("Parse configuration")
	
	f = open(configfile, "r+")

	if configfmt == "yaml" :
		configuration = yaml.load(f.read())
	else :
		configuration = json.loads(f.read())

	f.close
	
	log.debug(configuration)
	return configuration

if __name__ == "__main__":
	main()
