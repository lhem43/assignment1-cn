import socket
import json
import hashlib
import mmap
import errno
import os
from threading import Thread

def write_to_file(filepath: str, data : str, size_of_file : int = 100000):
    with open(filepath, mode="w+", encoding="utf-8") as file_obj:
        file_obj.truncate(size_of_file)
        with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_WRITE, offset=0) as mmap_obj:
            mmap_obj.write(data.encode())
def read_file(filepath: str):
    with open(filepath, mode="r", encoding="utf-8") as file_obj:
        with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_READ, offset=0) as mmap_obj:
            raw_obj = mmap_obj.read()
            return json.loads(raw_obj.partition(b"\x00")[0])
         
def create_sub_fold(folderpath:str):
    try:
        os.makedirs(folderpath)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise

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
            data = receiveData.decode('utf-8') #data đang là định dạng json
            fullmessage = json.loads(data)
            if "message" in fullmessage and "peer-ip" in fullmessage and "peer-port" in fullmessage and "peer-id" in fullmessage:
               if fullmessage["message"] == "I am a new user":
                  if self.add_peer(ip=fullmessage["peer-ip"], port=fullmessage["peer-port"], id=fullmessage["peer-id"]):
                     conn.send(b"Valid ID")
                  else:
                     conn.send(b"Invalid ID")
               elif fullmessage["message"] == "I am leaving":
                  if not self.delete_peer(id=fullmessage["peer-id"]):
                     print("Not found any peers.")
                  conn.close()
                  break
               elif fullmessage["message"] == "Send me a list of current peer":
                  print("Helloworld")
               elif fullmessage["message"] == "Send me a list of files":
                  
               elif fullmessage["message"] == "Submit new file":
                  metadata = {
                     "ip" : self.host,
                     "filename" : fullmessage["filename"],
                     "length" : fullmessage["length"],
                     "piece_length" : 524288,
                     "piece_count" : fullmessage["length"] //524288 if fullmessage["length"] % 524288 == 0 else fullmessage["length"] // 524288 + 1
                  }
                  self.add_file(metadata,fullmessage["peer-id"])
               elif fullmessage["message"] == "Request metainfo":
                                 
         except Exception:
            print(Exception)
            break
         
   def add_peer(self,ip, port, id):
      new_id = hashlib.sha256(id.encode('utf-8')).hexdigest()
      create_sub_fold("tracker")
      new_peer = {
         "peer-id" : new_id,
         "peer-ip" : ip,
         "peer-port" : port
      }
      try:
         list_peer = read_file("tracker/list_peer.txt")
         for peer in list_peer:
            if peer["peer-id"] == new_peer["peer-id"]:
               return False
         list_peer.append(new_peer)
         write_to_file("tracker/list_peer.txt", json.dumps(list_peer))
      except OSError as e:
         if e.errno == errno.ENOENT:
            write_to_file("tracker/list_peer.txt", json.dumps([new_peer]))
      return True
   
   def delete_peer(self, id):
      id_hash = hashlib.sha256(id.encode('utf-8')).hexdigest()
      try:
         list_peer = read_file("tracker/list_peer.txt")
         list_peer = [peer for peer in list_peer if peer["peer-id"] != id_hash]
         write_to_file("tracker/list_peer.txt", json.dumps(list_peer))
         return True
      except OSError as e:
         if e.errno == errno.ENOENT:
            return False
   def add_file(metadata, peer_id):
      id_hash = hashlib.sha256(peer_id.encode('utf-8')).hexdigest()