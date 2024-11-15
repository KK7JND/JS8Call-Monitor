#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Python adapter to monitor the JS8Call API output stream and examine the various
messages. Looks for usable data and when found, parse it, format it, and write
it as a N1MM logger formatted output stream for consumption by your favorite
N1MM compatible application. This adapter also supports a second output stream
for the GridTracker application that is based on the WSJT-X API/messaging
interfaces. This adapter has been tested on both N1MM+ and GridTracker.

A note about GridTracker; it was developed against the rich messaging interfaces
of WSJT-X. JS8Call on the other hand provides very limited data in it's API
interface. As a result, some of the more advanced features of GridTracker
may not work as expected. I.E GridTracker will not display anything until after
the first JS8Call activity that generates a status update occurs.

JS8Call Monitor version 0.20
"""
import socket
import sys
import os
import time
import configparser
import json
import datetime
import re
import pywsjtx
import requests
import threading
import string
import warnings
import smtplib
from distutils.util import strtobool
from email.mime.text import MIMEText

# Import python version sprecific modules
if sys.version_info.major == 3:
    import queue
elif sys.version_info.major == 2:
    import Queue
else:
    raise NotImplementedError

# Define aliases for python version sprecific functions
if sys.version_info.major == 3:
    def itervalues(d):
        return iter(d.values())
    def iteritems(d):
        return iter(d.items())
    def listvalues(d):
        return list(d.values())
    def listitems(d):
        return list(d.items())
elif sys.version_info.major == 2:
    def itervalues(d):
        return d.itervalues()
    def iteritems(d):
        return d.iteritems()
    def listvalues(d):
        return d.values()
    def listitems(d):
        return d.items()
else:
    raise NotImplementedError

class JS8CallMonitor:
    """ Class JS8CallMonitor """
    # pylint: disable=too-many-instance-attributes
    # These are all required variables.    
    # Configuration variables.
    adif_CLASS = ""
    adif_MY_CNTY = ""
    adif_MY_GRIDSQUARE = ""
    adif_MY_NAME = ""
    adif_OPERATOR = ""
    computer_name = ""
    config = ""
    consolelevel = 0
    logfilelevel = 0
    logfile = ""
    smtpenabled = False
    smtphost = ""
    smtpport = ""
    smtpuser = ""
    smtppass = ""
    mailfrom = ""
    mailto = ""    
    gridfrominfo = False
    gridlength = 6
    mapall = False
    mapcq = False
    mapheartbeat = False
    mapinfo = False
    mapstatusmsg = False
    maplog = False
    mapqso = False
    mapsnr = False
    autoclose = False
    mapnoinfo = ""
    mapnoinfocolor = ""
    mapnoinfoaprs = ""
    mapnopir = ""
    mapnopircolor = ""
    mapnopiraprs = ""
    mapstatus = ""
    mapstatuscolor = ""
    mapstatusaprs = ""
    grid_databases = ""
    fcc_lookup = False
    hamcallcd_lookup = False
    raccd_lookup = False
    local_lookup = False
    local_learn = False
    collect_rejects = False
    callook_lookup = False
    hamcallol_lookup = False
    hamcallol_username = ""
    hamcallol_password = ""
    n1mmenabled = False
    n1mmhost = ""
    n1mmport = ""
    gtenabled = False
    gthost = ""
    gtport = ""
    gsmsgenabled = False
    gsspotenabled = False
    gshost = ""
    gsport = ""
    gsauth = ""
    yaacenabled = False
    yaaclogfile = ""
    adifenabled = False
    adiflogfile = ""
    authenabled = False
    authtoken = ""
    # Debugging constants.
    log_smdr = 1
    log_critical = 2
    log_error = 3
    log_warning = 4
    log_info = 5
    log_entry = 6
    log_parm = 7
    log_debug = 8
    log_hidebug = 9
    log_experimental = 10
    # GridTracket constants.
    MY_WSJTX_ID = "WSJT-X"
    MY_WSJTX_MAX_SCHEMA = 2
    MY_WSJTX_REVISION = 1
    MY_WSJTX_VERSION = 1
    # GridTracker state variables.
    GTS_wsjtx_id = MY_WSJTX_ID
    GTS_dial_frequency = 0
    GTS_mode = ""
    GTS_dx_call = ""
    GTS_report = ""
    GTS_tx_mode = ""
    GTS_tx_enabled = False
    GTS_transmitting = False
    GTS_decoding = False
    GTS_rx_df = 0
    GTS_tx_df = 0
    GTS_de_call = ""
    GTS_de_grid = ""
    GTS_dx_grid = ""
    GTS_tx_watchdog = False
    GTS_sub_mode = ""
    GTS_fast_mode = False
    GTS_special_op_mode = 0
    # Runtime variables.
    adif_ARI_PROV = ""
    adif_ARRL_SECT = ""
    adif_BAND = ""
    adif_CALL = ""
    adif_CHECK = ""
    adif_COMMAND = ""
    adif_COMMENT = ""
    adif_CONTEST_ID = ""
    adif_CQZ = ""
    adif_DIG = ""
    adif_DISTRIKT = ""
    adif_DOK = ""
    adif_FREQ = "0"
    adif_FREQ_RX = ""
    adif_FREQ_TX = ""
    adif_GRIDSQUARE = ""
    adif_HOST = ""
    adif_HOST_IP = ""
    adif_HOST_PORT = ""
    adif_IARU_ZONE = ""
    adif_IOTA = ""
    adif_ITUZ = ""
    adif_KDA = ""
    adif_LAT = ""
    adif_LON = ""
    adif_MODE = ""
    adif_NAME = ""
    adif_NAQSO_SECT = ""
    adif_OBLAST = ""
    adif_OFFSET = "0"
    adif_PFX = ""
    adif_POINTS = ""
    adif_PRECEDENCE = ""
    adif_QSO_COLOR = ""
    adif_QSO_DATE = ""
    adif_QSO_ICON = ""
    adif_QTH = ""
    adif_RADIO = ""
    adif_RADIO_NR = ""
    adif_RDA = ""
    adif_RST_RCVD = "0"
    adif_RST_SENT = "0"
    adif_RX_PWR = ""
    adif_SAC = ""
    adif_SECT = ""
    adif_SECTION = ""
    adif_SRX = ""
    adif_STATE = ""
    adif_STATION = ""
    adif_STATION_CALLSIGN = ""
    adif_STX = ""
    adif_SUBMODE = ""
    adif_TIME_OFF = ""
    adif_TIME_ON = ""
    adif_TX_PWR = ""
    adif_UKEI = ""
    adif_VE_PROV = ""
    adif_WWPMC = ""
    recv_buffer = ""
    send_buffer = ""
    log_handle = ""
    fcc_data = {}
    hc_cd_data = {}
    rac_cd_data = {}
    local_data = {}
    host_data = {}
    radio_data = {}

    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config')
        self.adif_CLASS = self.config['STATION']['class']        
        self.adif_MY_CNTY = self.config['STATION']['my_county']
        self.adif_MY_GRIDSQUARE = self.config['STATION']['my_gridsquare']
        self.adif_MY_NAME = self.config['STATION']['my_name']
        self.adif_OPERATOR = self.config['STATION']['operator']
        self.computer_name = socket.gethostname()
        self.consolelevel = int(self.config['DEBUG']['consolelevel'])
        self.logfilelevel = int(self.config['DEBUG']['logfilelevel'])
        self.logfile = str(self.config['DEBUG']['logfile'])
        self.smtpenabled = bool(strtobool(self.config['SMTP']['enabled']))
        self.smtphost = str(self.config['SMTP']['host'])
        self.smtpport = str(self.config['SMTP']['port'])
        self.smtpuser = str(self.config['SMTP']['user'])
        self.smtppass = str(self.config['SMTP']['pass'])
        self.mailfrom = str(self.config['SMTP']['mailfrom'])
        self.mailto = str(self.config['SMTP']['mailto'])
        self.gridfrominfo = bool(strtobool(self.config['GRIDS']['frominfo']))
        self.gridlength = int(self.config['GRIDS']['gridlength'])
        self.mapall = bool(strtobool(self.config['GRIDS']['map_all']))
        self.mapcq = bool(strtobool(self.config['GRIDS']['map_cq']))
        self.mapheartbeat = bool(strtobool(self.config['GRIDS']['map_heartbeat']))
        self.mapinfo = bool(strtobool(self.config['GRIDS']['map_info']))
        self.mapstatusmsg = bool(strtobool(self.config['GRIDS']['map_status']))
        self.maplog = bool(strtobool(self.config['GRIDS']['map_log']))
        self.mapqso = bool(strtobool(self.config['GRIDS']['map_qso']))
        self.mapsnr = bool(strtobool(self.config['GRIDS']['map_snr']))
        self.autoclose = bool(strtobool(self.config['GRIDS']['auto_close']))
        self.mapnoinfo = str(self.config['NOINFO']['map'])
        self.mapnoinfocolor = str(self.config['NOINFO']['color'])
        self.mapnoinfoaprs = str(self.config['NOINFO']['aprs'])
        self.mapnopir = str (self.config['NOPIR']['map'])
        self.mapnopircolor = str (self.config['NOPIR']['color'])
        self.mapnopiraprs = str (self.config['NOPIR']['aprs'])
        self.mapstatus = str (self.config['STATUS']['map'])
        self.mapstatuscolor = str (self.config['STATUS']['color'])
        self.mapstatusaprs = str (self.config['STATUS']['aprs'])
        self.grid_databases = str(self.config['DATABASES']['location'])
        self.fcc_lookup = bool(strtobool(self.config['DATABASES']['FccData']))
        self.hamcallcd_lookup = bool(strtobool(self.config['DATABASES']['HamCallCD']))
        self.raccd_lookup = bool(strtobool(self.config['DATABASES']['RacCD']))
        self.local_lookup = bool(strtobool(self.config['DATABASES']['LocalDB']))
        self.local_learn = bool(strtobool(self.config['DATABASES']['LocalDB_learn']))
        self.collect_rejects = bool(strtobool(self.config['DATABASES']['Collect_Rejects']))
        self.callook_lookup = bool(strtobool(self.config['DATABASES']['Callook']))
        self.hamcallol_lookup = bool(strtobool(self.config['DATABASES']['HamCallOnline']))
        self.hamcallol_username = str(self.config['DATABASES']['HCusername'])
        self.hamcallol_password = str(self.config['DATABASES']['HCpassword'])
        self.n1mmenabled = bool(strtobool(self.config['N1MM']['enabled']))
        self.n1mmhost = self.config['N1MM']['host']
        self.n1mmport = self.config['N1MM']['port']
        self.gtenabled = bool(strtobool(self.config['GRIDTRACKER']['enabled']))
        self.gthost = self.config['GRIDTRACKER']['host']
        self.gtport = self.config['GRIDTRACKER']['port']
        self.gsmsgenabled = bool(strtobool(self.config['GEOSERVER']['enabled_msg']))
        self.gsspotenabled = bool(strtobool(self.config['GEOSERVER']['enabled_spot']))
        self.gshost = self.config['GEOSERVER']['host']
        self.gsport = self.config['GEOSERVER']['port']
        self.gsauth = self.config['GEOSERVER']['token']
        self.yaacenabled = bool(strtobool(self.config['YAAC']['enabled']))
        self.yaaclogfile = str(self.config['YAAC']['logfile'])
        self.adifenabled = bool(strtobool(self.config['ADIF']['enabled']))
        self.adiflogfile = str(self.config['ADIF']['logfile'])        
        self.authenabled = bool(strtobool(self.config['AUTH']['enabled']))
        self.authtoken = str(self.config['AUTH']['token'])        
        self.reset_vals()
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        
        # Supress those nasty SSL certificate warnings
        warnings.filterwarnings("ignore")

        # If flie logging is enabled, open the log file
        if not self.logfilelevel == 0:
            try:
                self.log_handle = open(self.logfile,'a')
            except:
                print ("ERROR Unable to open log file")

        # Check parameters
        if not self.gridlength in range(1, 12):
            self.debug_log(self.log_warning,"__init__: Parameter 'gridlength' out of range. Using default of 6.")
            self.gridlength = 6

        # Load host database
        self.debug_log(self.log_entry,"__init__: ENTER Load Host Database")
        try:
            fh = ''
            fh = open(self.grid_databases + "JS8monitor_hosts.dat",'r')
            self.host_data = fh.read()
            fh.close()               
            self.debug_log(self.log_debug,"__init__: Loaded Host Database")
            self.debug_log(self.log_debug,"__init__: Size: " + str(len(self.host_data)))
        except:
            if fh:
                fh.close()
            self.debug_log(self.log_debug,"__init__: Unable to load Host Database")
        self.debug_log(self.log_entry,"__init__: EXIT Load Host Database")

        # If FCC Data is enabled, read in the database file
        # Warning this will consume lots of memory
        if self.fcc_lookup:
            self.debug_log(self.log_entry,"__init__: ENTER Load FCC Data")
            try:
                fh = ''
                fh = open(self.grid_databases + "JS8monitor_fccgrids.dat",'r')
                self.fcc_data = fh.read()
                fh.close()               
                self.debug_log(self.log_debug,"__init__: Loaded FCC Data")
                self.debug_log(self.log_debug,"__init__: Size: " + str(len(self.fcc_data)))
            except:
                if fh:
                    fh.close()
                # Database failed to load so disable FCC lookups           
                self.fcc_lookup = False              
                self.debug_log(self.log_debug,"__init__: Unable to load FCC Data")
            self.debug_log(self.log_entry,"__init__: EXIT Load FCC Data")

        # If HamCall CD is enabled, read in the database file
        # Warning this will consume about 2.6 Mb of memory
        if self.hamcallcd_lookup:
            self.debug_log(self.log_entry,"__init__: ENTER Load HamCall CD Data")
            try:
                fh = ''
                fh = open(self.grid_databases + "JS8monitor_hcgrids.dat",'r')
                self.hc_cd_data = fh.read()
                fh.close()               
                self.debug_log(self.log_debug,"__init__: Loaded HamCall CD Data")
                self.debug_log(self.log_debug,"__init__: Size: " + str(len(self.hc_cd_data)))
            except:
                if fh:
                    fh.close()
                # Database failed to load so disable HamCall CD lookups           
                self.hamcallcd_lookup = False              
                self.debug_log(self.log_debug,"__init__: Unable to load HamCall CD Data")
            self.debug_log(self.log_entry,"__init__: EXIT Load HamCall CD Data")

        # If RAC CD is enabled, read in the database file
        # Warning this can consume lots of memory
        if self.raccd_lookup:
            self.debug_log(self.log_entry,"__init__: ENTER Load RAC CD Data")
            try:
                fh = ''
                fh = open(self.grid_databases + "JS8monitor_racgrids.dat",'r')
                self.rac_cd_data = fh.read()
                fh.close()               
                self.debug_log(self.log_debug,"__init__: Loaded RAC CD Data")
                self.debug_log(self.log_debug,"__init__: Size: " + str(len(self.rac_cd_data)))
            except:
                if fh:
                    fh.close()
                # Database failed to load so disable RAC CD lookups           
                self.raccd_lookup = False              
                self.debug_log(self.log_debug,"__init__: Unable to load RAC CD Data")
            self.debug_log(self.log_entry,"__init__: EXIT Load RAC CD Data")

        # If local database is enabled, read in the database file
        # Warning this can consume lots of memory
        if self.local_lookup:
            self.debug_log(self.log_entry,"__init__: ENTER Load Local Database")
            try:
                fh = ''
                fh = open(self.grid_databases + "JS8monitor_localgrids.dat",'r')
                self.local_data = fh.read()
                fh.close()               
                self.debug_log(self.log_debug,"__init__: Loaded Local Database")
                self.debug_log(self.log_debug,"__init__: Size: " + str(len(self.local_data)))
            except:
                if fh:
                    fh.close()
                # Database failed to load but we leave lookups enabled so
                # learning can create a new database and add to it.
                self.debug_log(self.log_debug,"__init__: Unable to load Local Database")
            self.debug_log(self.log_entry,"__init__: EXIT Load Local Database")
        else:
            # force learning off if lookups are disabled.
            # otherwise you get a database full of duplicates.
            self.local_learn = False
   
    def reset_vals(self):
        """ Reset all values to initial state """
        self.adif_ARI_PROV = ""
        self.adif_ARRL_SECT = ""
        self.adif_BAND = ""
        self.adif_CALL = ""
        self.adif_CHECK = ""
        self.adif_COMMAND = ""
        self.adif_COMMENT = ""
        self.adif_CONTEST_ID = ""
        self.adif_CQZ = ""
        self.adif_DIG = ""
        self.adif_DISTRIKT = ""
        self.adif_DOK = ""
        self.adif_FREQ = "0"
        self.adif_FREQ_RX = ""
        self.adif_FREQ_TX = ""
        self.adif_GRIDSQUARE = ""
        self.adif_HOST = "---"
        self.adif_HOST_IP = ""
        self.adif_HOST_PORT = ""
        self.adif_IARU_ZONE = ""
        self.adif_IOTA = ""
        self.adif_ITUZ = ""
        self.adif_KDA = ""
        self.adif_LAT = ""
        self.adif_LON = ""
        self.adif_MODE = ""
        self.adif_NAME = ""
        self.adif_NAQSO_SECT = ""
        self.adif_OBLAST = ""
        self.adif_OFFSET = "0"
        self.adif_PFX = ""
        self.adif_POINTS = ""
        self.adif_PRECEDENCE = ""
        self.adif_QSO_COLOR = ""
        self.adif_QSO_DATE = ""
        self.adif_QSO_ICON = ""
        self.adif_QTH = ""
        self.adif_RADIO = ""
        self.adif_RADIO_NR = ""
        self.adif_RDA = ""
        self.adif_RST_RCVD = "0"
        self.adif_RST_SENT = "0"
        self.adif_RX_PWR = ""
        self.adif_SAC = ""
        self.adif_SECT = ""
        self.adif_SECTION = ""
        self.adif_SRX = ""
        self.adif_STATE = ""
        self.adif_STATION = ""
        self.adif_STATION_CALLSIGN = ""
        self.adif_STX = ""
        self.adif_SUBMODE = ""
        self.adif_TIME_OFF = ""
        self.adif_TIME_ON = ""
        self.adif_TX_PWR = ""
        self.adif_UKEI = ""
        self.adif_VE_PROV = ""
        self.adif_WWPMC = ""

    def parse_json(self):
        """ Parse json message """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # It's a parser after all
        self.debug_log(self.log_entry,"parse_json: --Enter--")
        try:
            self.debug_log(self.log_info,"parse_json: Getting message from queue")
            msgJSON = msgQueue.get()
            self.debug_log(self.log_debug,"parse_json: Removing non-ascii garbage")
            msgJSON = str(re.sub(r'[^\x00-\x7f]',r'',msgJSON))
            self.debug_log(self.log_hidebug,"parse_json: Raw JSON: %s" %msgJSON)
            self.debug_log(self.log_info,"parse_json: Parsing JSON message from JS8Call...")
            msgIndex = msgJSON.split("|",1)
            source = str(msgIndex[0])
            message_raw = str(msgIndex[1])
            message = json.loads(msgIndex[1])
            msgQueue.task_done()
        except:
            message_raw = {}
            message = {}
        if not message:
            self.debug_log(self.log_error,"parse_json: No JSON message to parse")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        self.debug_log(self.log_info,"parse_json: Got JSON message from %s" %source)
        try:
            self.get_host(source)
            typ = message.get('type', '')
            value = message.get('value', '')
            params = message.get('params', {})
        except:
            self.debug_log(self.log_error,"parse_json: Unable to parse JSON message.")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if self.adif_HOST:
            self.debug_log(self.log_hidebug,"parse_json: -> host: " + self.adif_HOST)
        if typ:
            self.debug_log(self.log_hidebug,"parse_json: -> type: " + typ)
        if value:
            self.debug_log(self.log_hidebug,"parse_json: -> value: " + value)
        if params:
            self.debug_log(self.log_hidebug,"parse_json: -> params: ")
            self.debug_log(self.log_hidebug,params)
 
        if not typ:
            self.debug_log(self.log_info,"parse_json: Missing message TYPE")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'INBOX.MESSAGE':
            self.debug_log(self.log_info,"parse_json: ---INBOX.MESSAGE---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'INBOX.MESSAGES':
            self.debug_log(self.log_info,"parse_json: ---INBOX.MESSAGES---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'MODE.SPEED':
            self.debug_log(self.log_info,"parse_json: ---MODE.SPEED---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        
        if typ == 'RIG.FREQ':
            self.debug_log(self.log_info,"parse_json: ---RIG.FREQ---")

            # Fetch the details
            if 'DIAL' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_FREQ = str(params['DIAL'])
                    self.adif_FREQ = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_FREQ))
                    self.adif_FREQ = self.adif_FREQ.strip()
                except:
                    self.adif_FREQ = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[DIAL].")
            if 'FREQ' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_FREQ_TX = str(params['FREQ'])
                    self.adif_FREQ_TX = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_FREQ_TX))
                    self.adif_FREQ_TX = self.adif_FREQ_TX.strip()
                except:
                    self.adif_FREQ_TX = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[FREQ].")
            if 'OFFSET' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_OFFSET = str(params['OFFSET'])
                    self.adif_OFFSET = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_OFFSET))
                    self.adif_OFFSET = self.adif_OFFSET.strip()
                except:
                    self.aadif_OFFSET = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[OFFSET].")

            # fill in missing info
            self.get_band()
            # Print adif variables for debugging
            self.print_adif()
            # Log SMDR record
            msgChange = "Frequency Change >> BAND: " + self.adif_BAND + " FREQ: " + self.adif_FREQ + " OFFSET: " + self.adif_OFFSET
            self.debug_log(self.log_smdr,msgChange)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        
        if typ == 'RIG.PTT':
            self.debug_log(self.log_info,"parse_json: ---RIG.PTT---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.BAND_ACTIVITY':
            self.debug_log(self.log_info,"parse_json: ---RX.BAND_ACTIVITY---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.CALL_ACTIVITY':
            self.debug_log(self.log_info,"parse_json: ---RX.CALL_ACTIVITY---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.CALL_SELECTED':
            self.debug_log(self.log_info,"parse_json: ---RX.CALL_SELECTED---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.SPOT':
            self.debug_log(self.log_info,"parse_json: ---RX.SPOT---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.TEXT':
            self.debug_log(self.log_info,"parse_json: ---RX.TEXT---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.CALLSIGN':
            self.debug_log(self.log_info,"parse_json: ---STATION.CALLSIGN---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.GRID':
            self.debug_log(self.log_info,"parse_json: ---STATION.GRID---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.INFO':
            self.debug_log(self.log_info,"parse_json: ---STATION.INFO---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.STATUS':
            self.debug_log(self.log_info,"parse_json: ---STATION.STATUS---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'TX.FRAME':
            self.debug_log(self.log_info,"parse_json: ---TX.FRAME---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'TX.TEXT':
            self.debug_log(self.log_info,"parse_json: ---TX.TEXT---")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'CLOSE':
            self.debug_log(self.log_info,"parse_json: ---CLOSE---")
            # Log SMDR record
            self.debug_log(self.log_smdr,"JS8Call has terminated.")
            if self.autoclose:
                self.debug_log(self.log_critical,"---Shutting Down---\n")
                sys.exit(0)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'LOG.QSO':
            self.debug_log(self.log_info,"parse_json: ---LOG.QSO---")
            self.debug_log(self.log_hidebug,"parse_json: value: " + value + "<eor>")

            # set the default NOINFO tag
            attr = self.mapnoinfo
            tag, default = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, default)
            self.adif_QSO_COLOR = str(self.mapnoinfocolor)
            self.adif_QSO_ICON = str(self.mapnoinfoaprs)
            self.debug_log(self.log_info,"parse_json: Setting default tag for NOINFO")
            self.debug_log(self.log_debug,"parse_json: NOINFO %s: %s (%s) (%s)" % (tag, default, self.adif_QSO_COLOR, self.adif_QSO_ICON))

            self.debug_log(self.log_debug,"parse_json: Parsing log entry")
            # Note: Tags 'MY_GRIDSQUARE', 'OPERATOR' from JS8Call are
            # ignored if found, as they conflict with the config file
            # settings for these tags.
            for tag in ['BAND', 'CALL', 'COMMENT', 'FREQ', 'GRIDSQUARE',
                          'MODE', 'NAME', 'QSO_DATE', 'QSO_DATE_OFF',
                          'RST_RCVD', 'RST_SENT', 'STATION_CALLSIGN',
                          'SUBMODE', 'TIME_OFF', 'TIME_ON']:      
                try:
                    self.debug_log(self.log_debug,"parse_json: Searching for: " + tag)
                    message = value
                    search_token = "<" + tag + ":"
                    start = message.lower().find(search_token.lower())
                    if start == -1:
                        self.debug_log(self.log_debug,"parse_json: Did not find: " + tag)
                        continue
                    self.debug_log(self.log_debug,"parse_json: Start: " + str(start))
                    lstart = message.find(':',start)
                    if lstart == -1:
                        self.debug_log(self.log_debug,"parse_json: Did not find delimiter")
                        continue
                    self.debug_log(self.log_debug,"parse_json: Found delimiter: " + str(lstart))
                    lend = message.find('>',lstart)
                    if lend == -1:
                        self.debug_log(self.log_debug,"parse_json: Did not find closure")
                        continue
                    self.debug_log(self.log_debug,"parse_json: Found closure: " + str(lend))
                    self.debug_log(self.log_debug,"parse_json: Found length: " + message[lstart + 1:lend])
                    attr_len = int(message[lstart + 1:lend])
                    self.debug_log(self.log_debug,"parse_json: Converted length to number")
                    attr = str(message[lend + 1:lend + 1 + attr_len])
                    self.debug_log(self.log_debug,"parse_json: Found ATTR: " + attr)
                    if not attr:
                        self.debug_log(self.log_debug,"parse_json: Empty ATTR")
                        continue

                    # Look for second occurance of MODE tag
                    if tag == "MODE":
                        self.debug_log(self.log_debug,"parse_json: Found MODE. Looking for over-ride..")
                        search_token = "<" + tag + ":"
                        mstart = message.lower().find(search_token.lower(),start + 1)
                        if mstart == -1:
                            self.debug_log(self.log_debug,"parse_json: Did not find(o): " + tag) 
                            continue
                        self.debug_log(self.log_debug,"parse_json: Start(o): " + str(mstart))
                        ostart = message.find(':',mstart)
                        if ostart == -1:
                            self.debug_log(self.log_debug,"parse_json: Did not find delimiter(0)")
                            continue
                        self.debug_log(self.log_debug,"parse_json: Found delimiter(o): " + str(ostart))
                        oend = message.find('>',ostart)
                        if oend == -1:
                            self.debug_log(self.log_debug,"parse_json: Did not find closure(o)")
                            continue
                        self.debug_log(self.log_debug,"parse_json: Found closure(o): " + str(oend))
                        self.debug_log(self.log_debug,"parse_json: Found length(o): " + message[ostart + 1:oend])
                        oattr_len = int(message[ostart + 1:oend])
                        self.debug_log(self.log_debug,"parse_json: Converted length to number(o)")
                        oattr = str(message[oend + 1:oend + 1 + oattr_len])
                        self.debug_log(self.log_debug,"parse_json: Found ATTR(o): " + oattr)
                        if not oattr:
                            self.debug_log(self.log_debug,"parse_json: Empty ATTR(o)")
                        else:
                            self.debug_log(self.log_debug,"parse_json: Overriding ATTR with ATTR(0)")
                            attr = oattr

                    # Handle attribute formatting
                    # Normalize frequency to Hz
                    if tag == "FREQ":
                        self.debug_log(self.log_debug,"parse_json: Found FREQ")
                        attr = str(re.sub(r'\.',r'',attr))
                        self.debug_log(self.log_debug,"parse_json: ATTR: " + attr)
                    
                    # now set the tag
                    tag = "adif_" + tag
                    setattr(self, tag, attr)
                    self.debug_log(self.log_debug,"parse_json: TAG %s: %s" % (tag, attr))
                except:
                    self.debug_log(self.log_warning,"parse_json: SNAP! Something went wrong. Skipping: " + tag)
                    continue

            # Tags have now been parsed
            self.debug_log(self.log_debug,"parse_json: Done parsing tags")

            # handle any other data capture here
            if 'CMD' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_COMMAND = params['CMD']
                    self.adif_COMMAND = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_COMMAND))
                    self.adif_COMMAND = self.adif_COMMAND.strip()
                except:
                    self.adif_COMMAND = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[CMD].")

            # fill in missing info
            self.get_grid()
            # prefix callsign to comment
            self.adif_COMMENT = self.adif_CALL + ": " + self.adif_COMMENT
            # Print adif variables for debugging
            self.print_adif()
            # Log SMDR record
            self.debug_log(self.log_smdr,self.adif_COMMENT)
            # Send QSO
            if self.maplog:
                self.refresh_gts()
                self.send_status_gridtracker()
                self.log_new_qso()
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'PING':
            self.debug_log(self.log_info,"parse_json: ---PING---")
            """
            Capture the ip/port details for each radio seen, based
            on the PING event from the associated instance of
            JS8Call. All other clients should be ignored. This data
            is used to direct commands to the proper instance of
            JS8Call. The data comes from the get_host() subroutine
            called at the top of parse_json().
            """
            # Update in-memory radio database
            try:
                self.radio_data.update({self.adif_HOST_IP: self.adif_HOST_PORT})
                self.debug_log(self.log_info,"parse_json: Updated RADIO database: " + str(self.adif_HOST_IP))
            except:
                # Database failed to update
                self.debug_log(self.log_warning,"parse_json: Failed to update RADIO database")

            # If enabled, send heartbeat to GridTracker
            if self.gtenabled:
                # build heartbeat packet for GridTracker
                pkt = pywsjtx.HeartBeatPacket.Builder(self.MY_WSJTX_ID, self.MY_WSJTX_MAX_SCHEMA, self.MY_WSJTX_VERSION, self.MY_WSJTX_REVISION)
                               
                # now send the packet to GridTracker
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.connect((self.gthost,int(self.gtport)))          
                    self.debug_log(self.log_debug,"parse_json: Sending GRIDTRACKER heartbeat...")
                    sock.send(pkt)
                    self.debug_log(self.log_info,"parse_json: Sent GRIDTRACKER heartbeat.")
                except KeyboardInterrupt:
                    sys.stderr.write("User cancelled.")
                    sock.close()
                    sys.exit(0)
                except socket.error as msg:
                    self.debug_log(self.log_error,"parse_json: %s Unable to establish connection to GRIDTRACKER" % msg)            
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return                        

        if typ == 'RX.ACTIVITY':
            self.debug_log(self.log_info,"parse_json: ---RX.ACTIVITY---")
            self.debug_log(self.log_hidebug,"parse_json: value: " + value + "<eor>")
            # Send GridTracker status message if required
            self.send_status_gridtracker()
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        if typ == 'RX.DIRECTED':
            self.debug_log(self.log_info,"parse_json: ---RX.DIRECTED---")
            # Populate all of the adif messages based on the data received.
            self.adif_ARI_PROV = ""
            self.adif_ARRL_SECT = ""
            self.adif_BAND = ""
            if 'FROM' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_CALL = str(params['FROM'])
                    self.adif_CALL = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_CALL))
                    self.adif_CALL = self.adif_CALL.strip()
                except:
                    self.adif_CALL = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[FROM].")
            self.adif_CHECK = ""
            if 'CMD' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_COMMAND = params['CMD']
                    self.adif_COMMAND = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_COMMAND))
                    self.adif_COMMAND = self.adif_COMMAND.strip()
                except:
                    self.adif_COMMAND = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[CMD].")            
            if 'TEXT' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_COMMENT = params['TEXT']
                    self.adif_COMMENT = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_COMMENT))
                except:
                    self.adif_COMMENT = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[TEXT].")
            # adif variable assignment
            self.adif_CONTEST_ID = ""
            self.adif_CQZ = ""
            self.adif_DIG = ""
            self.adif_DISTRIKT = ""
            self.adif_DOK = ""
            if 'DIAL' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_FREQ = str(params['DIAL'])
                    self.adif_FREQ = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_FREQ))
                    self.adif_FREQ = self.adif_FREQ.strip()
                except:
                    self.adif_FREQ = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[DIAL].")
            self.adif_FREQ_RX = ""
            if 'GRID' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_GRIDSQUARE = str(params['GRID'])
                    self.adif_GRIDSQUARE = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_GRIDSQUARE))
                    self.adif_GRIDSQUARE = self.adif_GRIDSQUARE.strip()
                except:
                    self.adif_GRIDSQUARE = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[GRID].")
            self.adif_IARU_ZONE = ""
            self.adif_IOTA = ""
            self.adif_ITUZ = ""
            self.adif_KDA = ""
            self.adif_LAT = ""
            self.adif_LON = ""
            self.adif_MODE = "MFSK"
            self.adif_NAME = ""
            self.adif_NAQSO_SECT = ""
            self.adif_OBLAST = ""
            if 'OFFSET' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_OFFSET = str(params['OFFSET'])
                    self.adif_OFFSET = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_OFFSET))
                    self.adif_OFFSET = self.adif_OFFSET.strip()
                except:
                    self.adif_OFFSET = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[SNR].")   
            self.adif_PFX = ""
            self.adif_POINTS = ""
            self.adif_PRECEDENCE = ""
            self.adif_QTH = ""
            if 'RADIO' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_RADIO = str(params['RADIO'])
                    self.adif_RADIO = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_RADIO))
                    self.adif_RADIO = self.adif_RADIO.strip()
                except:
                    self.adif_RADIO = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[RADIO].")   
            self.adif_RADIO_NR = ""
            self.adif_RDA = ""
            if 'SNR' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_RST_RCVD = str(params['SNR'])
                    self.adif_RST_RCVD = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_RST_RCVD))
                    self.adif_RST_RCVD = self.adif_RST_RCVD.strip()
                except:
                    self.adif_RST_RCVD = "0"
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[SNR].")   
            self.adif_RST_SENT = "0"
            self.adif_RX_PWR = ""
            self.adif_SAC = ""
            self.adif_SECT = ""
            self.adif_SECTION = ""
            self.adif_SRX = ""
            self.adif_STATE = ""
            if 'TO' in params:
                try:
                    # remove non-ascii garbage
                    self.adif_STATION = str(params['TO'])
                    self.adif_STATION = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_STATION))
                    self.adif_STATION = self.adif_STATION.strip()
                except:
                    self.adif_STATION = ""
                    self.debug_log(self.log_debug,"parse_json: Unable to save JSON[TO].")
            self.adif_STX = ""
            self.adif_SUBMODE = "JS8"
            self.adif_TX_PWR = ""
            self.adif_UKEI = ""
            self.adif_VE_PROV = ""
            self.adif_WWPMC = ""

            # set the default NOINFO tag
            attr = self.mapnoinfo
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.mapnoinfocolor)
            self.adif_QSO_ICON = str(self.mapnoinfoaprs)
            self.debug_log(self.log_info,"parse_json: Setting default tag for NOINFO")
            self.debug_log(self.log_debug,"parse_json: NOINFO %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))
            
            # get UTC time from system clock since UTC fields aren't reliable
            mytime = datetime.datetime.utcnow()
            self.adif_TIME_OFF = mytime.strftime("%H%M%S")
            self.adif_TIME_ON = mytime.strftime("%H%M%S")
            self.adif_QSO_DATE = mytime.strftime("%Y%m%d")

            # ---- BEGIN PROCESSING ----
            # Process querry(?) messages
            # We have to intercept and handle the querries(?) first so that
            # the message detection below only fires on actual messages.
            self.debug_log(self.log_entry,"parse_json: ENTER Map (?)")
            message = self.adif_COMMAND
            search_token = "?"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: (?) NOT found")                
            else:
                self.debug_log(self.log_debug,"parse_json: (?) FOUND")
                # we have a message with a (?) in the command.
                # now go process it, but don't map it.
                # fill in missing info
                self.get_band()
                self.get_grid()
                # Print adif variables for debugging
                self.print_adif()
                # Log SMDR record
                self.debug_log(self.log_smdr,self.adif_COMMENT)
                self.debug_log(self.log_entry,"parse_json: EXIT Map (?)")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: Exit Map (?)")

            # Process CQ messages
            self.debug_log(self.log_entry,"parse_json: Enter Map CQ")
            message = self.adif_COMMAND
            search_token = "CQ"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: CQ NOT found")
            else:
                self.debug_log(self.log_debug,"parse_json: CQ FOUND")
                # fill in missing info
                self.get_band()
                self.get_grid()
                # Print ADIF variables for debugging
                self.print_adif()
                # Log SMDR record
                self.debug_log(self.log_smdr,self.adif_COMMENT)

                # Send QSO
                if self.mapcq:
                    self.refresh_gts()
                    self.send_status_gridtracker()
                    self.send_decode_gridtracker()
                    self.log_new_qso()
                self.debug_log(self.log_entry,"parse_json: EXIT Map CQ")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: Exit Map CQ")

            # Process HEARTBEAT messages
            self.debug_log(self.log_entry,"parse_json: ENTER Map HEARTBEAT")
            message = self.adif_COMMAND
            search_token = "HEARTBEAT"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: HEARTBEAT NOT found")
            else:
                self.debug_log(self.log_debug,"parse_json: HEARTBEAT FOUND")
                # fill in missing info
                self.get_band()
                self.get_grid()
                # Print ADIF variables for debugging
                self.print_adif()
                # Log SMDR record
                self.debug_log(self.log_smdr,self.adif_COMMENT)
                # Send QSO
                if self.mapheartbeat:
                    self.refresh_gts()
                    self.send_status_gridtracker()
                    self.send_decode_gridtracker()
                    self.log_new_qso()
                self.debug_log(self.log_entry,"parse_json: EXIT Map HEARTBEAT")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: EXIT Map HEARTBEAT")

            # Process SNR messages
            self.debug_log(self.log_entry,"parse_json: ENTER Map SNR")
            message = self.adif_COMMAND
            search_token = "SNR"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: SNR NOT found")
            else:
                self.debug_log(self.log_debug,"parse_json: SNR FOUND")
                message = self.adif_COMMENT
                while True:
                    # check if SNR was intended for our station
                    if not self.mapall:
                        search_token = self.adif_OPERATOR
                        mycall = message.lower().find(search_token.lower())
                        if mycall == -1:
                            self.debug_log(self.log_debug,"parse_json: SNR NOT for our station")
                            self.debug_log(self.log_smdr,self.adif_COMMENT)
                            break
                    # check if the SNR report has MSG data.
                    search_token = "MSG"
                    msg = message.lower().find(search_token.lower())
                    if msg == -1:
                        self.debug_log(self.log_debug,"parse_json: MSG NOT found")
                        search_token = "SNR "
                        end = len(message)
                        start = message.lower().find(search_token.lower(),end-9,end)
                    else:
                        self.debug_log(self.log_debug,"parse_json: MSG FOUND")
                        search_token = "SNR "
                        end = msg
                        start = message.lower().find(search_token.lower(),end-9,end)
                    # safety check
                    if start == -1:
                        self.debug_log(self.log_debug,"parse_json: SNR NOT found in COMMENT")
                        self.debug_log(self.log_smdr,self.adif_COMMENT)
                        break
                    # get the SNR report from the message (what they heard)
                    snr = message[start+3:end]
                    self.debug_log(self.log_debug,"parse_json: SNR_1: " + str(snr))
                    snr = snr.strip()
                    self.debug_log(self.log_debug,"parse_json: SNR_2: " + str(snr))
                    # safety in case we grab someting unexpected
                    snr = snr[:4]
                    self.debug_log(self.log_debug,"parse_json: SNR_3: " + str(snr))
                    # test if we have a number
                    try:
                        test = int(snr)
                    except:
                        snr = "0"
                        self.debug_log(self.log_debug,"parse_json: SNR_4: " + str(snr))
                    self.adif_RST_SENT = str(snr)
                    self.debug_log(self.log_debug,"parse_json: SNR: " + self.adif_RST_SENT)
                    # fill in missing info
                    self.get_band()
                    self.get_grid()                        
                    # Print ADIF variables for debugging
                    self.print_adif()
                    # Log SMDR record
                    self.debug_log(self.log_smdr,self.adif_COMMENT)
                    # Send QSO
                    if self.mapsnr:
                        self.refresh_gts()
                        self.send_status_gridtracker()
                        self.send_decode_gridtracker()
                        self.log_new_qso()
                    break
                self.debug_log(self.log_entry,"parse_json: EXIT Map SNR")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: Exit Map SNR")

            # Process INFO messages
            self.debug_log(self.log_entry,"parse_json: ENTER Map INFO")
            message = self.adif_COMMAND
            search_token = "INFO"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: INFO NOT found")                
            else:
                self.debug_log(self.log_debug,"parse_json: INFO FOUND")
                # we have a message with the INFO tag.
                # now go process it.
                # fill in missing info
                self.get_band()
                # process INFO message
                self.parse_info()
                # Check for missing gridsquares
                self.get_grid()
                # Print adif variables for debugging
                self.print_adif()
                # Log SMDR record
                self.debug_log(self.log_smdr,self.adif_COMMENT)
                # Send QSO
                if self.mapinfo:
                    self.refresh_gts()
                    self.send_status_gridtracker()
                    self.log_new_qso()

                    # Post INFO message to GeoChron
                    self.send_message_geoserver()

                # Send an alert we have an INFO message
                self.send_alert("New Info Message", self.adif_COMMENT)

                self.debug_log(self.log_entry,"parse_json: EXIT Map INFO")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: Exit Map INFO")

            # Process STATUS messages
            self.debug_log(self.log_entry,"parse_json: ENTER Map STATUS")
            message = self.adif_COMMAND
            search_token = "STATUS"
            start = message.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"parse_json: STATUS NOT found")                
            else:
                self.debug_log(self.log_debug,"parse_json: STATUS FOUND")
                # we have a message with the STATUS tag.
                # now go process it.
                attr = self.mapstatus
                tag, value = attr.strip().split(':')
                tag = "adif_" + tag
                setattr(self, tag, value)
                self.adif_QSO_COLOR = str(self.mapstatuscolor)
                self.adif_QSO_ICON = str(self.mapstatusaprs)
                self.debug_log(self.log_info,"parse_json: STATUS message")
                self.debug_log(self.log_debug,"parse_json: STATUS %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))
                # fill in missing info
                self.get_band()
                self.get_grid()
                # Print adif variables for debugging
                self.print_adif()
                # Log SMDR record
                self.debug_log(self.log_smdr,self.adif_COMMENT)
                # Send QSO
                if self.mapstatusmsg:
                    self.refresh_gts()
                    self.send_status_gridtracker()
                    self.log_new_qso()

                    # Post STATUS message to GeoChron
                    self.send_message_geoserver()

                # Send an alert we have an STATUS message
                self.send_alert("New Status Message", self.adif_COMMENT)

                self.debug_log(self.log_entry,"parse_json: EXIT Map STATUS")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return
            self.debug_log(self.log_entry,"parse_json: Exit Map STATUS")
            """
            If we have reached this point, we have a standard message.
            Process it using a default handler. If we identify additional
            message types that need special handeling, then code them here.

            Some saved debugger stuff for later
            Unused fields passed in API
            Note UTC from the API is not reliable/stable
            params['UTC']
            params['extra']
            params['freq']
            params['speed']
            params['tdrift']
            params['to']
            """
            # Process QSO messages (default handler)
            self.debug_log(self.log_entry,"parse_json: ENTER Map QSO")
            # fill in missing info
            self.get_band()
            self.get_grid()
            # Print adif variables for debugging
            self.print_adif()
            # Log SMDR record
            self.debug_log(self.log_smdr,self.adif_COMMENT)
            # Send QSO
            if self.mapqso:
                self.refresh_gts()
                self.send_status_gridtracker()
                self.log_new_qso()
            self.debug_log(self.log_entry,"parse_json: EXIT Map QSO")
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        """
        Begin processing of command TYPES below. These types are used
        to send commands to JS8Call. The originator is assumed to be
        a client application.

        Start by parsing any passed parameters and checking authorization.
        """
        auth = ""
        if 'AUTH' in params:
            try:
                # remove non-ascii garbage
                auth = str(params['AUTH'])
                auth = str(re.sub(r'[^\x00-\x7f]',r'',auth))
                auth = auth.strip()
            except:
                auth = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[AUTH].")
        if 'RADIO' in params:
            try:
                # remove non-ascii garbage
                self.adif_RADIO = str(params['RADIO'])
                self.adif_RADIO = str(re.sub(r'[^\x00-\x7f]',r'',self.adif_RADIO))
                self.adif_RADIO = self.adif_RADIO.strip()
            except:
                self.adif_RADIO = ""
                self.debug_log(self.log_debug,"parse_json: Unable to save JSON[RADIO].")      

        # Check for valid security token.
        if self.authenabled:
            if not auth == self.authtoken:
                self.debug_log(self.log_smdr,"Authorization Failure.")
                self.debug_log(self.log_info,"parse_json: Authorization failed.")
                self.debug_log(self.log_entry,"parse_json: --Exit--\n")
                return

        if typ == 'INBOX.GET_MESSAGES':
            self.debug_log(self.log_info,"parse_json: ---INBOX.GET_MESSAGES---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'INBOX.STORE_MESSAGE':
            self.debug_log(self.log_info,"parse_json: ---INBOX.STORE_MESSAGE---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'MODE.GET_SPEED':
            self.debug_log(self.log_info,"parse_json: ---MODE.GET_SPEED---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'MODE.SET_SPEED':
            self.debug_log(self.log_info,"parse_json: ---MODE.SET_SPEED---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RIG.GET_FREQ':
            self.debug_log(self.log_info,"parse_json: ---RIG.GET_FREQ---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RIG.SET_FREQ':
            self.debug_log(self.log_info,"parse_json: ---RIG.SET_FREQ---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.GET_BAND_ACTIVITY':
            self.debug_log(self.log_info,"parse_json: ---RX.GET_BAND_ACTIVITY---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.GET_CALL_ACTIVITY':
            self.debug_log(self.log_info,"parse_json: ---RX.GET_CALL_ACTIVITY---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.GET_CALL_SELECTED':
            self.debug_log(self.log_info,"parse_json: ---RX.GET_CALL_SELECTED---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'RX.GET_TEXT':
            self.debug_log(self.log_info,"parse_json: ---RX.GET_TEXT---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.GET_CALLSIGN':
            self.debug_log(self.log_info,"parse_json: ---STATION.GET_CALLSIGN---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.GET_GRID':
            self.debug_log(self.log_info,"parse_json: ---STATION.GET_GRID---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.SET_GRID':
            self.debug_log(self.log_info,"parse_json: ---STATION.SET_GRID---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.GET_INFO':
            self.debug_log(self.log_info,"parse_json: ---STATION.GET_INFO---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.SET_INFO':
            self.debug_log(self.log_info,"parse_json: ---STATION.SET_INFO---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.GET_STATUS':
            self.debug_log(self.log_info,"parse_json: ---STATION.GET_STATUS---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'STATION.SET_STATUS':
            self.debug_log(self.log_info,"parse_json: ---STATION.SET_STATUS---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'TX.SET_TEXT':
            self.debug_log(self.log_info,"parse_json: ---TX.SET_TEXT---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return
        if typ == 'TX.SEND_MESSAGE':
            self.debug_log(self.log_info,"parse_json: ---TX.SEND_MESSAGE---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        # Test harness for testing command communications from clients.
        if typ == 'TEST.TEST':
            self.debug_log(self.log_info,"parse_json: ---TEST.TEST---")
            self.queue_cmd(message_raw)
            self.debug_log(self.log_entry,"parse_json: --Exit--\n")
            return

        """
        If we have reached this point, we have an unknown TYPE.
        Process them using a default handler. If we identify additional
        TYPES that need special handeling, then code them here.
        """
        self.debug_log(self.log_info,"parse_json: ---UNKNOWN.TYPE---")
        self.debug_log(self.log_entry,"parse_json: --Exit--\n")
        return

    def parse_info(self):
        """ Parse INFO message """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # It's a parser after all
        self.debug_log(self.log_entry,"parse_info: --Enter--")
        self.debug_log(self.log_info,"parse_info: Parsing INFO message from JS8Call...")
        message = self.adif_COMMENT
        if not message:                
            # set noinfo pir
            # This indicates the message text field was blank
            attr = self.mapnoinfo
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.mapnoinfocolor)
            self.adif_QSO_ICON = str(self.mapnoinfoaprs)
            self.debug_log(self.log_info,"parse_info: No INFO message")
            self.debug_log(self.log_debug,"parse_info: NOINFO %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))
            self.debug_log(self.log_entry,"parse_info: --Exit--")
            return

        self.debug_log(self.log_debug,"parse_info: Got INFO message")
        # set default pir
        # This indicates the message text field had text, but no pir
        attr = self.mapnopir
        tag, value = attr.strip().split(':')
        tag = "adif_" + tag
        setattr(self, tag, value)
        self.adif_QSO_COLOR = str(self.mapnopircolor)
        self.adif_QSO_ICON = str(self.mapnopiraprs)
        self.debug_log(self.log_info,"parse_info: Set default PIR message")
        self.debug_log(self.log_debug,"parse_info: NOPIR %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))
 
        # check for unknown pir
        search_token = self.config['UNKNOWN']['search']
        start = message.lower().find(search_token.lower())
        if start == -1:
            self.debug_log(self.log_info,"parse_info: UNKNOWN pir NOT found")
        else:
            self.debug_log(self.log_info,"parse_info: UNKNOWN pir FOUND")
            attr = str(self.config['UNKNOWN']['map'])
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.config['UNKNOWN']['color'])
            self.adif_QSO_ICON = str(self.config['UNKNOWN']['aprs'])
            self.debug_log(self.log_debug,"parse_info: UNKNOWN %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))

        # check for green pir
        search_token = self.config['GREEN']['search']
        start = message.lower().find(search_token.lower())
        if start == -1:
            self.debug_log(self.log_info,"parse_info: GREEN pir NOT found")
        else:
            self.debug_log(self.log_info,"parse_info: GREEN pir FOUND")
            attr = str(self.config['GREEN']['map'])
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.config['GREEN']['color'])
            self.adif_QSO_ICON = str(self.config['GREEN']['aprs'])            
            self.debug_log(self.log_debug,"parse_info: GREEN %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))

        # check for yellow pir
        search_token = self.config['YELLOW']['search']
        start = message.lower().find(search_token.lower())
        if start == -1:
            self.debug_log(self.log_info,"parse_info: YELLOW pir NOT found")
        else:
            self.debug_log(self.log_info,"parse_info: YELLOW pir FOUND")
            attr = str(self.config['YELLOW']['map'])
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.config['YELLOW']['color'])
            self.adif_QSO_ICON = str(self.config['YELLOW']['aprs'])
            self.debug_log(self.log_debug,"parse_info: YELLOW %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))

        # check for red pir
        search_token = self.config['RED']['search']
        start = message.lower().find(search_token.lower())
        if start == -1:
            self.debug_log(self.log_info,"parse_info: RED pir NOT found")
        else:
            self.debug_log(self.log_info,"parse_info: RED pir FOUND")
            attr = str(self.config['RED']['map'])
            tag, value = attr.strip().split(':')
            tag = "adif_" + tag
            setattr(self, tag, value)
            self.adif_QSO_COLOR = str(self.config['RED']['color'])
            self.adif_QSO_ICON = str(self.config['RED']['aprs'])
            self.debug_log(self.log_debug,"parse_info: RED %s: %s (%s) (%s)" % (tag, value, self.adif_QSO_COLOR, self.adif_QSO_ICON))

        # check INFO for gridsquares if enabled
        # this routine is looking for a very specific format of the INFO message
        # example "GRID;PIR1=G;PIR2=Y"
        if self.gridfrominfo:
            self.debug_log(self.log_debug,"parse_info: MESSAGE: " + str(message))
            end = message.find(';')
            self.debug_log(self.log_debug,"parse_info: END: " + str(end))
            if end == -1:
                self.debug_log(self.log_debug,"parse_info: GRID NOT found")
                self.debug_log(self.log_entry,"parse_info: --Exit--")
                return
            start = message.find('INFO ',end -12,end)
            self.debug_log(self.log_debug,"START: " + str(start))
            if start == -1:
                self.debug_log(self.log_debug,"parse_info: GRID NOT found")
                self.debug_log(self.log_entry,"parse_info: --Exit--")
                return
            grid = message[start + 5:end]
            self.debug_log(self.log_debug,"parse_info: GRID_1: " + str(grid))
            grid = grid.strip()
            self.debug_log(self.log_debug,"parse_info: GRID_2: " + str(grid))
            # safety in case we grab someting unexpected
            grid = grid[:self.gridlength]         
            self.debug_log(self.log_debug,"parse_info: GRID_3: " + str(grid))
            self.adif_GRIDSQUARE = str(grid)
            self.debug_log(self.log_debug,"parse_info: INFO GRID: " + self.adif_GRIDSQUARE)

            # If the call sign has not been captured, grab it from the info line.
            if not self.adif_CALL:
                callend = message.find(':',end -22,start)
                self.debug_log(self.log_debug,"parse_info: CALL END: " + str(callend))
                if callend == -1:
                    self.debug_log(self.log_debug,"parse_info: CALL NOT found")
                    return
                callstart = message.find(' ',callend -9,callend)
                self.debug_log(self.log_debug,"parse_info: CALL START: " + str(callstart))
                if callstart == -1:
                    callstart = 0
                self.adif_CALL = str(message[callstart:callend])
                self.debug_log(self.log_debug,"parse_info: CALL_1: " + str(self.adif_CALL))
                self.adif_CALL = self.adif_CALL.strip()
                self.debug_log(self.log_debug,"parse_info: CALL Found: " + str(self.adif_CALL))
        self.debug_log(self.log_entry,"parse_info: --Exit--")

    def get_band(self):
        """ Calculate the band from the frequency (Hz) """
        self.debug_log(self.log_entry,"get_band: --Enter--")
        if not self.adif_FREQ:
            self.debug_log(self.log_debug,"get_band: No frequency to lookup")
            self.debug_log(self.log_entry,"get_band: --Exit--")
            return
        if self.adif_BAND:
            self.debug_log(self.log_debug,"get_band: BAND already defined: " + str(self.adif_BAND))
            self.debug_log(self.log_entry,"get_band: --Exit--")
            return
        while True:
            self.debug_log(self.log_debug,"get_band: Looking up frequency: %s" % (self.adif_FREQ))
            test = int(self.adif_FREQ)
            if test in range(1800000, 2000000):
                self.adif_BAND = "160m"
                break
            if test in range(3500000, 4000000):
                self.adif_BAND = "80m"
                break
            if test in range(5330000, 5404000):
                self.adif_BAND = "60m"
                break
            if test in range(7000000, 7300000):
                self.adif_BAND = "40m"
                break
            if test in range(10100000, 10150000):
                self.adif_BAND = "30m"
                break
            if test in range(14000000, 14350000):
                self.adif_BAND = "20m"
                break
            if test in range(18068000, 18168000):
                self.adif_BAND = "17m"
                break
            if test in range(21000000, 21450000):
                self.adif_BAND = "15m"
                break
            if test in range(24890000, 24990000):
                self.adif_BAND = "12m"
                break
            if test in range(28000000, 29700000):
                self.adif_BAND = "10m"
                break
            if test in range(50000000, 54000000):
                self.adif_BAND = "6m"
                break
            if test in range(144000000, 148000000):
                self.adif_BAND = "2m"
                break
            if test in range(222000000, 225000000):
                self.adif_BAND = "1.25m"
                break
            if test in range(420000000, 450000000):
                self.adif_BAND = "70cm"
                break
            if test in range(902000000, 928000000):
                self.adif_BAND = "33cm"
                break
            if test in range(1240000000, 1300000000):
                self.adif_BAND = "23cm"
                break
            # No match found
            self.adif_BAND = "OOB"
            break
        self.debug_log(self.log_debug,"get_band: BAND: " + str(self.adif_BAND))        
        self.debug_log(self.log_entry,"get_band: --Exit--")

    def print_adif(self):
        """ Print adif fields """
        self.debug_log(self.log_entry,"print_adif: --Enter--")
        self.debug_log(self.log_debug,'print_adif: adif_ARI_PROV: ' + self.adif_ARI_PROV)
        self.debug_log(self.log_debug,'print_adif: adif_ARRL_SECT: ' + self.adif_ARRL_SECT)
        self.debug_log(self.log_debug,'print_adif: adif_BAND: ' + self.adif_BAND)
        self.debug_log(self.log_debug,'print_adif: adif_CALL: ' + self.adif_CALL)
        self.debug_log(self.log_debug,'print_adif: adif_CHECK: ' + self.adif_CHECK)
        self.debug_log(self.log_debug,'print_adif: adif_CLASS: ' + self.adif_CLASS)
        self.debug_log(self.log_debug,'print_adif: adif_COMMAND: ' + self.adif_COMMAND)
        self.debug_log(self.log_debug,'print_adif: adif_COMMENT: ' + self.adif_COMMENT)
        self.debug_log(self.log_debug,'print_adif: adif_CONTEST_ID: ' + self.adif_CONTEST_ID)
        self.debug_log(self.log_debug,'print_adif: adif_CQZ: ' + self.adif_CQZ)
        self.debug_log(self.log_debug,'print_adif: adif_DIG: ' + self.adif_DIG)
        self.debug_log(self.log_debug,'print_adif: adif_DISTRIKT: ' + self.adif_DISTRIKT)
        self.debug_log(self.log_debug,'print_adif: adif_DOK: ' + self.adif_DOK)
        self.debug_log(self.log_debug,'print_adif: adif_FREQ: ' + self.adif_FREQ)
        self.debug_log(self.log_debug,'print_adif: adif_FREQ_RX: ' + self.adif_FREQ_RX)
        self.debug_log(self.log_debug,'print_adif: adif_GRIDSQUARE: ' + self.adif_GRIDSQUARE)
        self.debug_log(self.log_debug,'print_adif: adif_HOST: ' + self.adif_HOST)
        self.debug_log(self.log_debug,'print_adif: adif_HOST_IP: ' + self.adif_HOST_IP)
        self.debug_log(self.log_debug,'print_adif: adif_HOST_PORT: ' + self.adif_HOST_PORT)
        self.debug_log(self.log_debug,'print_adif: adif_IARU_ZONE: ' + self.adif_IARU_ZONE)
        self.debug_log(self.log_debug,'print_adif: adif_IOTA: ' + self.adif_IOTA)
        self.debug_log(self.log_debug,'print_adif: adif_ITUZ: ' + self.adif_ITUZ)
        self.debug_log(self.log_debug,'print_adif: adif_KDA: ' + self.adif_KDA)
        self.debug_log(self.log_debug,'print_adif: adif_LAT: ' + self.adif_LAT)
        self.debug_log(self.log_debug,'print_adif: adif_LON: ' + self.adif_LON)
        self.debug_log(self.log_debug,'print_adif: adif_MODE: ' + self.adif_MODE)
        self.debug_log(self.log_debug,'print_adif: adif_MY_CNTY: ' + self.adif_MY_CNTY)
        self.debug_log(self.log_debug,'print_adif: adif_MY_GRIDSQUARE: ' + self.adif_MY_GRIDSQUARE)
        self.debug_log(self.log_debug,'print_adif: adif_MY_NAME: ' + self.adif_MY_NAME)
        self.debug_log(self.log_debug,'print_adif: adif_NAME: ' + self.adif_NAME)
        self.debug_log(self.log_debug,'print_adif: adif_NAQSO_SECT: ' + self.adif_NAQSO_SECT)
        self.debug_log(self.log_debug,'print_adif: adif_OBLAST: ' + self.adif_OBLAST)
        self.debug_log(self.log_debug,'print_adif: adif_OFFSET: ' + self.adif_OFFSET)
        self.debug_log(self.log_debug,'print_adif: adif_OPERATOR: ' + self.adif_OPERATOR)
        self.debug_log(self.log_debug,'print_adif: adif_PFX: ' + self.adif_PFX)
        self.debug_log(self.log_debug,'print_adif: adif_POINTS: ' + str(self.adif_POINTS))
        self.debug_log(self.log_debug,'print_adif: adif_PRECEDENCE: ' + self.adif_PRECEDENCE)
        self.debug_log(self.log_debug,'print_adif: adif_QSO_COLOR: ' + self.adif_QSO_COLOR)
        self.debug_log(self.log_debug,'print_adif: adif_QSO_DATE: ' + self.adif_QSO_DATE)
        self.debug_log(self.log_debug,'print_adif: adif_QSO_ICON: ' + self.adif_QSO_ICON)
        self.debug_log(self.log_debug,'print_adif: adif_QTH: ' + self.adif_QTH)
        self.debug_log(self.log_debug,'print_adif: adif_RADIO: ' + self.adif_RADIO)
        self.debug_log(self.log_debug,'print_adif: adif_RADIO_NR: ' + self.adif_RADIO_NR)
        self.debug_log(self.log_debug,'print_adif: adif_RDA: ' + self.adif_RDA)
        self.debug_log(self.log_debug,'print_adif: adif_RST_RCVD: ' + self.adif_RST_RCVD)
        self.debug_log(self.log_debug,'print_adif: adif_RST_SENT: ' + self.adif_RST_SENT)
        self.debug_log(self.log_debug,'print_adif: adif_RX_PWR: ' + self.adif_RX_PWR)
        self.debug_log(self.log_debug,'print_adif: adif_SAC: ' + self.adif_SAC)
        self.debug_log(self.log_debug,'print_adif: adif_SECT: ' + self.adif_SECT)
        self.debug_log(self.log_debug,'print_adif: adif_SECTION: ' + self.adif_SECTION)
        self.debug_log(self.log_debug,'print_adif: adif_SRX: ' + self.adif_SRX)
        self.debug_log(self.log_debug,'print_adif: adif_STATE: ' + self.adif_STATE)
        self.debug_log(self.log_debug,'print_adif: adif_STATION: ' + self.adif_STATION)
        self.debug_log(self.log_debug,'print_adif: adif_STATION_CALLSIGN: ' + self.adif_STATION_CALLSIGN)
        self.debug_log(self.log_debug,'print_adif: adif_STX: ' + self.adif_STX)
        self.debug_log(self.log_debug,'print_adif: adif_SUBMODE: ' + self.adif_SUBMODE)
        self.debug_log(self.log_debug,'print_adif: adif_TIME_OFF: ' + self.adif_TIME_OFF)
        self.debug_log(self.log_debug,'print_adif: adif_TIME_ON: ' + self.adif_TIME_ON)
        self.debug_log(self.log_debug,'print_adif: adif_TX_PWR: ' + self.adif_TX_PWR)
        self.debug_log(self.log_debug,'print_adif: adif_UKEI: ' + self.adif_UKEI)
        self.debug_log(self.log_debug,'print_adif: adif_VE_PROV: ' + self.adif_VE_PROV)
        self.debug_log(self.log_debug,'print_adif: adif_WWPMC: ' + self.adif_WWPMC)
        self.debug_log(self.log_debug,'print_adif: computer_name: ' + self.computer_name)
        self.debug_log(self.log_entry,"print_adif: --Exit--")

    def get_grid(self):
        """ Lookup callsign and get grid """
        self.debug_log(self.log_entry,"get_grid: --Enter--")
        if not self.adif_CALL:
            self.debug_log(self.log_warning,"get_grid: CALL is missing")
            self.debug_log(self.log_entry,"get_grid: --Exit--")
            return
        if self.adif_GRIDSQUARE:
            self.debug_log(self.log_debug,"get_grid: GRID already exists: " + self.adif_GRIDSQUARE)
            self.debug_log(self.log_entry,"get_grid: --Exit--")
            return        
        # Check for callsign modifiers (/x)
        search_token = "/"
        start = self.adif_CALL.lower().find(search_token.lower())
        if start == -1:
            self.debug_log(self.log_debug,"get_grid: Callsign modifier NOT found: " + self.adif_CALL)
        else:
            self.debug_log(self.log_debug,"get_grid: Callsign modifier FOUND: " + self.adif_CALL)
            callindex = self.adif_CALL.split("/",1)
            if len(callindex) > 0:
                self.adif_CALL = str(callindex[0].strip())
        self.debug_log(self.log_debug,"get_grid: Lookup CALL: " + self.adif_CALL)
        # Try grid lookup via databases in order. First match wins.
        if not self.adif_GRIDSQUARE:
            self.get_grid_fccdb()
        if not self.adif_GRIDSQUARE:
            self.get_grid_hamcall_cd()
        if not self.adif_GRIDSQUARE:
            self.get_grid_rac_cd()
        if not self.adif_GRIDSQUARE:
            self.get_grid_localdb()
        if not self.adif_GRIDSQUARE:
            self.get_grid_callook()
        if not self.adif_GRIDSQUARE:
            self.get_grid_hamcall_net()

        # Check if we are still missing the grid
        if not self.adif_GRIDSQUARE:
            self.debug_log(self.log_debug,"get_grid: GRID not found")
            self.update_rejects()
            self.debug_log(self.log_entry,"get_grid: --Exit--")
            return

        # Append comment to indicate grid was from lookup
        self.adif_COMMENT = "[!] " + self.adif_COMMENT
        self.debug_log(self.log_debug,"get_grid: GRID: " + self.adif_GRIDSQUARE)
        self.debug_log(self.log_debug,"get_grid: COMMENT: " + self.adif_COMMENT)
        self.debug_log(self.log_entry,"get_grid: --Exit--")

    def get_grid_fccdb(self):
        """ OFFLINE - FCC Database Lookup """
        self.debug_log(self.log_entry,"get_grid_fccdb: --Enter--")
        if self.fcc_lookup:
            try:
                # Check for empty database
                if not self.fcc_data:
                    self.debug_log(self.log_debug,"get_grid_fccdb: FCC Database is empty")
                    self.debug_log(self.log_entry,"get_grid_fccdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_fccdb: CALL: " + self.adif_CALL)
                search_token = self.adif_CALL
                start = self.fcc_data.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"get_grid_fccdb: CALL START not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_fccdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_fccdb: Start: " + str(start))
                search_token = "\n"
                end = self.fcc_data.lower().find(search_token.lower(),start)
                if end == -1:
                    self.debug_log(self.log_debug,"get_grid_fccdb: CALL END not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_fccdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_fccdb: End: " + str(end))
                callindexraw = self.fcc_data[start:end]
                self.debug_log(self.log_debug,"get_grid_fccdb: Raw: " + callindexraw)
                callindex = callindexraw.split(",",1)
                self.debug_log(self.log_debug,"get_grid_fccdb: Grid: " + str(callindex[1].strip()))
                if len(callindex) > 0:
                    self.adif_GRIDSQUARE = str(callindex[1].strip())
            except:
                self.debug_log(self.log_warning,"get_grid_fccdb: Unable to retrieve GRID from FCC Database")
        self.debug_log(self.log_entry,"get_grid_fccdb: --Exit--")

    def get_grid_hamcall_cd(self):
        """ OFFLINE - Lookup HamCall CD Data """
        self.debug_log(self.log_entry,"get_grid_hamcall_cd: --Enter--")
        if self.hamcallcd_lookup:
            try:
                # Check for empty database
                if not self.hc_cd_data:
                    self.debug_log(self.log_debug,"get_grid_hamcall_cd: HamCall CD Database is empty")
                    self.debug_log(self.log_entry,"get_grid_hamcall_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_hamcall_cd: CALL: " + self.adif_CALL)
                search_token = self.adif_CALL
                start = self.hc_cd_data.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"get_grid_hamcall_cd: CALL START not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_hamcall_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_hamcall_cd: Start: " + str(start))
                search_token = "\n"
                end = self.hc_cd_data.lower().find(search_token.lower(),start)
                if end == -1:
                    self.debug_log(self.log_debug,"get_grid_hamcall_cd: CALL END not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_hamcall_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_hamcall_cd: End: " + str(end))
                callindexraw = self.hc_cd_data[start:end]
                self.debug_log(self.log_debug,"get_grid_hamcall_cd: Raw: " + callindexraw)
                callindex = callindexraw.split(",",1)
                self.debug_log(self.log_debug,"get_grid_hamcall_cd: Grid: " + str(callindex[1].strip()))
                if len(callindex) > 0:
                    self.adif_GRIDSQUARE = str(callindex[1].strip())
            except:
                self.debug_log(self.log_warning,"get_grid_hamcall_cd: Unable to retrieve GRID from HamCall CD")
        self.debug_log(self.log_entry,"get_grid_hamcall_cd: --Exit--")

    def get_grid_rac_cd(self):
        """ OFFLINE - Lookup RAC CD Data """
        self.debug_log(self.log_entry,"get_grid_rac_cd: --Enter--")
        if self.raccd_lookup:
            try:
                # Check for empty database
                if not self.rac_cd_data:
                    self.debug_log(self.log_debug,"get_grid_rac_cd: RAC CD Database is empty")
                    self.debug_log(self.log_entry,"get_grid_rac_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_rac_cd: CALL: " + self.adif_CALL)
                search_token = self.adif_CALL
                start = self.rac_cd_data.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"get_grid_rac_cd: CALL START not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_rac_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_rac_cd: Start: " + str(start))
                search_token = "\n"
                end = self.rac_cd_data.lower().find(search_token.lower(),start)
                if end == -1:
                    self.debug_log(self.log_debug,"get_grid_rac_cd: CALL END not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_rac_cd: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_rac_cd: End: " + str(end))
                callindexraw = self.rac_cd_data[start:end]
                self.debug_log(self.log_debug,"get_grid_rac_cd: Raw: " + callindexraw)
                callindex = callindexraw.split(",",1)
                self.debug_log(self.log_debug,"get_grid_rac_cd: Grid: " + str(callindex[1].strip()))
                if len(callindex) > 0:
                    self.adif_GRIDSQUARE = str(callindex[1].strip())
            except:
                self.debug_log(self.log_warning,"get_grid_rac_cd: Unable to retrieve GRID from RAC CD Database")
        self.debug_log(self.log_entry,"get_grid_rac_cd: --Exit--")

    def get_grid_localdb(self):
        """ OFFLINE - Local Database Lookup """
        self.debug_log(self.log_entry,"get_grid_localdb: --Enter--")
        if self.local_lookup:
            try:
                # Check for empty database
                if not self.local_data:
                    self.debug_log(self.log_debug,"get_grid_localdb: Local Database is empty")
                    self.debug_log(self.log_entry,"get_grid_localdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_localdb: CALL: " + self.adif_CALL)
                search_token = self.adif_CALL
                start = self.local_data.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"get_grid_localdb: CALL START not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_localdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_localdb: Start: " + str(start))
                search_token = "\n"
                end = self.local_data.lower().find(search_token.lower(),start)
                if end == -1:
                    self.debug_log(self.log_debug,"get_grid_localdb: CALL END not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_localdb: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_localdb: End: " + str(end))
                callindexraw = self.local_data[start:end]
                self.debug_log(self.log_debug,"get_grid_localdb: Raw: " + callindexraw)
                callindex = callindexraw.split(",",1)
                self.debug_log(self.log_debug,"get_grid_localdb: Grid: " + str(callindex[1].strip()))
                if len(callindex) > 0:
                    self.adif_GRIDSQUARE = str(callindex[1].strip())
            except:
                self.debug_log(self.log_warning,"get_grid_localdb: Unable to retrieve GRID from Local Database")
        self.debug_log(self.log_entry,"get_grid_localdb: --Exit--")

    def get_grid_callook(self):
        """ ONLINE - callook.info Lookup """
        self.debug_log(self.log_entry,"get_grid_callook: --Enter--")
        if self.callook_lookup:
            try:
                self.debug_log(self.log_debug,"get_grid_callook: CALL: " + self.adif_CALL)
                query = requests.get('https://callook.info/{}/json'.format(self.adif_CALL), verify=False)
                result = json.loads(query.text)    
                self.debug_log(self.log_hidebug,result)
                if not result["status"] == "VALID":
                    self.debug_log(self.log_debug,"get_grid_callook: Invalid STATUS")
                    self.debug_log(self.log_entry,"get_grid_callook: --Exit--")
                    return
                self.adif_GRIDSQUARE = result["location"]["gridsquare"]
                self.debug_log(self.log_debug,"get_grid_callook: Grid: " + self.adif_GRIDSQUARE)
                if self.adif_GRIDSQUARE:
                    self.update_localdb()
            except:
                self.debug_log(self.log_warning,"get_grid_callook: Unable to retrieve GRID from callook.info")
        self.debug_log(self.log_entry,"get_grid_callook: --Exit--")

    def get_grid_hamcall_net(self):
        """ # ONLINE - hamcall.net Lookup """
        self.debug_log(self.log_entry,"get_grid_hamcall_net: --Enter--")
        if self.hamcallol_lookup:
            try:
                self.debug_log(self.log_debug,"get_grid_hamcall_net: CALL: " + self.adif_CALL)
                # build the url
                url = "https://hamcall.net/call?"
                url = url + "username=" + str(self.hamcallol_username)
                url = url + "&password=" + str(self.hamcallol_password)
                url = url + "&rawlookup=1"
                url = url + "&callsign=" + str(self.adif_CALL)
                url = url + "&program=JS8Call_Monitor"
                query = requests.get(url, verify=False)
                self.debug_log(self.log_hidebug,query.text)
                
                # Now parse the result
                start = -1
                for pos in range(0,len(query.text)):
                    # look for GRID field; high ASCII 202
                    if ord(query.text[pos]) == 202:
                        start = pos
                        break
                if start == -1:
                    self.debug_log(self.log_debug,"get_grid_hamcall_net: GRID START not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_hamcall_net: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_hamcall_net: GRID START found: " + str(start))
                # find the end of the grid
                end = -1
                for pos in range(start + 1,start + 11):
                    # look for the next high ASCII chr
                    if ord(query.text[pos]) > 180:
                        end = pos
                        break
                if end == -1:
                    self.debug_log(self.log_debug,"get_grid_hamcall_net: GRID END not found: " + self.adif_CALL)
                    self.debug_log(self.log_entry,"get_grid_hamcall_net: --Exit--")
                    return
                self.debug_log(self.log_debug,"get_grid_hamcall_net: GRID END found: " + str(end))
                # get result and remove non-ascii garbage
                result = query.text[start + 1:end]
                result = str(re.sub(r'[^\x00-\x7f]',r'',result))
                self.debug_log(self.log_debug,"get_grid_hamcall_net: Grid: " + str(result.strip()))
                self.adif_GRIDSQUARE = result.strip()
                if self.adif_GRIDSQUARE:
                    self.update_localdb()
            except:
                self.debug_log(self.log_warning,"get_grid_hamcall_net: Unable to retrieve GRID from HamCall.net")   
        self.debug_log(self.log_entry,"get_grid_hamcall_net: --Exit--")

    def update_localdb(self):
        """ Update Local Database file """
        self.debug_log(self.log_entry,"update_localdb: --Enter--")
        if not self.local_learn:
            self.debug_log(self.log_debug,"update_localdb: Learning is disabled")
            self.debug_log(self.log_entry,"update_localdb: --Exit--")
            return
        if not self.adif_CALL:
            self.debug_log(self.log_warning,"update_localdb: CALL is missing")
            self.debug_log(self.log_entry,"update_localdb: --Exit--")
            return
        if not self.adif_GRIDSQUARE:
            self.debug_log(self.log_warning,"update_localdb: GRID is missing")
            self.debug_log(self.log_entry,"update_localdb: --Exit--")
            return
        try:
            # create the database entry
            self.debug_log(self.log_debug,"update_localdb: Updating local database...")
            dbEntry = self.adif_CALL + "," + self.adif_GRIDSQUARE + "\n"
            
            # append to local file
            fh = ''
            fh = open(self.grid_databases + "JS8monitor_localgrids.dat",'a')
            fh.write(dbEntry)
            fh.close()
            self.debug_log(self.log_debug,"update_localdb: Upadated local Database file")

            # append to in-memory local database
            # Create database if empty, otherwise append entry.
            if not self.local_data:
                self.local_data = dbEntry
            else:
                self.local_data = self.local_data + dbEntry
            self.debug_log(self.log_debug,"update_localdb: Upadated local Database in Memory")
            self.debug_log(self.log_debug,"update_localdb: Size: " + str(len(self.local_data)))
        except:
            # Database failed to update
            if fh:
                fh.close()
            self.debug_log(self.log_warning,"update_localdb: Failed to update Local Database")
        self.debug_log(self.log_entry,"update_localdb: --Exit--")

    def update_rejects(self):
        """ Update Rejects Database file """
        self.debug_log(self.log_entry,"update_rejects: --Enter--")
        if not self.collect_rejects:
            self.debug_log(self.log_debug,"update_rejects: Collecting Rejects is disabled")
            self.debug_log(self.log_entry,"update_rejects: --Exit--")
            return
        if not self.adif_CALL:
            self.debug_log(self.log_warning,"update_rejects: CALL is missing")
            self.debug_log(self.log_entry,"update_rejects: --Exit--")
            return
        try:
            # create the database entry
            self.debug_log(self.log_debug,"update_rejects: Updating rejects database...")
            dbEntry = self.adif_CALL + "\n"
            
            # append to local file
            fh = ''
            fh = open(self.grid_databases + "JS8monitor_rejects.dat",'a')
            fh.write(dbEntry)
            fh.close()
            self.debug_log(self.log_debug,"update_rejects: Updated rejects database file")
        except:
            # Database failed to update
            if fh:
                fh.close()
            self.debug_log(self.log_warning,"update_rejects: Failed to update rejects database")
        self.debug_log(self.log_entry,"update_rejects: --Exit--")        
    
    def get_host(self, source):
        """ Get host name from source IP tuple """
        self.debug_log(self.log_entry,"get_host: --Enter--")
        if not source:
            self.debug_log(self.log_warning,"get_host: SOURCE is missing")
            self.debug_log(self.log_entry,"get_host: --Exit--")
            return

        try:
            # The raw source should be in the form of a host/port tuple
            # I.E. ('127.0.0.1', 2171)
            sourceindex = source.split(",",1)
            source_ip = sourceindex[0]
            start = 2
            end = len(source_ip)-1
            source_ip = source_ip[start:end]
            self.debug_log(self.log_debug,"get_host: Source IP: " + source_ip)

            source_port = sourceindex[1]
            start = 0
            end = len(source_port)-1
            source_port = source_port[start:end]
            self.debug_log(self.log_debug,"get_host: Source Port: " + source_port)

            # Capture the IP/port info
            self.adif_HOST_IP = str(source_ip.strip())
            self.adif_HOST_PORT = str(source_port.strip())

            # Now resolve the name using the host database
            # Check for empty database
            if not self.host_data:
                self.debug_log(self.log_debug,"get_host: Host Database is empty")
                self.debug_log(self.log_entry,"get_host: --Exit--")
                return
            
            search_token = source_ip
            start = self.host_data.lower().find(search_token.lower())
            if start == -1:
                self.debug_log(self.log_debug,"get_host: Source START not found: " + source_ip)
                self.debug_log(self.log_entry,"get_host: --Exit--")
                return
            self.debug_log(self.log_debug,"get_host: Start: " + str(start))
            search_token = "\n"
            end = self.host_data.lower().find(search_token.lower(),start)
            if end == -1:
                self.debug_log(self.log_debug,"get_host: Source END not found: " + source_ip)
                self.debug_log(self.log_entry,"get_host: --Exit--")
                return
            self.debug_log(self.log_debug,"get_host: End: " + str(end))
            hostindexraw = self.host_data[start:end]
            self.debug_log(self.log_debug,"get_host: Raw: " + hostindexraw)
            hostindex = hostindexraw.split(",",1)
            self.debug_log(self.log_debug,"get_host: Host: " + str(hostindex[1].strip()))
            if len(hostindex) > 0:
                self.adif_HOST = str(hostindex[1].strip())
        except:
            self.debug_log(self.log_warning,"get_host: Unable to retrieve HOST from Host Database")
        self.debug_log(self.log_entry,"get_host: --Exit--")

    def debug_log(self, level, msg):
        """ Log debug message to console and/or file """
        if not level:
            return
        if not msg:
            return

        # Calculate tags
        tag = ''
        if level == self.log_smdr:
            tag = '[SMDR]'
        if level == self.log_critical:
            tag = '[CRITICAL]'
        if level == self.log_error:
            tag = '[ERROR]'
        if level == self.log_warning:
            tag = '[WARNING]'
        if level == self.log_info:
            tag = '[INFO]'

        # Calculate UTC DateTime stamp
        mytime = datetime.datetime.utcnow()
        dg = mytime.strftime("%Y-%m-%d")
        tg = mytime.strftime("%H:%M:%S")

        # Format message compatible for machine procesing
        try:
            msgF = dg + "|" + tg + "|" + str(self.adif_HOST) + "|" + tag + "|" + msg
        except:
            msgF = dg + "|" + tg + "|" + str(self.adif_HOST) + "|" + tag + "|[object]"
        
        if level in range(1, self.consolelevel+1):
            print (msgF)
        if level in range(1, self.logfilelevel+1):
            self.log_handle.write(msgF)
            self.log_handle.write("\n")
            self.log_handle.flush()

    def to_latlng(self, gs):
            """
            Takes in a Maidenhead locator string (gridsquare) and converts it
            into a tuple of WGS-84 compatible (latitude, longitude).
            """
            self.debug_log(self.log_entry,"to_latlng: --Enter--")
            self.debug_log(self.log_debug,"to_latlng: Grid: %s" %gs)
            if len(gs) < 4:
                    self.debug_log(self.log_debug,"to_latlng: Invalid gridsquare specified.")
                    self.debug_log(self.log_entry,"to_latlng: --Exit--")
                    return None, None
            lat, lng = None, None
            if len(gs) > 4:
                    lng = self._to_lng(gs[0], int(gs[2]), gs[4])
                    lat = self._to_lat(gs[1], int(gs[3]), gs[5])
            else:
                    lng = self._to_lng(gs[0], int(gs[2]))
                    lat = self._to_lat(gs[1], int(gs[3]))

            # if either calc fails, return error
            if lat==None or lng==None:
                self.debug_log(self.log_debug,"to_latlng: lat: %s lng: %s" %(str(lat), str(lng)))
                self.debug_log(self.log_entry,"to_latlng: --Exit--")
                return None, None

            self.debug_log(self.log_debug,"to_latlng: lat: %s lng: %s" %(str(lat), str(lng)))
            self.debug_log(self.log_entry,"to_latlng: --Exit--")
            return round(lat, 3), round(lng, 3)

    def _to_lat(self, field, square, subsq=None):
            """
            Converts the specified field, square, and (optional) sub-square
            into a WGS-84 compatible latitude value.
            """
            self.debug_log(self.log_entry,"_to_lat: --Enter--")
            try:
                lat = (string.ascii_uppercase.index(field.upper()) * 10.0) - 90
                lat += square
                if subsq is not None:
                        lat += (string.ascii_lowercase.index(subsq.lower()) / 24.0)
                        lat += 1.25 / 60.0 
                else:
                        lat += 0.5
            except:
                self.debug_log(self.log_debug,"_to_lat: Unable to calculate lat")
                lat = None
                
            self.debug_log(self.log_entry,"_to_lat: --Exit--")
            return lat

    def _to_lng(self, field, square, subsq=None):
            """
            Converts the specified field, square, and (optional) sub-square
            into a WGS-84 compatible longitude value.
            """
            self.debug_log(self.log_entry,"_to_lng: --Enter--")
            try:
                lng = (string.ascii_uppercase.index(field.upper()) * 20.0) - 180
                lng += square * 2.0
                if subsq is not None:
                    lng += string.ascii_lowercase.index(subsq.lower()) / 12.0
                    lng += 2.5 / 60.0
                else:
                    lng += 1.0
            except:
                self.debug_log(self.log_debug,"_to_lng: Unable to calculate lng")
                lng = None
                
            self.debug_log(self.log_entry,"_to_lng: --Exit--")
            return lng

    def send_alert(self, sub, msg):
        """ Send Email Alert """
        self.debug_log(self.log_entry,"send_alert: --Enter--")
        # check if alerts are enabled
        if self.smtpenabled:
            if sub:
                self.debug_log(self.log_hidebug,"send_alert: -> sub: " + sub)
            else:
                self.debug_log(self.log_warning,"send_alert: Missing SUBJECT")
                self.debug_log(self.log_entry,"send_alert: --Exit--")
                return
            if msg:
                self.debug_log(self.log_hidebug,"send_alert: -> msg: " + msg)
            else:
                self.debug_log(self.log_warning,"send_alert: Missing MESSAGE")
                self.debug_log(self.log_entry,"send_alert: --Exit--")
                return

            # prepare message for SNMP consumption
            # replaces spaces with peroids
            msg = str(msg.replace(" ", "."))

            # compose the email
            body = ' '.join(msg)
            alertMsg = MIMEText(body)
            alertMsg['Subject'] = sub
            alertMsg['From'] = self.mailfrom
            alertMsg['To'] = self.mailto
            self.debug_log(self.log_debug,"send_alert: Sending email...")
            # send email
            s = smtplib.SMTP(self.smtphost, self.smtpport)
            if self.smtpuser != "" and self.smtppass != "":
                self.debug_log(self.log_debug,"send_alert: Using SMTP auth")
                s.login(self.smtpuser, self.smtppass)
            s.sendmail(self.mailfrom, self.mailto, alertMsg.as_string())
            s.quit()
            # email sent
            self.debug_log(self.log_info,"send_alert: Email sent") 
        self.debug_log(self.log_entry,"send_alert: --Exit--")

    def log_new_qso(self):
        """ Log new QSO to various loggers """
        self.debug_log(self.log_entry,"log_new_qso: --Enter--")
        self.debug_log(self.log_debug,"log_new_qso: Gridsquare length set to " + str(self.gridlength))
        self.adif_GRIDSQUARE = self.adif_GRIDSQUARE[:self.gridlength]
        self.log_qso_n1mm()
        self.log_qso_gridtracker()
        self.log_qso_geoserver()
        self.log_qso_yaac()
        self.log_qso_adif()
        self.debug_log(self.log_entry,"log_new_qso: --Exit--")
        
    def log_qso_n1mm(self):
        """ Log new QSO to N1MM """
        self.debug_log(self.log_entry,"log_qso_n1mm: --Enter--")
        # Check if N1MM stream enabled
        if self.n1mmenabled:
            self.send_buffer = ""
            tags = ""

            # Format the frequency in MHz for consumption by N1MM.
            # This is done so proper formatting of frequency is maintained
            # when exporting ADIF files from N1MM logs.

            # Note: County mapper has a bug that appears if frequency has
            # more than 6 digits.
       
            # build records
            # add or remove adif fields to be passed to N1MM here
            try:
                record = {}
                record['band'] = str(self.adif_BAND)
                record['call'] = str(self.adif_CALL)
                record['comment'] = str(self.adif_COMMENT)
                record['freq'] = str(float(self.adif_FREQ)/1000000)
                record['gridsquare'] = str(self.adif_GRIDSQUARE)
                record['mode'] = str(self.adif_MODE)
                record['my_gridsquare'] = str(self.adif_MY_GRIDSQUARE)
                record['operator'] = str(self.adif_OPERATOR)
                record['qso_date'] = str(self.adif_QSO_DATE)
                record['qso_date_off'] = str(self.adif_QSO_DATE)
                record['rst_rcvd'] = str(self.adif_RST_RCVD)
                record['rst_sent'] = str(self.adif_RST_SENT)
                record['station_callsign'] = str(self.adif_OPERATOR)
                record['submode'] = str(self.adif_SUBMODE)
                record['time_off'] = str(self.adif_TIME_OFF)
                record['time_on'] = str(self.adif_TIME_ON)
                self.debug_log(self.log_hidebug,record)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_n1mm: Error in Phase 1")
                self.debug_log(self.log_entry,"log_qso_n1mm: --Exit--")
                return
 
            # build fields
            try:
                fields = []
                for k,v in iteritems(record):
                    fields.append("<%s:%d>%s" % (k, len(v), v))
                fields.append('<eor>')
                self.debug_log(self.log_hidebug,fields)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_n1mm: Error in Phase 2")
                self.debug_log(self.log_entry,"log_qso_n1mm: --Exit--")
                return

            # attach header for N1MM
            try:
                for i in range(len(fields)):
                    tags = tags + fields[i]          
                self.send_buffer = "<command:3>Log<parameters:%d>%s" % (len(tags), tags)
                self.debug_log(self.log_hidebug,self.send_buffer + "\n")
            except:
                self.debug_log(self.log_error,"log_qso_n1mm: Error in Phase 3")
                self.debug_log(self.log_entry,"log_qso_n1mm: --Exit--")
                return
            
            # now send the contents of send_buffer to N1MM
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.n1mmhost,int(self.n1mmport)))          
                self.debug_log(self.log_debug,"log_qso_n1mm: Sending N1MM log...")
                sock.send(self.send_buffer.encode('utf-8'))
                self.debug_log(self.log_info,"log_qso_n1mm: Sent N1MM log")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"log_qso_n1mm: %s Unable to establish connection to N1MM" % msg)
        self.debug_log(self.log_entry,"log_qso_n1mm: --Exit--")

    def log_qso_gridtracker(self):
        """ Log new QSO to GRIDTRACKER """
        self.debug_log(self.log_entry,"log_qso_gridtracker: --Enter--")
        # Check if GridTracker stream enabled
        if self.gtenabled:
            self.send_buffer = ""
            tags = ""

            # build records
            # add or remove adif fields to be passed to GridTracker here
            try:
                record = {}
                record['band'] = str(self.adif_BAND)
                record['call'] = str(self.adif_CALL)
                record['comment'] = str(self.adif_COMMENT)
                record['freq'] = str(self.adif_FREQ)
                record['gridsquare'] = str(self.adif_GRIDSQUARE)
                record['mode'] = str(self.adif_MODE)
                record['my_gridsquare'] = str(self.adif_MY_GRIDSQUARE)
                record['operator'] = str(self.adif_OPERATOR)
                record['qso_date'] = str(self.adif_QSO_DATE)
                record['qso_date_off'] = str(self.adif_QSO_DATE)
                record['rst_rcvd'] = str(self.adif_RST_RCVD)
                record['rst_sent'] = str(self.adif_RST_SENT)
                record['station_callsign'] = str(self.adif_OPERATOR)
                record['submode'] = str(self.adif_SUBMODE)
                record['time_off'] = str(self.adif_TIME_OFF)
                record['time_on'] = str(self.adif_TIME_ON)
                self.debug_log(self.log_hidebug,record)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_gridtracker: Error in Phase 1")
                self.debug_log(self.log_entry,"log_qso_gridtracker: --Exit--")
                return

            # build fields
            try:
                fields = []
                for k,v in iteritems(record):
                    fields.append("<%s:%d>%s" % (k, len(v), v))
                fields.append('<eor>')
                self.debug_log(self.log_hidebug,fields)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_gridtracker: Error in Phase 2")
                self.debug_log(self.log_entry,"log_qso_gridtracker: --Exit--")
                return

            # attach header for GridTracker
            try:
                for i in range(len(fields)):
                    tags = tags + fields[i]          
                self.send_buffer = "<adif_ver:5>3.0.7<programid:6>WSJT-X<EOH>%s" % (tags)
                self.debug_log(self.log_hidebug,self.send_buffer + "\n")
            except:
                self.debug_log(self.log_error,"log_qso_gridtracker: Error in Phase 3")
                self.debug_log(self.log_entry,"log_qso_gridtracker: --Exit--")
                return

            # build log packet for GridTracker
            try:
                pkt = pywsjtx.LoggedADIFPacket.Builder(self.MY_WSJTX_ID,self.send_buffer)
            except:
                self.debug_log(self.log_error,"log_qso_gridtracker: Error in Phase 4")
                self.debug_log(self.log_entry,"log_qso_gridtracker: --Exit--")
                return
    
            # now send the packet to GridTracker
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.gthost,int(self.gtport)))         
                self.debug_log(self.log_debug,"log_qso_gridtracker: Sending GRIDTRACKER log...")
                sock.send(pkt)
                self.debug_log(self.log_info,"log_qso_gridtracker: Sent GRIDTRACKER log")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"log_qso_gridtracker: %s Unable to establish connection to GRIDTRACKER" % msg)
        self.debug_log(self.log_entry,"log_qso_gridtracker: --Exit--")

    def refresh_gts(self):
        """ Refresh GridTracker State Variables """
        self.debug_log(self.log_entry,"refresh_gts: --Enter--")
        # First lets initialize the state variables
        self.GTS_wsjtx_id = ""
        self.GTS_dial_frequency = 0
        self.GTS_mode = ""
        self.GTS_dx_call = ""
        self.GTS_report = ""
        self.GTS_tx_mode = ""
        self.GTS_tx_enabled = False
        self.GTS_transmitting = False
        self.GTS_decoding = False
        self.GTS_rx_df = 0
        self.GTS_tx_df = 0
        self.GTS_de_call = ""
        self.GTS_de_grid = ""
        self.GTS_dx_grid = ""
        self.GTS_tx_watchdog = False
        self.GTS_sub_mode = ""
        self.GTS_fast_mode = False
        self.GTS_special_op_mode = 0

        # Now lets update the state variables       
        self.GTS_wsjtx_id = self.MY_WSJTX_ID
        self.GTS_dial_frequency = (int(self.adif_FREQ))
        self.GTS_mode = str(self.adif_MODE)
        self.GTS_dx_call = str(self.adif_CALL)
        self.GTS_report = ""
        self.GTS_tx_mode = str(self.adif_MODE)
        self.GTS_tx_enabled = False
        self.GTS_transmitting = False
        self.GTS_decoding = False
        self.GTS_rx_df = int(self.adif_RST_RCVD)
        self.GTS_tx_df = int(self.adif_RST_SENT)
        self.GTS_de_call = "" #str(self.adif_OPERATOR) #QTH display
        self.GTS_de_grid = "" #str(self.adif_MY_GRIDSQUARE) #QTH display
        self.GTS_dx_grid = str(self.adif_GRIDSQUARE)
        self.GTS_tx_watchdog = False
        self.GTS_sub_mode = str(self.adif_SUBMODE)
        self.GTS_fast_mode = False
        self.GTS_special_op_mode = 0
        self.debug_log(self.log_entry,"refresh_gts: --Exit--")

    def send_status_gridtracker(self):
        """ Send GridTracker Status Message """
        self.debug_log(self.log_entry,"send_status_gridtracker: --Enter--")        
        # If enabled, send status update to GridTracker
        # This is needed to wake GridTraker up after restart.
        if self.gtenabled:
            # build status packet for GRIDTRACKER
            try:
                pkt = pywsjtx.StatusPacket.Builder(self.GTS_wsjtx_id, self.GTS_dial_frequency,
                        self.GTS_mode, self.GTS_dx_call, self.GTS_report, self.GTS_tx_mode,
                        self.GTS_tx_enabled, self.GTS_transmitting, self.GTS_decoding,
                        self.GTS_rx_df, self.GTS_tx_df, self.GTS_de_call, self.GTS_de_grid,
                        self.GTS_dx_grid, self.GTS_tx_watchdog, self.GTS_sub_mode,
                        self.GTS_fast_mode, self.GTS_special_op_mode)
            except:
                self.debug_log(self.log_error,"send_status_gridtracker: Error in Phase 1")
                self.debug_log(self.log_entry,"send_status_gridtracker: --Exit--")
                return

            # now send the packet to GridTracker
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.gthost,int(self.gtport)))          
                self.debug_log(self.log_debug,"send_status_gridtracker: Sending GRIDTRACKER status update...")
                sock.send(pkt)
                self.debug_log(self.log_info,"send_status_gridtracker: Sent GRIDTRACKER status update.")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"send_status_gridtracker: %s Unable to establish connection to GRIDTRACKER" % msg)
        self.debug_log(self.log_entry,"send_status_gridtracker: --Exit--")

    def send_decode_gridtracker(self):
        """ Send GridTracker Decode Message """
        self.debug_log(self.log_entry,"send_decode_gridtracker: --Enter--")        
        # If enabled, send decode messages to GridTracker
        if self.gtenabled:

            # build fields
            try:
                # calculate time
                utcnow = datetime.datetime.utcnow()
                utcmidnight = datetime.datetime(utcnow.year, utcnow.month, utcnow.day, 0, 0)
                millis_since_midnight = int((utcnow - datetime.datetime(utcnow.year, utcnow.month, utcnow.day, 0, 0)).total_seconds() * 1000)
                time = millis_since_midnight
           
                self.debug_log(self.log_debug,"send_decode_gridtracker: UTC Now: " + str(utcnow))
                self.debug_log(self.log_debug,"send_decode_gridtracker: UTC Midnight: " + str(utcmidnight))
                self.debug_log(self.log_debug,"send_decode_gridtracker: Millis since midnight: " + str(millis_since_midnight))
                self.debug_log(self.log_debug,"send_decode_gridtracker: Time: " + str(time))

                # calculate message

                # set default value
                gtmessage = str(self.adif_STATION) + " " + str(self.adif_CALL) + " " + str(self.adif_GRIDSQUARE[0:4])

                # process CQ
                self.debug_log(self.log_entry,"send_decode_gridtracker: ENTER Message CQ")
                message = self.adif_COMMAND
                search_token = "CQ"
                start = message.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: CQ NOT found")                
                else:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: CQ FOUND")
                    #gtmessage = "CQ" + " " + str(self.adif_STATION) + " " + str(self.adif_GRIDSQUARE[0:4])
                    gtmessage = "CQ" + " " + str(self.adif_CALL) + " " + str(self.adif_GRIDSQUARE[0:4])
                self.debug_log(self.log_entry,"send_decode_gridtracker: Exit Message CQ")

                # process SNR
                self.debug_log(self.log_entry,"send_decode_gridtracker: ENTER Message SNR")
                message = self.adif_COMMAND
                search_token = "SNR"
                start = message.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: SNR NOT found")                
                else:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: SNR FOUND")
                    #gtmessage = str(self.adif_STATION) + " " + str(self.adif_CALL) + " " + str(self.adif_RST_RCVD)
                    gtmessage = str(self.adif_STATION) + " " + str(self.adif_CALL) + " " + str(self.adif_GRIDSQUARE[0:4])
                self.debug_log(self.log_entry,"send_decode_gridtracker: Exit Message SNR")

                # process HEARTBEAT
                self.debug_log(self.log_entry,"send_decode_gridtracker: ENTER Message HEARTBEAT")
                message = self.adif_COMMAND
                search_token = "HEARTBEAT"
                start = message.lower().find(search_token.lower())
                if start == -1:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: HEARTBEAT NOT found")                
                else:
                    self.debug_log(self.log_debug,"send_decode_gridtracker: HEARTBEAT FOUND")
                    gtmessage = str(self.adif_STATION) + " " + str(self.adif_CALL) + " " + str(self.adif_GRIDSQUARE[0:4])
                self.debug_log(self.log_entry,"send_decode_gridtracker: Exit Message HEARTBEAT")

                self.debug_log(self.log_debug,"send_decode_gridtracker: Message set to " + str(gtmessage))
                # calculate other parameters
                new = True
                snr = int(self.adif_RST_SENT)
                deltaTime = 0.0
                deltaFreq = int(self.adif_OFFSET)
                mode = str(self.adif_MODE)
                low_confidence = False
                off_air = False
            except:
                self.debug_log(self.log_error,"send_decode_gridtracker: Error in Phase 1")
                self.debug_log(self.log_entry,"send_decode_gridtracker: --Exit--")
                return

            # build decode packet for GRIDTRACKER
            try:
                pkt = pywsjtx.DecodePacket.Builder(self.MY_WSJTX_ID, new, 
                        time, snr, deltaTime, deltaFreq, mode,
                        gtmessage, low_confidence, off_air)
            except:
                self.debug_log(self.log_error,"send_decode_gridtracker: Error in Phase 2")
                self.debug_log(self.log_entry,"send_decode_gridtracker: --Exit--")
                return

            # now send the packet to GridTracker
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.gthost,int(self.gtport)))          
                self.debug_log(self.log_debug,"send_decode_gridtracker: Sending GRIDTRACKER decode message...")
                sock.send(pkt)
                self.debug_log(self.log_info,"send_decode_gridtracker: Sent GRIDTRACKER decode message.")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"send_decode_gridtracker: %s Unable to establish connection to GRIDTRACKER" % msg)
        self.debug_log(self.log_entry,"send_decode_gridtracker: --Exit--")

    def log_qso_geoserver(self):
        """ Log new QSO (spot) to GeoServer """
        self.debug_log(self.log_entry,"log_qso_geoserver: --Enter--")
        # Check if GeoServer stream enabled for spot reporting
        if self.gsspotenabled:
            if not self.adif_CALL:
                self.debug_log(self.log_warning,"log_qso_geoserver: CALL is missing")
                self.debug_log(self.log_entry,"log_qso_geoserver: --Exit--")
                return
            if not self.adif_GRIDSQUARE:
                self.debug_log(self.log_warning,"log_qso_geoserver: GRIDSQUARE is missing")
                self.debug_log(self.log_entry,"log_qso_geoserver: --Exit--")
                return

            # build packet
            try:
                data = {
                    'type': 'SPOT.GRID',
                    'params': {'AUTH': str(self.gsauth), 'CALL': str(self.adif_CALL), 'GRID': str(self.adif_GRIDSQUARE), 'COLOR': str(self.adif_QSO_COLOR)}
                }
                json_data = json.dumps(data, sort_keys=False, indent=2)
                self.debug_log(self.log_hidebug,"log_qso_geoserver: data %s" % json_data)
            except:
                self.debug_log(self.log_error,"log_qso_geoserver: Error in Phase 1")
                self.debug_log(self.log_entry,"log_qso_geoserver: --Exit--")
                return

            # now send the packet to GeoServer
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.gshost,int(self.gsport)))         
                self.debug_log(self.log_debug,"log_qso_geoserver: Sending GEOSERVER log...")
                sock.sendall(json_data.encode())
                self.debug_log(self.log_info,"log_qso_geoserver: Sent GEOSERVER log")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"log_qso_geoserver: %s Unable to establish connection to GEOSERVER" % msg)
        self.debug_log(self.log_entry,"log_qso_geoserver: --Exit--")

    def send_message_geoserver(self):
        """ Send Message to GeoServer """
        self.debug_log(self.log_entry,"send_message_geoserver: --Enter--")
        # Check if GeoServer stream enabled for message reporting
        if self.gsmsgenabled:
            if not self.adif_COMMENT:
                self.debug_log(self.log_warning,"send_message_geoserver: COMMENT is missing")
                self.debug_log(self.log_entry,"send_message_geoserver: --Exit--")
                return
            # calculate time
            # Not using adif_TIME_xxx variables because formatting is not
            # appropiate for GeoChron display.
            mytime = datetime.datetime.utcnow()
            dtg = mytime.strftime("%H:%M:%S")

            # trim the beginning from INFO & STATUS messages, and reformat to
            # conform to the limitations of the GeoChron text legend component
            try:
                while True:
                    # check for INFO message
                    message = self.adif_COMMENT
                    search_token = "INFO "
                    start = message.lower().find(search_token.lower())
                    if start == -1:
                        self.debug_log(self.log_debug,"send_message_geoserver: INFO NOT found")
                    else:
                        self.debug_log(self.log_debug,"send_message_geoserver: INFO FOUND")
                        message = message[start:]
                        message = str(dtg) + " " + str(self.adif_CALL) + " " + message
                        break

                    # check for STATUS message
                    message = self.adif_COMMENT
                    search_token = "STATUS "
                    start = message.lower().find(search_token.lower())
                    if start == -1:
                        self.debug_log(self.log_debug,"send_message_geoserver: STATUS NOT found")
                    else:
                        self.debug_log(self.log_debug,"send_message_geoserver: STATUS FOUND")
                        message = message[start:]
                        message = str(dtg) + " " + str(self.adif_CALL) + " " + message
                        break

                    # none of the above so set the default handling
                    message = str(dtg) + " " + message
                    break

                # limit message length
                message = message[:40]
                self.debug_log(self.log_debug,"send_message_geoserver: message %s" % message)
            except:
                self.debug_log(self.log_error,"send_message_geoserver: Error in Phase 1")
                self.debug_log(self.log_entry,"send_message_geoserver: --Exit--")
                return

            # build packet
            try:
                data = {
                    'type': 'MESSAGE.SEND',
                    'params': {'AUTH': str(self.gsauth), 'MESSAGE': message}
                }
                json_data = json.dumps(data, sort_keys=False, indent=2)
                self.debug_log(self.log_hidebug,"send_message_geoserver: data %s" % json_data)
            except:
                self.debug_log(self.log_error,"send_message_geoserver: Error in Phase 2")
                self.debug_log(self.log_entry,"send_message_geoserver: --Exit--")
                return

            # now send the packet to GeoServer
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.connect((self.gshost,int(self.gsport)))         
                self.debug_log(self.log_debug,"send_message_geoserver: Sending GEOSERVER log...")
                sock.sendall(json_data.encode())
                self.debug_log(self.log_info,"send_message_geoserver: Sent GEOSERVER log")
            except KeyboardInterrupt:
                sys.stderr.write("User cancelled.")
                sock.close()
                sys.exit(0)
            except socket.error as msg:
                self.debug_log(self.log_error,"send_message_geoserver: %s Unable to establish connection to GEOSERVER" % msg)
        self.debug_log(self.log_entry,"send_message_geoserver: --Exit--")

    def log_qso_yaac(self):
        """ Log new QSO to YAAC APRS file
        On entry this routine assumes that if LAT/LON data exists in
        self.adif_LAT or self.adif_LON that it is in WGS-84 format.
        """
        self.debug_log(self.log_entry,"log_qso_yaac: --Enter--")
        # Check if YACC stream enabled
        if self.yaacenabled:
            try:
                if not self.adif_LAT:
                    # calculate LAT from gridsquare
                    if not self.adif_GRIDSQUARE:
                        self.debug_log(self.log_warning,"log_qso_yaac: LAT is missing")
                        self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                        return
                    lat,lng = None, None
                    lat,lng = self.to_latlng(self.adif_GRIDSQUARE)
                    if lat==None or lng==None:
                        self.debug_log(self.log_info,"log_qso_yaac: Unable to calculate lat/lon.")
                        self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                        return
                    self.adif_LAT = str(lat)
                    self.adif_LON = str(lng)

                if not self.adif_LON:
                    # calculate LON from gridsquare
                    if not self.adif_GRIDSQUARE:
                        self.debug_log(self.log_warning,"log_qso_yaac: LON is missing")
                        self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                        return
                    lat,lng = None, None
                    lat,lng = self.to_latlng(self.adif_GRIDSQUARE)
                    if lat==None or lng==None:
                        self.debug_log(self.log_info,"log_qso_yaac: Unable to calculate lat/lon.")
                        self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                        return
                    self.adif_LAT = str(lat)
                    self.adif_LON = str(lng)                
            except:
                self.debug_log(self.log_error,"log_qso_yaac: Error in Phase 1")
                self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                return

            try:
                # Convert WGS-84 latitude to APRS format (DDMM.MM)
                lat = float(self.adif_LAT)
                lat_degree = abs(int(lat))
                lat_minute = abs(lat - int(lat)) * 60.0
                lat_min_str = ("%02.4f" % lat_minute).zfill(7)[:5]
                lat_dir = "S"
                if lat > 0.0:
                    lat_dir = "N"
                lat_str = "%02d%s" % (lat_degree, lat_min_str) + lat_dir
                self.adif_LAT = str(lat_str)

                # Convert WGS-84 longitude to APRS format (DDDMM.MM)
                lon = float(self.adif_LON)
                lon_degree = abs(int(lon))
                lon_minute = abs(lon - int(lon)) * 60.0
                lon_min_str = ("%02.4f" % lon_minute).zfill(7)[:5]
                lon_dir = "E"
                if lon < 0.0:
                    lon_dir = "W"
                lon_str = "%03d%s" % (lon_degree, lon_min_str) + lon_dir
                self.adif_LON = str(lon_str)
            except:
                self.debug_log(self.log_error,"log_qso_yaac: Error in Phase 2")
                self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                return

            """
            The following are the APRS symbols set in the default
            config file settings;
                red_code=['/',':'] # Fire
                yel_code=['\','U'] # Sun
                grn_code=['\','W'] # Green Circle
                unk_code=['\','0'] # Grey Circle
                 no_stat=['\','.'] # Grey Circle w/ Question Mark
                 no_info=['\','!'] # Warning Triangle
                  status=['\',')'] # Red and Black Asterisk
            """
            try:
                # parse the APRS symbol settings
                self.debug_log(self.log_debug,"log_qso_yaac: ICON: %s" % self.adif_QSO_ICON) 
                iconindex = self.adif_QSO_ICON.split(",",1)
                symtable = iconindex[0].strip()
                symtable = symtable[2:-1]
                symcode = iconindex[1].strip()
                symcode = symcode[1:-2]
                self.debug_log(self.log_debug,"log_qso_yaac: Table: " + str(symtable))
                self.debug_log(self.log_debug,"log_qso_yaac: Code: " + str(symcode))
            except:
                self.debug_log(self.log_error,"log_qso_yaac: Error in Phase 3")
                self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                return

            # build fields
            try:
                # Calculate UTC DateTime stamp
                mytime = datetime.datetime.utcnow()
                dtg = mytime.strftime("%d/%b/%Y %H:%M:%S")

                src = str("X0" + self.adif_CALL[(len(self.adif_CALL)-2):])
                dest = str("NULL")
                lat = str(self.adif_LAT)
                lng = str(self.adif_LON)
                grid = str(self.adif_GRIDSQUARE)
                msg = str(self.adif_COMMENT)
            except:
                self.debug_log(self.log_error,"log_qso_yaac: Error in Phase 4")
                self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")
                return

            try:
                # build logfile entry
                self.debug_log(self.log_debug,"log_qso_yaac: Updating yaac logfile...")
                dbEntry = dtg + "," + src + ">" + dest + ":=" + lat + symtable + lng + symcode + " " + grid + " " + msg + "\n"
                self.debug_log(self.log_hidebug,"log_qso_yaac: data %s" % dbEntry)

                # append to log file
                fh = ''
                fh = open(self.yaaclogfile,'a')
                fh.write(dbEntry)
                fh.close()
                self.debug_log(self.log_debug,"log_qso_yaac: Updated yaac logfile")
            except:
                # logfile failed to update
                if fh:
                    fh.close()
                self.debug_log(self.log_warning,"log_qso_yaac: Failed to update yaac logfile")
        self.debug_log(self.log_entry,"log_qso_yaac: --Exit--")

    def log_qso_adif(self):
        """ Log new QSO to ADIF database """
        self.debug_log(self.log_entry,"log_qso_adif: --Enter--")
        # Check if ADIF stream enabled
        if self.adifenabled:
            self.send_buffer = ""
            tags = ""

            # build records
            # add or remove adif fields to be passed to ADIF database here
            try:
                record = {}
                record['band'] = str(self.adif_BAND)
                record['call'] = str(self.adif_CALL)
                record['comment'] = str(self.adif_COMMENT)
                record['freq'] = str(self.adif_FREQ)
                record['gridsquare'] = str(self.adif_GRIDSQUARE)
                record['mode'] = str(self.adif_MODE)
                record['my_gridsquare'] = str(self.adif_MY_GRIDSQUARE)
                record['operator'] = str(self.adif_OPERATOR)
                record['qso_date'] = str(self.adif_QSO_DATE)
                record['qso_date_off'] = str(self.adif_QSO_DATE)
                record['rst_rcvd'] = str(self.adif_RST_RCVD)
                record['rst_sent'] = str(self.adif_RST_SENT)
                record['station_callsign'] = str(self.adif_OPERATOR)
                record['submode'] = str(self.adif_SUBMODE)
                record['time_off'] = str(self.adif_TIME_OFF)
                record['time_on'] = str(self.adif_TIME_ON)
                self.debug_log(self.log_hidebug,record)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_adif: Error in Phase 1")
                self.debug_log(self.log_entry,"log_qso_adif: --Exit--")
                return

            # build fields
            try:
                fields = []
                for k,v in iteritems(record):
                    fields.append("<%s:%d>%s" % (k, len(v), v))
                fields.append('<eor>')
                self.debug_log(self.log_hidebug,fields)
                self.debug_log(self.log_hidebug,"\n")
            except:
                self.debug_log(self.log_error,"log_qso_adif: Error in Phase 2")
                self.debug_log(self.log_entry,"log_qso_adif: --Exit--")
                return

            # build tags
            try:
                for i in range(len(fields)):
                    tags = tags + fields[i] + " "
                tags = tags + "\n"
                self.debug_log(self.log_hidebug,tags)
            except:
                self.debug_log(self.log_error,"log_qso_adif: Error in Phase 3")
                self.debug_log(self.log_entry,"log_qso_adif: --Exit--")
                return

            # open ADIF database
            try:
                if os.path.exists(self.adiflogfile):
                    fh = ''
                    fh = open(self.adiflogfile,'a')
                else:
                    fh = ''
                    fh = open(self.adiflogfile,'a')
                    fh.write("JS8Monitor ADIF Export<eoh>\n")
            except:
                self.debug_log(self.log_error,"log_qso_adif: Error in Phase 4")
                self.debug_log(self.log_entry,"log_qso_adif: --Exit--")
                return

            # append tags to ADIF database
            try:
                fh.write(tags)
                fh.close()
                self.debug_log(self.log_debug,"log_qso_adif: Updated ADIF database")
            except:
                # database failed to update
                if fh:
                    fh.close()
                self.debug_log(self.log_warning,"log_qso_adif: Failed to update ADIF database")
            self.debug_log(self.log_entry,"log_qso_adif: --Exit--")

    def queue_cmd(self, command):
        """ Queue command message """
        self.debug_log(self.log_entry,"queue_cmd: --Enter--")
        if not command:
            self.debug_log(self.log_debug,"queue_cmd: Missing COMMAND")
            self.debug_log(self.log_entry,"queue_cmd: --Exit--")
            return
        if not self.adif_RADIO:
            self.debug_log(self.log_debug,"queue_cmd: Missing RADIO")
            self.debug_log(self.log_entry,"queue_cmd: --Exit--")
            return
        if not self.radio_data:
            self.debug_log(self.log_debug,"queue_cmd: Radio Database is empty")
            self.debug_log(self.log_entry,"queue_cmd: --Exit--")
            return

        # get radio port from the radio database
        try:
            radio = self.adif_RADIO
            self.debug_log(self.log_debug,"queue_cmd: RADIO: " + str(radio))
            port = str(self.radio_data.get(radio))
            if port == 'None':
                self.debug_log(self.log_debug,"queue_cmd: PORT not found")
                self.debug_log(self.log_entry,"queue_cmd: --Exit--")
                return
            self.debug_log(self.log_debug,"queue_cmd: PORT: " + str(port))
            addr = "('" + str(radio) + "', " + str(port) + ")"
            self.debug_log(self.log_debug,"queue_cmd: ADDR: " + str(addr))
        except:
            self.debug_log(self.log_warning,"queue_cmd: Unable to retrieve PORT from RADIO Database")
            self.debug_log(self.log_entry,"queue_cmd: --Exit--")
            return

        # queue the command            
        try:
            msg = str(addr) + "|" + str(command)
            cmdQueue.put(msg)
            self.debug_log(self.log_debug,"queue_cmd: COMMAND: %s" %msg)
            self.debug_log(self.log_info,"queue_cmd: Command message queued")           
        except:
            self.debug_log(self.log_error,"queue_cmd: Unable to queue command message")
        self.debug_log(self.log_entry,"queue_cmd: --Exit--")
        return

    def parse_cmd(self):
        """ Parse command message """
        # pylint: disable=too-many-branches
        # pylint: disable=too-many-statements
        # It's a parser after all
        self.debug_log(self.log_entry,"parse_cmd: --Enter--")
        try:
            self.debug_log(self.log_info,"parse_cmd: Getting command from queue")
            cmdJSON = cmdQueue.get()
            self.debug_log(self.log_debug,"parse_cmd: Removing non-ascii garbage")
            cmdJSON = str(re.sub(r'[^\x00-\x7f]',r'',cmdJSON))
            self.debug_log(self.log_hidebug,"parse_cmd: Raw JSON: %s" %cmdJSON)
            self.debug_log(self.log_info,"parse_cmd: Parsing JSON command for JS8Call...")
            cmdIndex = cmdJSON.split("|",1)
            dest = str(cmdIndex[0])
            command_raw = str(cmdIndex[1])
            command = json.loads(cmdIndex[1])
            cmdQueue.task_done()
        except:
            command_raw = {}
            command = {}
        if not command:
            self.debug_log(self.log_error,"parse_cmd: No JSON command to parse")
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return

        self.debug_log(self.log_info,"parse_cmd: Got JSON command for %s" %dest)
        # In this context host (dest) refers to the radio ip address
        try:
            self.get_host(dest)
            typ = command.get('type', '')
            value = command.get('value', '')
            params = command.get('params', {})
        except:
            self.debug_log(self.log_error,"parse_cmd: Unable to parse JSON command.")
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return

        if self.adif_HOST:
            self.debug_log(self.log_hidebug,"parse_cmd: -> host: " + self.adif_HOST)
        if typ:
            self.debug_log(self.log_hidebug,"parse_cmd: -> type: " + typ)
        if value:
            self.debug_log(self.log_hidebug,"parse_cmd: -> value: " + value)
        if params:
            self.debug_log(self.log_hidebug,"parse_cmd: -> params: ")
            self.debug_log(self.log_hidebug,params)
 
        if not typ:
            self.debug_log(self.log_info,"parse_cmd: Missing command TYPE")
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return

        if typ == 'INBOX.GET_MESSAGES':
            self.debug_log(self.log_info,"parse_cmd: ---INBOX.GET_MESSAGES---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Inbox get message request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'INBOX.STORE_MESSAGE':
            self.debug_log(self.log_info,"parse_cmd: ---INBOX.STORE_MESSAGE---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Inbox store message request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'MODE.GET_SPEED':
            self.debug_log(self.log_info,"parse_cmd: ---MODE.GET_SPEED---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get speed request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'MODE.SET_SPEED':
            self.debug_log(self.log_info,"parse_cmd: ---MODE.SET_SPEED---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Set speed request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RIG.GET_FREQ':
            self.debug_log(self.log_info,"parse_cmd: ---RIG.GET_FREQ---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get frequency request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RIG.SET_FREQ':
            self.debug_log(self.log_info,"parse_cmd: ---RIG.SET_FREQ---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Set frequency request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RX.GET_BAND_ACTIVITY':
            self.debug_log(self.log_info,"parse_cmd: ---RX.GET_BAND_ACTIVITY---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get band activity request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RX.GET_CALL_ACTIVITY':
            self.debug_log(self.log_info,"parse_cmd: ---RX.GET_CALL_ACTIVITY---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get call activity request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RX.GET_CALL_SELECTED':
            self.debug_log(self.log_info,"parse_cmd: ---RX.GET_CALL_SELECTED---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get call selected request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'RX.GET_TEXT':
            self.debug_log(self.log_info,"parse_cmd: ---RX.GET_TEXT---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get text request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.GET_CALLSIGN':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.GET_CALLSIGN---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get station callsign request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.GET_GRID':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.GET_GRID---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get station grid request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.SET_GRID':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.SET_GRID---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Set station grid request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.GET_INFO':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.GET_INFO---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get station info request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.SET_INFO':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.SET_INFO---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Set station info request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.GET_STATUS':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.GET_STATUS---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Get station status request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'STATION.SET_STATUS':
            self.debug_log(self.log_info,"parse_cmd: ---STATION.SET_STATUS---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"Set station status request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'TX.SET_TEXT':
            self.debug_log(self.log_info,"parse_cmd: ---TX.SET_TEXT---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"TX set text request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'TX.SEND_MESSAGE':
            self.debug_log(self.log_info,"parse_cmd: ---TX.SEND_MESSAGE---")
            self.send_cmd(command_raw)
            self.debug_log(self.log_smdr,"TX send message request from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return
        if typ == 'TEST.TEST':
            self.debug_log(self.log_info,"parse_cmd: ---TEST.TEST---")            
            self.debug_log(self.log_smdr,"Test message from " + str(self.adif_HOST_IP))
            self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
            return

        """
        If we have reached this point, we have a unknown TYPE.
        Process it using a default handler. If we identify additional
        TYPES that need special handeling, then code them here.
        """
        self.debug_log(self.log_info,"parse_cmd: ---UNKNOWN.TYPE---")
        self.debug_log(self.log_entry,"parse_cmd: --Exit--\n")
        return

    def send_cmd(self, command):
        """ Send command message """
        self.debug_log(self.log_entry,"send_cmd: --Enter--")
        if not command:
            self.debug_log(self.log_debug,"send_cmd: Missing COMMAND")
            self.debug_log(self.log_entry,"send_cmd: --Exit--")
            return
        if not self.adif_HOST_IP:
            self.debug_log(self.log_debug,"send_cmd: Missing RADIO IP")
            self.debug_log(self.log_entry,"send_cmd: --Exit--")
            return
        if not self.adif_HOST_PORT:
            self.debug_log(self.log_debug,"send_cmd: Missing RADIO PORT")
            self.debug_log(self.log_entry,"send_cmd: --Exit--")
            return
        
        self.debug_log(self.log_debug,"send_cmd: RADIO: " + str(self.adif_HOST_IP))
        self.debug_log(self.log_debug,"send_cmd: PORT: " + str(self.adif_HOST_PORT))
        self.debug_log(self.log_debug,"send_cmd: CMD: " + str(command))

        # send the command JSON to the radio
        self.send_buffer = command
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect((self.adif_HOST_IP,int(self.adif_HOST_PORT)))          
            self.debug_log(self.log_debug,"send_cmd: Sending command...")
            sock.send(self.send_buffer.encode('utf-8'))
            self.debug_log(self.log_info,"send_cmd: Sent command")
        except KeyboardInterrupt:
            sys.stderr.write("User cancelled.")
            sock.close()
            sys.exit(0)
        except socket.error as msg:
            self.debug_log(self.log_error,"send_cmd: %s Unable to establish connection to RADIO" % msg)
        self.debug_log(self.log_entry,"send_cmd: --Exit--")
        return

class udp_server:
    """ Class UDP Server """
    config = ""
    js8host = ""
    js8port = ""
    
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config.read('config')
        self.js8host = self.config['JS8Call']['host']
        self.js8port = self.config['JS8Call']['port']
        print("udp_server: Host: " + self.js8host)
        print("udp_server: Port: " + self.js8port)
        msgServer = threading.Thread(name='msgServer',target=self.run)
        msgServer.daemon = True
        msgServer.start()
        print("udp_server: Started > %s \n" % msgServer.is_alive())

    def run(self):
        try:
            addr = ""
            recv_buffer = ""
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.bind((self.js8host,int(self.js8port)))
            while True:
                recv_buffer, addr = sock.recvfrom(65500)
                if sys.version_info.major < 3:
                    msg = str(addr) + "|" + str(recv_buffer)
                else:
                    msg = str(addr) + "|" + str(recv_buffer.decode('utf-8'))
                msgQueue.put(msg)
                addr = ""
                recv_buffer = ""
        except socket.error as msg:
            sys.stderr.write("[ERROR] %s" % msg)
            sys.exit(2)

if __name__ == "__main__":
    msgQueue = {}
    cmdQueue = {}

    # Python version sprecific functions
    if sys.version_info.major == 3:
        msgQueue = queue.Queue()
        cmdQueue = queue.Queue()
    elif sys.version_info.major == 2:
        msgQueue = Queue.Queue()
        cmdQueue = Queue.Queue()
    else:
        raise NotImplementedError
    
    print("JS8Call Monitor v0.20 written by KK7JND")
    print("Starting UDP server...")
    S = udp_server()
    J = JS8CallMonitor()
    while True:
        while not msgQueue.empty():
            J.parse_json()
            J.reset_vals()
            #print("Inner MSG loop")
        while not cmdQueue.empty():
            J.parse_cmd()
            J.reset_vals()
            #print("Inner CMD loop")
        #print("Outer loop")
        time.sleep(5)
    J.sock.close()
