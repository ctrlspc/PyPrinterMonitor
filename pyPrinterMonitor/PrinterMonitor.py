'''

	This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
	Created on Jan 5, 2012

	@author: jjm20
'''

import pickle
config = None
configFile = None

def SnmpWalk(host,oid):
    
    '''
        Wraps the functionlity of the pysnmp library for walking the mib of a device from a specified oid
        
        Keyword arguments:
        host -- Should be the ipv4 address of the host device represented as a string eg. "192.168.0.1"
        oid  -- It can be either a tuple or a string. If it is a string the idividual nodes of the oid must be 
        delimited by dots, with no leading or trailing nodes or non integer values. eg (1,1,1,2,3,4) or "1.1.1.2.3.4"
        
        (This code is fully tested in spec1_7.txt in the docs_with_test folder.)

    '''
    if not isinstance(host, str):
        raise TypeError('The host parameter must be a str')
    
    if not isinstance(oid, str) and not isinstance(oid, tuple):
        raise TypeError('The oid parameter must be either a str or a tuple.')
    
    if isinstance(oid, str):
        #convert it into a tuple
        oid = tuple(int(node) for node in oid.split('.'))
        
    
    from pysnmp.entity.rfc3413.oneliner import cmdgen
    cg = cmdgen.CommandGenerator()
    comm_data = cmdgen.CommunityData('my-manager','public')
    transport = cmdgen.UdpTransportTarget((host,161))
    variables = oid
    errIndication,errStatus,errIndex, result = cg.nextCmd(comm_data,transport,variables)
    
    return (errIndication,errStatus,errIndex, result)


def loadConfig(cfgfile = None):
    '''
        Loads a yaml formatted config file, returning the de-serialised Python object represented by the YAML. The function will also
        save the object in the PrinterMonitor.config variable. Furthermore it will only read the file once, so multiple calls will return the 
        object sored in PrinterMonitor.config if this is not None.
    
        keyword arguments:
        cfgFile -- The filename containing the yaml configuration - if this is not specified the function will try and look up the 
        filename from the PrinterMonitor.configFile module property
        
    '''
    global config
    global configFile
    
    if config != None:
        return config
    
    if cfgfile is None:
        #check to see if there is a filename parameter set
        if configFile == None or configFile == "":
            raise ValueError('No config data nor config file location was available, cannot continue without this data.')
        else:
            cfgfile = configFile
            
    configContents = open(cfgfile,'r')
    import yaml
    config = yaml.load(configContents)
    configContents.close()
    
    if _checkConfig(config):
        return config
    else:
        raise ValueError('The config file was incorrectly formatted. It must contain the host address of at least one printer.')
    
def _checkConfig(configObject):
    '''
        To be correctly formatted the configuration object (the object returned by yaml.load) must be a dictionary. This dictionary should have 
        a key called 'printers', who's value is a dictionary. This dictionary should have at least one key and the value of this key must be a 
        dictionary, and it must at a minimum have a key called 'address', with a string value.
        Each key in the printers dict should be checked that they contain the address key.
        
        keyword arguments:
        configObject -- The object to be testing for compliance to the above.
        
        returns -- True/False if the configuration is correctly formed.
    '''
    
    #Run the configuration Gauntlet
    if(not isinstance(configObject, dict)):
        return False
    else:
        if not 'printers' in configObject:
            return False
        else:
            if len(configObject['printers']) == 0:
                return False
            else:
                for key in configObject['printers']:
                    
                    printer = configObject['printers'][key]
                    
                    if not isinstance(printer, dict):
                        return False
                    else:
                        if not 'address' in printer:
                            return False
                        else:
                            if not isinstance(printer['address'], str):
                                return False
    
    #Well done you are a well formed configuration!
    return True

