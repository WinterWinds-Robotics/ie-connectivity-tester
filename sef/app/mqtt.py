#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os, sys, select
import ssl
from rich import print, logging, print_json, tree
from rich.style import Style
from rich.text import Text
from rich.console import Console
import json
import zlib
import paho.mqtt.client as mqtt
import zenoh
import time
import threading
import traceback
from math import pi, sin, cos
console = Console()
zconf = zenoh.Config()
zsession = zenoh.open(zconf)

parser = argparse.ArgumentParser()

parser.add_argument("-H", "--host", required=False, default="mqtt.gofs.live")
parser.add_argument("-t", "--topic", required=False, default="#")
parser.add_argument("-q", "--qos", required=False, type=int, default=0)
parser.add_argument(
    "-c", "--clientid", required=False, default=os.environ.get("MQTT_CLIENT_ID")
)
parser.add_argument(
    "-u", "--username", required=False, default=os.environ.get("MQTT_USERNAME")
)
parser.add_argument(
    "-d",
    "--disable-clean-session",
    action="store_true",
    help="disable 'clean session' (sub + msgs not cleared when client disconnects)",
)
parser.add_argument(
    "-p", "--password", required=False, default=os.environ.get("MQTT_PASSWORD")
)
parser.add_argument(
    "-P",
    "--port",
    required=False,
    type=int,
    default=None,
    help="Defaults to 8883 for TLS or 1883 for non-TLS",
)
parser.add_argument("-k", "--keepalive", required=False, type=int, default=60)
parser.add_argument("-s", "--use-tls", action="store_true", default=True)
parser.add_argument("--insecure", action="store_true", default=True)
parser.add_argument("-F", "--cacerts", required=False, default=None)
parser.add_argument(
    "--tls-version",
    required=False,
    default=None,
    help="TLS protocol version, can be one of tlsv1.2 tlsv1.1 or tlsv1\n",
)
parser.add_argument("-D", "--debug", action="store_true")
parser.add_argument("-i", "--interactive", action="store_true")

args, unknown = parser.parse_known_args()


mqttlc = mqtt.Client(args.clientid, clean_session=not args.disable_clean_session)


def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))


base_search = "FSPi-013A"
topic_search = "RawCompressed"

last_msg = dict()
last_json = None
topics = dict()


mutex = threading.Lock()


def on_message(mqttc, obj, msg):
    global mqttlc
    global last_msg, last_json
    mqttlc.publish(msg.topic, msg.payload)
    # zsession.put(f"mqtt/raw{msg.topic}", msg.payload)
    if base_search not in msg.topic:
        return
        
    try:
        if topic_search in msg.topic:
            try:
                payload = zlib.decompress(msg.payload)
            except Exception as e:
                print(f"EXCEPTION in decompress: {e}")
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                print(exc_type, fname, exc_tb.tb_lineno)
                payload = f"bad {len(msg.payload)}-byte blob"
        else:
            payload = msg.payload

        mutex.acquire()
        try:
            last_msg[msg.topic] = json.loads(payload)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            if args.debug:
                print(f"EXCEPTION in loads: {e}")
                print(
                    f"topic:{msg.topic} --> payload (type={type(payload)}): {payload}"
                )
                print(payload)
            last_msg[msg.topic] = payload

        # try:
        #     zsession.put(f"mqtt/processed/{msg.topic}", payload)
        # except:
        #     print(f"ERROR putting \"mqtt/processed/{msg.topic}\"")

        mutex.release()
        # print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
        # print(f"{msg.topic} (QOS: {msg.qos}) (Payload length: {len(payload)})")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        print(f"\t{msg.topic}")
        # logging.log.log(level=logging.log.warn(f"exception: {e}"))
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)

    # print(j)


def on_publish(mqttc, obj, mid):
    # if topic_search in msg.topic:
    print("mid: " + str(mid))


def on_subscribe(mqttc, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))


def on_log(mqttc, obj, level, string):
    print(string)


usetls = args.use_tls

if args.cacerts:
    usetls = True

port = args.port
if port is None:
    if usetls:
        port = 8883
    else:
        port = 1883

mqttc = mqtt.Client(args.clientid, clean_session=not args.disable_clean_session)

