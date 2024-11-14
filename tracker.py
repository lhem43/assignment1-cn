import socket
from threading import Thread

class Tracker:
   def __init__(self, port=8000):
      self.host = self.get_host_default_interface_ip()
      self.port = port
      self.sock = socket.socket()
      self.sock.bind((self.host, self.port))
      self.sock.listen(10)
   
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
   def run(self):
      print("Listening on: {}:{}".format(self.host, self.port))
      while True:
         try:
            conn, addr = self.sock.accept()
            nconn = Thread(target=self.new_connection, args=(conn,addr))
            nconn.start()
         except Exception:
            print(Exception)
            break
            
            
   def new_connection(self, conn, addr):
      while True:
         try:
            receiveData = conn.recv(1024)
            data = receiveData.decode("utf-8")
         except Exception:
            print(Exception)
            break