def GetTonerInformation():
    '''
        Contacts every printer referenced in the configuration file, and gets information on what toners (including Maintenance Kits) are installed
        and what the capacity, and amount remaining for that toner is.
        It is assumed that the PrinterMonitor.loadConfig method will have already been called to initalise the configuration object. As a backup 
        this function calls the loadConfig function again but this relies on the PrinetMonitor.configFile attribute being set if the loadConfig 
        function hasn't been called successfully previously.
        
        returns -- A dictionary with a key for each printer in the configuration. The value of this key is a list of TonerState objects.
    '''
    config = loadConfig()
    dataDict = {}
    for key in config['printers']:
        
        
        printer = config['printers'][key]
        
        if 'toners' in printer:
            #we do want to know about the toners for this printer
            
            #we can either accept an ipaddress or a host name, but if it is a host name then we need to resolve the ipaddress
            
            printerAddress = printer['address']
            
            ipAddress = ''
            import re
            
            ipMatcher = re.match('^(([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])\.){3}([0-9]|[1-9][0-9]|1[0-9]{2}|2[0-4][0-9]|25[0-5])$',printerAddress) 
            
            
            if ipMatcher:
                ipAddress = printerAddress
            else:
                hostMatcher = re.match('^(([a-zA-Z]|[a-zA-Z][a-zA-Z0-9\-]*[a-zA-Z0-9])\.)*([A-Za-z]|[A-Za-z][A-Za-z0-9\-]*[A-Za-z0-9])$', printerAddress)
                
                if hostMatcher:
                    import socket
                    ipAddress = socket.gethostbyname(printerAddress)
            
            errorIndication, errorStatus, errorIndex, result = SnmpWalk(ipAddress, (1,3,6,1,2,1,43,11,1,1))
            
            if errorIndication != None:
                #There was a SNMP error so we need to handle this appropriatley
                
                tonerStateInstance = TonerState(error=True, errorDescription\
                            ='SNMP engine-level error has occured. The Error Status is %d, and the Error Index is %d. The Returned result was %s' % \
                            (errorStatus, errorIndex, str(result)))
                
                dataDict[key] = [tonerStateInstance]
            else:
                #now we need to create TonerState object for each of the objects in the tonersDict
                tonerStateList = []
                gotError = False
                #the snmp call worked ok, but lets not rule out data problems!
                
                tonersDict = {}
                
                def addValueToDict(tonerIndex, key, value):
                    if tonerIndex in tonersDict:
                        tonersDict[tonerIndex][key] = value
                    else:
                        tonersDict[tonerIndex] = {key:value} 
                
                
                    
                for dataRow in result :
                    
                    try:
                        oidTuple = dataRow[0][0].asTuple()
                        if oidTuple[10] == 6:
                            #description
                            addValueToDict(oidTuple[-1], 'description', dataRow[0][1])
                        elif oidTuple[10] == 8:
                            #capacity
                            addValueToDict(oidTuple[-1], 'capacity', dataRow[0][1])
                        elif oidTuple[10] == 9:
                            #remaining
                            addValueToDict(oidTuple[-1], 'remaining', dataRow[0][1])
                    except IndexError:
                        #if we get an index error here then the data is not properly formed!!
                        gotError = True
                    except AttributeError:
                        #This is most likely because the dataRow[0][0] did not return an ObjectName object
                        gotError = True
                
                if len(tonersDict) <= 0 or gotError:
                    #result is not properly formed!
                    tonerStateList.append( TonerState(error=True, errorDescription\
                            ="A Data level error has occured, meaning that we have not got the expected data back from the printer about it's toners. The returned data was %s" % \
                            (str(result))))
                else:
                    for keys in tonersDict:
                        
                        #strip out any null byte at the end of the octetstring, and decode to human readable string
                        if tonersDict[keys]['description'].asNumbers()[-1] == 0:
                            tonersDict[keys]['description'] = tonersDict[keys]['description'].prettyIn(tonersDict[keys]['description'].asNumbers()[:-1])
                        else:
                            tonersDict[keys]['description'] = tonersDict[keys]['description'].asOctets()
    
                        tonerStateList.append(TonerState(tonersDict[keys]['description'], \
                                                         int(tonersDict[keys]['capacity']), \
                                                         int(tonersDict[keys]['remaining'])))   
                
                     
                dataDict[key] = tonerStateList
        else:
            dataDict[key] = None      
        
    return dataDict

