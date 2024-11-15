#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python script to change the frequency of the radio using JS8Call Monitor.

If JS8Call Monitor is running on a remote host, you will need to adjust the
radio varible to point at the external interface of this host. This value has
to match what JS8Call Monitor is seeing reported in the PING event and saving
to the RADIO database.

version 0.1
"""
import socket
import sys
import json

# Configuration variables.
monitorhost = "127.0.0.1"
monitorport = "2217"
token = "fixme"
dial = 14078000
offset = 2000
radio = "127.0.0.1"

# build packet
data = {
    'params':{'DIAL':dial,'OFFSET':offset,'RADIO':radio,'AUTH':token},'type':'RIG.SET_FREQ','value':''
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
