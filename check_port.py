import socket
import sys
import time

def check_port(host, port, timeout=5):
    start_time = time.time()
    while time.time() - start_time < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex((host, port)) == 0:
                print(f"Success: {host}:{port} is open")
                return True
        time.sleep(1)
    print(f"Failure: {host}:{port} is closed")
    return False

if __name__ == "__main__":
    if not check_port("127.0.0.1", 4000, timeout=30):
        sys.exit(1)
