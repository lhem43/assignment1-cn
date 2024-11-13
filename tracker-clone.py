import socket
import json
import mmap
import errno
import shutil
import os
import time
from threading import Thread
import hashlib
def addr_to_string(raw_addr : tuple):
   return ''.join([str(item) for item in raw_addr])
def myGenHash(data : str):
    enc_data = data.encode('utf-8')
    hash_object = hashlib.sha256(enc_data)
    return hash_object.hexdigest()
def create_sub_fold(folderpath:str):
    try:
        os.makedirs(folderpath)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
def flush_folder(folderpath : str):
    try:
        shutil.rmtree(folderpath)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
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
class Tracker:
   def __init__(self, port = 22236):
      self.host = self.get_host_default_interface_ip()
      self.port = port
      self.sock = socket.socket() 
      self.sock.bind((self.host, self.port))
      flush_folder("tracker")
      self.sock.listen(10)
    # get ip address of the Tracker
   def get_host_default_interface_ip(self):              
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
      print(f"Server is running on {self.host}:{self.port}")
      while True:
         try:
            conn, addr = self.sock.accept()
            Thread(target= self.new_connection, args=(addr, conn)).start()
         except Exception as e:
            print(e)
            break
      self.sock.close()
   def add_peer(self, peer, addr):
      create_sub_fold("tracker")
      peer_format = peer.copy()
      peer_format.pop("message")
      peer_format["key"] = myGenHash(addr_to_string(addr))
      try:
         list_peer = read_file("tracker/list_peer.txt")
         list_peer.append(peer_format)
         new_list_peer = json.dumps(list_peer)
         write_to_file("tracker/list_peer.txt", new_list_peer)
      except OSError as e:
         if e.errno == errno.ENOENT:
            new_list_peer = json.dumps([peer_format])
            print(new_list_peer.encode())
            write_to_file("tracker/list_peer.txt", new_list_peer)
   def ensure_unique_id(self, peer_name : str):
      try:
         list_peer = read_file("tracker/list_peer.txt")
         for peer in list_peer:
            if peer["peer-id"] == peer_name:
               return False
      except OSError as e:
         if e.errno == errno.ENOENT:
            pass
         else:
            print(e)
            return False
      return True
   def add_file(self, metadata, peer_id):
      try:
         list_meta = read_file("tracker/magnet.txt")
         list_meta.append({
            "id": f"{peer_id}_{metadata['filename']}.torrent",
            "filename": metadata["filename"]
         })
         new_list_meta = json.dumps(list_meta)
         write_to_file("tracker/magnet.txt", new_list_meta)
      except OSError as e:
         if e.errno == errno.ENOENT:
            new_list_meta = json.dumps([{
            "id": f"{peer_id}_{metadata['filename']}.torrent",
            "filename": metadata["filename"]
            }])
            write_to_file("tracker/magnet.txt", new_list_meta)
      create_sub_fold("tracker/torrent")
      torrent_content = json.dumps(metadata)
      write_to_file(f"tracker/torrent/{peer_id}_{metadata['filename']}.torrent", torrent_content)
   def delete_peer(self, addr):
      try:
         current_peer = read_file("tracker/list_peer.txt")
         for i in range(len(current_peer)):
            if current_peer[i]["key"] == myGenHash(addr_to_string(addr)):
               current_peer.pop(i)
               print(f"{addr} is leaving")
               break
         new_current_peer = json.dumps(current_peer)
         write_to_file("tracker/list_peer.txt", new_current_peer)
      except OSError as e:
         print(e)
   def print_list_peer(self):
      print(read_file("tracker/list_peer.txt"))
   def new_connection(self, addr, conn : socket.socket):
      print(conn)
      while True:
         try:
            message = conn.recv(1024).decode('utf-8')
            if not message:
               self.delete_peer(addr)
               self.print_list_peer()
               conn.close()
               break
            print(message)
            if "{" in message:
               message = "{" + message.partition("{")[2]
               data = json.loads(message)
               if "peer-id" in data and "peer-ip" in data and "peer-port" in data:
                  if "message" in data:
                     if data["message"] == "I am a new user":
                        if self.ensure_unique_id(data["peer-id"]) == True:
                           self.add_peer(data, addr)
                           self.print_list_peer()
                           conn.send(b"Valid ID")
                        else:
                           conn.send(b"Invalid ID")
                     elif data["message"] == "Send me a list of current peer":
                        cur_list = read_file("tracker/list_peer.txt")
                        peer_raw_mess = []
                        for peer in cur_list:
                           if peer["key"] != myGenHash(addr_to_string(addr)):
                              peer_raw_mess.append({
                                 'peer-ip': peer["peer-ip"],
                                 "peer-port":peer["peer-port"],
                                 "peer-id": peer["peer-id"]
                              })
                        peer_mess = json.dumps(peer_raw_mess).encode('utf-8')
                        time.sleep(1)
                        conn.send(peer_mess)
                     elif data["message"] == "Send me a list of files":
                        try:
                           cur_list = read_file("tracker/magnet.txt")
                           file_mess = json.dumps(cur_list).encode('utf-8')
                           time.sleep(1)
                           conn.send(file_mess)
                        except OSError as e:
                           if e.errno == errno.ENOENT:
                              files_raw_mess = "Not found files".encode('utf-8')
                              conn.send(files_raw_mess)
                           else:
                              print(e)
                     elif data["message"] == "Submit new file":
                        meata_info = {
                           "ip": self.host,
                           "filename": data["filename"],
                           "length": data["length"],
                           'piece_length': 524288,
                           'piece_count': data["length"] // 524288 if data["length"] % 524288 == 0 else data["length"] // 524288 + 1
                        }
                        self.add_file(meata_info, data["peer-id"])
                     elif data["message"] == "Request metainfo":
                        req_metainfo = read_file(f"tracker/torrent/{data['filename']}")
                        time.sleep(1)
                        conn.send(json.dumps(req_metainfo).encode('utf-8'))
         except Exception as e:
            print(e)
            conn.close()
            break
if __name__ == "__main__":
   Tracker().run()