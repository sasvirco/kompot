# Kompot
Kompot is a tool for subscribing to [Cloud Service Automation](https://en.wikipedia.org/wiki/HP_Cloud_Service_Automation_Software) offers. It was designed to be run from command line, and be used from CI tools like Jenkins. It's original purpose was to run offers tests when building new oo content packs that deploy csa services.

# Current state

Kompot is in **alpha stage**, currently only able to subscribe to a service, and either fail or succeed, depending on the success of the subscription. It cancels the subscription after its done and if delete options is provided, can also delete them.

# Options
```
Kompot - CSA Subscription tester

optional arguments:
  -h, --help            show this help message and exit
  --loglevel LOGLEVEL   FATAL, ERROR, WARNING, INFO, DEBUG
  --trustcert           Trust self-signed certs
  --logfile LOGFILE     Logfile to store messages (Default: kompot.log)
  --exitonfail          Exit if one of the tests fail
  --delay DELAY         Delay in seconds between every request
  --quiet               Don not print to stderr
  --configfile CONFIGFILE
                        Config file in json format
  --heartbeat HEARTBEAT
                        How often to query CSA for status
  --timeout TIMEOUT     How long to wait for all subscription to finish
  --configfmt CONFIGFMT
                        Config format - yaml, json
  --delete              Delete all subscriptions
  --outputfolder OUTPUTFOLDER
                        Folder to print instance document

```

- quiet - By default Kompot prints detailed logs in both logfile and console. The quiet option will suppress stdout messages.
- outputfolder - that is the folder, where the test results will be stored. it is not used currently
- delay - that option is used to not flood csa with numerous api calls. It is used for odering and canceling services, and is the time to wait between the api calls. Defaults to 15 seconds.
- heartbeat - when orders are requested, Kompot will wait until the requests either fail or are online. The heartbeat defines on what intervals Kompot will check what is the current status of it's subscriptions. Defaults to 120 seconds.
- timeout - How long kompot should wait for subscription to fail or succeed, before it gives up. Note, that still running subscriptions that timeout will be ignored from the final result and manual cleanup should be attempted. Defaults to 3600 seconds(1h).
- delete  - if that option is specified, subscriptions that have been active or failed will be deleted after they are canceled.
- exitonfail - if that option is specified, script will exit at the end with a non-zero status if any of the orders had failed
- trustcert - trust the ssl certificates, usefull with self-signed ones
- loglevel - defines the verbosity of the logs. Info provides information about what is currently going on, while DEBUG prints very detailed requests and reponses, very usefull with identifying issues.

The rest are self-explanatory.

# Config file

The configfile can be either in json or yaml format. It includes 2 objects. General, where the url for the csa service, api and consumer information is defined, and the orders, that contains an array of objects where information about the orders we want to make resides.

### Example in yaml 

```
---
  general: 
    host: "10.10.0.11:8444"
    apiusername: "idmTransportUser"
    apipassword: "cloud"
    tenantName: "CSA_CONSUMER"
    credentials: 
      username: "consumer"
      password: "cloud"
  orders: 
    - 
      subscriptionPrefix: "test_"
      offeringName: "TSS Cloud Server v1.0"
      offeringVersion: "1.0.1"
      name: "test cloud server"
      serviceOptions: 
        disk: "0"
        hostName: "test4@rslab.local"
        failFlow: "false"
        osType: "RedHat 7"
        memory: "1024"
        nCPU: "2"
      deployedProperties :
        hostName: "test4@rslab.local"
        joinedDomain: true
    - 
      subscriptionPrefix: "test_"
      offeringName: "TSS Cloud Server v1.0"
      offeringVersion: "1.0.0"
      name: "test cloud server2"
      serviceOptions: 
        disk: "0"
        hostName: "test4@rslab.local"
        failFlow: "true"
        osType: "RedHat 7"
        memory: "1024"
        nCPU: "2"
```

# Configuration options
## eneral 
- host - hostname and port (TODO: change it to separate entries for protocol, host and port)
- apiusername - the username used to connect to the consumer api
- apipassword  - the password for the user used to connect to the consumer api
- tenantName - contains the tenant (csa organization) to log into
- credentials - object containing username and password to use for odering the subscription
      username: "consumer"
      password: "cloud"

## Order 
- subscriptionPrefix - prefix used for subscriptions in CSA 
- offeringName - the name offer we want to order
- offeringVersion - the version of the offer, if not specified the last one the api returns is used if offer has multiple versions
- name - name of the test case, currently not used and subject of change
- serviceOptions - list of names and values of the subscriber options we want to supply to the offer. The internal names of the subscriber options are used.
- deployedProperties - list of properties and values, we want to assert after succesfull subscription. Not used currently and subject of change

# future state

The following features are considered for next releases
- produce a report file, similar to Junit
- checks for specific property values after succesfull deployment
- support for diferent catalogs
- lifecycle actions support
