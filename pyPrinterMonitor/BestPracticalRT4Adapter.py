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
    Created on Jan 19, 2012

    @author: jjm20
'''



''' 
    ####################################
    # Requirements for the Config file #
    ####################################
    
    QueueHost - the host name for the RabbitMQ server
    QueueName - The RabbitMQ Queue that will be connected to
    RTHost - The host name of the RT server
    RTUser - The username of the user that is used to access the RT REST API
    RTUserPass - the password fo the REST API user
    RTQueueId - The RT queue that messages should be forwarded to.

'''




configInfo = {}

def __callback(ch, method, properties, body):
    
    '''
        This is the callback function that is called when a message is delivered to the message queue
        IT SHOULD NOT BE CALLED DIRECTLY
        
        In this implementation we are forwarding these messages into the RT queue specified in the configuration file
    
    '''
    from rtkit.resource import RTResource
    from rtkit.authenticators import CookieAuthenticator
    from rtkit.errors import RTResourceError
    
    from rtkit import set_logging 
    import logging
    set_logging('error')
    logger = logging.getLogger('rtkit')
    
    auth = CookieAuthenticator(configInfo['RTUser'], configInfo['RTUserPass'])
    resource = RTResource('%s/REST/1.0/' % (configInfo['RTHost'],), auth)
    
    
    content = {'content':   {
                                'Queue': configInfo['RTQueueId'],
                                'Subject' : body,
                            }
               }
    try:
        response = resource.post(path='ticket/new', payload=content,)
        logger.info(response.parsed)
    except RTResourceError as e:
        logger.error(e.response.status_int)
        logger.error(e.response.status)
        logger.error(e.response.parsed)
    
def main():
    '''
        Checks that the required command line arguments are passed in, then 
        reads the config file specified in the command line argument, and uses it to
        setup a connection and callback to a RabbitMQ queue using pika.
    '''
    global configInfo
    import argparse
    
    
    parser = argparse.ArgumentParser(description='Description of your program')
    parser.add_argument('-c','--config', help='The configuration file to be used', required=True)
    args = vars(parser.parse_args())

    configFile = args['config']
    
    #load the config
    configContents = open(configFile,'r')
    import yaml
    configInfo = yaml.load(configContents)
    configContents.close()
    
    
    import pika
    
    connection = pika.BlockingConnection(pika.ConnectionParameters(
        host=configInfo['QueueHost']))
    channel = connection.channel()
    channel.queue_declare(queue=configInfo['QueueName'])
    channel.basic_consume(__callback,
                          queue=configInfo['QueueName'],
                          no_ack=True)
    channel.start_consuming()

            
            






if __name__ == '__main__':
    main()
    