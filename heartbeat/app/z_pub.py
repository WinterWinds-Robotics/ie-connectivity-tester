import zenoh, random, time

random.seed()

def read_rmp():
    return random.randint(115, 120)

if __name__ == "__main__":
    session = zenoh.open()
    key = 'applications/squimasq/heartbeat'
    pub = session.declare_publisher(key)
    seq = 0
    while True:
        t = read_rmp()
        buf = f"connectivity-tester-heartbeat-{seq}"
        print(f"Putting Data ('{key}': '{buf}')...")
        pub.put(buf)
        seq += 1
        time.sleep(1)
