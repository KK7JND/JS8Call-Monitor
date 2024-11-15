#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python script to perform email notifications via JS8Call Monitor to APRS gateway.

If JS8Call Monitor is running on a remote host, you will need to adjust the
radio varible to point at the external interface of this host. This value has
to match what JS8Call Monitor is seeing reported in the PING event and saving
to the RADIO database.

Note: uses parameters passed on the command line
p1=dest p2=message

version 0.1
"""
import socket
import sys
import json
import ctypes

# Configuration variables.
monitorhost = "127.0.0.1"
monitorport = "2217"
token = "fixme"
radio = "127.0.0.1"
##dest = "test@email.com"
##message = "Hello World!"

# check command line arguments passed
if not len(sys.argv) == 3:
    print('2001')
    print('Missing required gateway parameter(s).')
    sys.exit(0)

dest = sys.argv[1]
message = sys.argv[2]

# build packet
messageString = "@APRSIS CMD :EMAIL-2  :" + dest + " " + message + "{03}"
data = {
    'params':{'RADIO':radio,'AUTH':token},'type':'TX.SEND_MESSAGE','value':messageString
}
send_buffer = json.dumps(data, sort_keys=False, indent=None)

# now send the contents of send_buffer to JS8Call Monitor
try:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.connect((monitorhost,int(monitorport)))          
    sock.send(send_buffer.encode('utf-8'))
except KeyboardInterrupt:
    sys.stderr.write("User cancelled.")
    sock.close()
    sys.exit(0)
