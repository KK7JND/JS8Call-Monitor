#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python script to perform grid notifications via JS8Call Monitor to APRS gateway.

If JS8Call Monitor is running on a remote host, you will need to adjust the
radio varible to point at the external interface of this host. This value has
to match what JS8Call Monitor is seeing reported in the PING event and saving
to the RADIO database.

Note: uses parameters passed on the command line
p1=grid

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
##grid = "EM73TV53"

# check command line arguments passed
if not len(sys.argv) == 2:
    print('2001')
    print('Missing required gateway parameter(s).')
    sys.exit(0)

grid = sys.argv[1]

# build packet
messageString = "@APRSIS GRID " + grid
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