if usetls:
    if args.tls_version == "tlsv1.2":
        tlsVersion = ssl.PROTOCOL_TLSv1_2
    elif args.tls_version == "tlsv1.1":
        tlsVersion = ssl.PROTOCOL_TLSv1_1
    elif args.tls_version == "tlsv1":
        tlsVersion = ssl.PROTOCOL_TLSv1
    elif args.tls_version is None:
        tlsVersion = None
    else:
        print("Unknown TLS version - ignoring")
        tlsVersion = None

    if not args.insecure:
        cert_required = ssl.CERT_REQUIRED
    else:
        cert_required = ssl.CERT_NONE

    mqttc.tls_set(
        ca_certs=args.cacerts,
        certfile=None,
        keyfile=None,
        cert_reqs=cert_required,
        tls_version=tlsVersion,
    )

    if args.insecure:
        mqttc.tls_insecure_set(True)

if args.username or args.password:
    mqttc.username_pw_set(args.username, args.password)

mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttlc.on_connect = on_connect
mqttlc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

if args.debug:
    mqttc.on_log = on_log

print("Connecting to " + args.host + " port: " + str(port))
mqttc.connect(args.host, port, args.keepalive)
try:
    mqttlc.connect("zenoh", 1883, args.keepalive)
except Exception as e:
    print(f"EXCEPTION : {e}")
    exc_type, exc_obj, exc_tb = sys.exc_info()
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    print(exc_type, fname, exc_tb.tb_lineno)
    
mqttc.subscribe(args.topic, args.qos)


# def mqtt_loop(client):
#     client.loop_forever()
# In [4]: for w in last_msg['FSPi-013A/FSiC/FSiC-003/Meta/iControlMetaData']['Well Meta Data']:
def print_meta(key):
    wells = last_msg[key].get("Well Meta Data")
    if type(wells) is type([]):
        print(f"Meta data for {len(wells)} wells:")
        try:
            for well in wells:
                print("-" * 40 + "  ")
                print(key)
                md = well.get("Meta Data")
                if md:
                    # 'Well Name': '17H',                                                
                    # 'Color': 16860,                                                    
                    # 'FS Valve ID': 'FSV-037',                                          
                    # 'iControl Well #': 'Well 3',
                    for k,v in md.items():
                        if type(v) is not type({}):
                            print(f"{k}: {v}")
                        else:
                            print(f"{k}: {len(v.__str__())} byte blob")
                print("-" * 40 + "\n\n")

        except Exception as e:
            print(f"EXCEPTION : {e}")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)

def interact(t, h):
    print(t,h)
    import IPython
    IPython.embed()

if args.interactive:
    pass
    # keyboard.add_hotkey('shift+i', interact, args=('triggered', 'hotkey'))
         
rc = 0
m = []

def process(dt):
    print(f"Processing after idling for {dt}")
    print(type(last_msg))
    try:
        mutex.acquire()
        for k,v in last_msg.items():
            if "Meta" in k:
                try:
                    print_meta(k)
                except Exception as e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    print(exc_type, fname, exc_tb.tb_lineno)
                    print(e)
            elif topic_search in k:
                console.print_json(json.dumps(v))
            else:
                x = f"{type(last_msg[k])}"
                x = x.removeprefix("<class '")
                x = x.removesuffix("'>")
                # print(f"{k}: {len(last_msg[k].__str__())} byte {x}")
                text1 = Text(f"{k}: ")
                s1 = "bold magenta on black"
                text2 = Text(f"{len(last_msg[k].__str__())} byte ")
                s2 = "italic cyan on black"
                text3 = Text(f"{x}")
                s3 = "bold green on black"
                console.print(text1, style=s1, end='')
                console.print(text2, style=s2, end='')
                console.print(text3, style=s3)
                      

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
        print(traceback.format_exc())
    finally:
        mutex.release()
try:
    mqttc.loop_start()
    time.sleep(2)
    old_time = 0
    while True:
        process(time.time()-old_time)
        old_time = time.time()
        time.sleep(10)
except KeyboardInterrupt:
    rc = 255
    if args.interactive:
        IPython.embed()
finally:
    sys.exit(rc)