def generateTonerAlerts(current, previous):
    '''
    
    '''
    
    config = loadConfig()
    
    for printer in current:
        
        for index in range(len(current[printer])):
            
            currentTonerState = current[printer][index]
            previousTonerState = None
            
            if previous != None and printer in previous:
                previousTonerState = previous[printer][index]
                
            #for each tonerState object in the list
            #get the config object for the current printer
            if 'toners' in config['printers'][printer]:
                tonerThresholds = config['printers'][printer]['toners']
                
                #check for the empty warning first, then if not triggered check for the near empty
                if currentTonerState.getPercentageRemaining() <= tonerThresholds['empty']:
                    if previousTonerState == None or  previousTonerState.getPercentageRemaining() > tonerThresholds['empty']:
                        #we have met the threshold for the first time send the message
                        sendAlert(printer, 'TONER EMPTY WARNING for %s' % (currentTonerState.description))
                elif currentTonerState.getPercentageRemaining() <= tonerThresholds['low']:
                    if previousTonerState == None or  previousTonerState.getPercentageRemaining() > tonerThresholds['low']:
                        #we have met the threshold for the first time send the message
                        sendAlert(printer, 'TONER NEAR EMPTY WARNING for %s' % (currentTonerState.description))
        
        
        
        
    return None
def generateAlerts(currentState):
    
    '''
    '''
    
    
    previousState = None
    
    try:
        previousStateFile = open('previousState.pkl', 'r')
        previousState = pickle.load(previousStateFile)
        previousStateFile.close()
    except IOError as e:
        #the file doesn't exist so we have no previous state to compare to - ho hum.
        pass
    
    generateTonerAlerts(currentState, previousState)
    
    outFile =  open('previousState.pkl', 'w')
    pickle.dump(currentState, outFile)
    outFile.close()
    
def sendAlert(printer,alert):
    
    import pika
    
    config = loadConfig()
    
    if 'mq' in config:
        
        connection = pika.BlockingConnection(pika.ConnectionParameters(config['mq']['host']))
        channel = connection.channel()
        channel.queue_declare(queue=config['mq']['queue'])
        channel.basic_publish(exchange='',
                             routing_key=config['mq']['queue'],
                             body='%s: %s' % (printer,alert)) 


class TonerState():
    '''
        Represents a physical Toner (including maintenance Kits)
        
        public properties:
        
        description - str - The published name of the toner (including its description code)
        capacity - int - The capacity of the toner in arbitary units
        remaining - int - The amount of toner remaining in arbitary units
        error - Boolean - If there was an error getting the data from the printer
        errorDescription - Str - A human readable description of the error that caused the error state.
    '''
    def __init__(self, description = None, capacity = 0 , remaining = 0, error = False, errorDescription = None ):
        self.description = description
        self.capacity = capacity
        self.remaining = remaining
        self.error = error
        self.errorDescription = errorDescription

    def getPercentageRemaining(self):
        '''
            Calculates the percentage remaining in the toner. This is returned as an integer rounded down to the nearest integer.
        '''
        if(self.capacity > 0):
            return int((float(self.remaining)/self.capacity) *100)
        else:
            return 0



if __name__ == '__main__':

    import argparse
    
    
    parser = argparse.ArgumentParser(description='PyPrinterMonitor - uses SNMP to get information from your printers.')
    parser.add_argument('-c','--config', help='The configuration file to be used', required=True)
    args = vars(parser.parse_args())
    
    configFile = args['config']
    loadConfig(configFile)
    currentState = GetTonerInformation()
    generateAlerts(currentState)
    
