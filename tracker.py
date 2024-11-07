import socket
from threading import Thread

class Tracker:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.peers = []
        # self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
        self.sock.bind((self.host, self.port))
    

    # get ip address of the Tracker
    def get_host_default_interface_ip():              
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
       s.connect(('8.8.8.8',1))
       ip = s.getsockname()[0]
    except Exception:
       ip = '127.0.0.1'
    finally:
       s.close()
    return ip