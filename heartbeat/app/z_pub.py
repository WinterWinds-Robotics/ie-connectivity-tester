import zenoh, random, time
import sys, os
import paho.mqtt.client as mqtt

mqttlc = mqtt.Client("heartbeat")

random.seed()

def read_rmp():
    return random.randint(115, 120)

def on_connect(mqttc, obj, flags, rc):
    print("rc: " + str(rc))

def on_publish(mqttc, obj, mid):
    # if topic_search in msg.topic:
    print("mid: " + str(mid))

mqttlc.on_connect = on_connect
mqttlc.on_publish = on_publish
if __name__ == "__main__":

    try:
        mqttlc.connect("zenoh", 1883)
    except Exception as e:
        print(f"EXCEPTION : {e}")
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        print(exc_type, fname, exc_tb.tb_lineno)
    session = zenoh.open()
    key = 'applications/squimasq/heartbeat'
    mkey = 'applications/squimasq/mqtt-heartbeat'
    pub = session.declare_publisher(key)
    seq = 0
    while True:
        t = read_rmp()
        buf = f"connectivity-tester-heartbeat-{seq}"
        print(f"Putting Data ('{key}': '{buf}')...")
        pub.put(buf)
        mqttlc.publish(mkey, buf)
        seq += 1
        time.sleep(1)
