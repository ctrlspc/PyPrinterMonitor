'''
Created on Jan 11, 2012

@author: jjm20
'''


import pika

connection = pika.BlockingConnection(pika.ConnectionParameters(
        host='localhost'))
channel = connection.channel()

channel.queue_declare(queue='RT_Events_q')

print ' [*] Waiting for messages. To exit press CTRL+C'

def callback(ch, method, properties, body):
    print " [x] Received %r" % (body,)

channel.basic_consume(callback,
                      queue='RT_Events_q',
                      no_ack=True)

channel.start_consuming()