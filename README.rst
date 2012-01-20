Overview
========

This is a library-in-progress, developed by Jason Marshall from the School of Psychology at the University of Kent, UK

It is being written so that we can remotely monitor our networked printers using SNMP, and send warning to our ticket management system.
To give us flexibility we are not going to send messages directly to our TMS (we are currently using RT) but to a RabbitMQ message queue,
we will then have a daemon that will pull messages from this queue and stick them in the TMS.

This library is far from complete at the moment, and there will be significant changes in the future, not least packaging it properly

News
====

18-Jan-2012 v.0.0.2 pushed - This includes a working adapter for consuming RabbitMQ messages and pushing them into RT using the REST API
11-Jan-2012 v.0.0.1 pushed - This is the first working increment of the library, but it is far from shippable.

External Module Dependencies:
-----------------------------
pysnmp - http://pysnmp.sourceforge.net/
yaml - http://pyyaml.org/
pika - https://github.com/pika/pika


Installation
============

Todo - haven't gotten around to packaging the script yet but hopefully soon.

Configuration Files
===================

PrinterMonitor
--------------

Currently the idea is that the PrinterMonitor will be setup to run as a cron job (we are running it every 5mins). It can be run from the 
command line with something like:

::
python PrinterMonitor --config <your-config-file> --loggingLevel INFO --loggingFile <you-log-file>

The loggingLevel is optional and defaults to WARNING
The loggingFile is optional and if not specified will default to writting the log to stdout
The config file is mandatory, an example of the minimum required for configurtion is:

printers:
    <your printer name>:
        address: <your printer host name or ip4 address>
        toners:
            low: 5
            empty: 1
mq:
    host:
        <the host that is running rabbitmq>
    queue:
        <the name of your rabbitmq queue>
PersistanceFile:
    previousState.pkl       
The BestPracticalRT4Adapter will block waiting for messages to arrive in the queue so it can be run once and left, but it would be advisable to have a 
script that checks that the process is still alive every once in a while.

::
python BestPracticalRT4Adapter --config <your config file>

The config file is mandatory and the following is an example of what is required at a minimum:

QueueHost:
    <the location of the rabbitMq server>
QueueName:
    <the name of the rabbit mq queue to consume from>
RTHost:
    <your RT host>
RTUser:
    <the RT user that has access to the REST API>
RTUserPass:
    <that users password>
RTQueueId:
    <the RT queue id>


