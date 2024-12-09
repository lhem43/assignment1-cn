import socket
import argparse
import json
import time
import errno
import os
import shutil
import mmap
import sys
# import pdb
import traceback
from threading import Thread, Lock
from datetime import datetime
import hashlib
import urllib
import urllib.parse

def decode_magnet(magnet_link : str): #lấy thông tin từ magnet
    if not magnet_link.startswith("magnet:?"):
        raise ValueError("Invalid magnet link format")
    query = magnet_link[8:]
    params = urllib.parse.parse_qs(query)
    info_hash = params.get('xt', [None])[0]
    if info_hash and info_hash.startswith('urn:btih:'):
        info_hash = info_hash[9:]
    file_name = params.get('dn', [None])[0]
    tracker = params.get('tr', [None])[0] #just 1 tracker in this version
    return {
        'info_hash': info_hash,
        'file_name': file_name,
        'tracker': tracker
    }

def generate_magnet_link(info_hash, file_name, tracker_ip, tracker_port): #tạo magnet
    info_hash = f"urn:btih:{info_hash.lower()}"
    magnet_link = f"magnet:?xt={info_hash}"
    if file_name:
        magnet_link += f"&dn={file_name}"
    tracker_url = f"{tracker_ip}:{tracker_port}"
    magnet_link += f"&tr={tracker_url}"
    return magnet_link

def myGenHash(data : str):
    enc_data = data.encode('utf-8')
    hash_object = hashlib.sha256(enc_data)
    return hash_object.hexdigest()
def read_file(filepath: str, offst: int, num_bytes : int = 524288):
    # with open(filepath, mode="rb", encoding="utf-8") as file_obj:
    with open(filepath, mode="rb") as file_obj:
        with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_READ, offset=0) as mmap_obj:
            mmap_obj.seek(offst)
            # print(mmap_obj.tell())
            return mmap_obj.read(num_bytes)
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
class Node:
    def __init__(self) -> None:
        self.parser = argparse.ArgumentParser(
            prog="Peer",
            description="This is a peer",
            epilog="!!!It requires the tracker running!!!"
        )
        self.add_subparse()
        self.my_parse = self.parser.parse_args()
        self.peer_host = self.get_host_default_interface_ip()
        self.username = myGenHash(self.peer_host + str(self.my_parse.peer_port))
        self.priv_lock = Lock()
        self.connect_tracker = socket.socket()
        self.connect_tracker.connect((self.my_parse.tracker_ip, self.my_parse.tracker_port))
    def add_subparse(self):
        self.parser.add_argument('--tracker-ip')
        self.parser.add_argument('--tracker-port', type=int)
        self.parser.add_argument('--peer-port', type=int)
    def thread_server(self):
       s = socket.socket()
       s.bind((self.peer_host, self.my_parse.peer_port))
       s.listen(10)
       while True:
            try:
                conn, addr = s.accept()
                Thread(target=self.peer_transfer, args=(conn, addr)).start()
            except Exception as e:
                conn.close()
                print(e)
                break
    def process_pieceName(self, pieceName:str):
        formated_item = []
        newName = [item[::-1] for item in pieceName[::-1].partition("_")]
        formated_item.append(newName[0])
        formated_item.append(newName[2][5:])
        return formated_item
    def peer_transfer(self, conn : socket.socket, addr):
        print(conn)
        while True:
            message = conn.recv(1024).decode('utf-8')
            if not message:
                break
            if "{" in message:
                message = "{" + message.partition("{")[2]
                data = json.loads(message)
                if "peer-ip" in data and "peer-port" in data:
                    if "I am requesting for filename" in data["message"]:
                        piece_name = data["message"].partition(":")[2]
                        piece_content = b''
                        founded = False
                        try:
                            completed_files = os.listdir(f"peer_file/files_{self.username}")
                            for file in completed_files:
                                if file == self.process_pieceName(piece_name)[0]:
                                    founded = True
                                    piece_index = int(self.process_pieceName(piece_name)[1])
                                    try:
                                        piece_content = read_file(f"peer_file/files_{self.username}/{file}", piece_index * 524288, data["length"])
                                    except Exception as e:
                                        print(e)
                                        message = {
                                            "notification": ""
                                        }
                                        time.sleep(1)
                                        conn.send(json.dumps(message).encode('utf-8'))
                                        return None
                                    break
                        except Exception as e:
                            print(e)
                            message = {
                                "notification": ""
                            }
                            time.sleep(1)
                            conn.send(json.dumps(message).encode('utf-8'))
                            break
                        if founded == False:
                            try:
                                completed_files = os.listdir(f"peer_file/pieces_{self.username}")
                                for file in completed_files:
                                    if file == piece_name:
                                        founded = True
                                        piece_index = int(self.process_pieceName(piece_name)[1])
                                        try:
                                            piece_content = read_file(f"peer_file/pieces_{self.username}/{piece_name}", piece_index * 524288, data["length"])
                                        except Exception as e:
                                            print(e)
                                            message = {
                                            "notification": ""
                                            }
                                            time.sleep(1)
                                            conn.send(json.dumps(message).encode('utf-8'))
                                            return None
                                        break
                            except Exception as e:
                                print(e)
                                message = {
                                    "notification": ""
                                }
                                time.sleep(1)
                                conn.send(json.dumps(message).encode('utf-8'))
                                break
                        if founded == True:
                            time.sleep(1)
                            conn.sendall(piece_content)
                            break
                        else:
                            message = {
                                "notification": ""
                            }
                            time.sleep(1)
                            conn.send(json.dumps(message).encode('utf-8'))
                            break
    def peer_connect(self, ip, port, piece_index, filename, desFileName ,piece_length = 524288):
        s = socket.socket()
        s.connect((ip, port))
        message = {
            "peer-ip": ip,
            "peer-port": port,
            "length": piece_length,
            "message": f"I am requesting for filename:_part{piece_index}_{filename}"
        }
        time.sleep(1)
        s.send(json.dumps(message).encode('utf-8'))
        while True:
            # time.sleep(1)
            raw_data = s.recv(piece_length)
            if not raw_data:
                break
            try:
                if "{" in raw_data.decode('utf-8'):
                    message = "{" + raw_data.decode('utf-8').partition("{")[2]
                    data = json.loads(message)
                    if data:
                        if "notification" in data:
                            print(data["notification"])
                    s.close()
                    break
            except Exception as e:
                pass
            if raw_data:
                with self.priv_lock:
                    try:
                        filesize = os.stat(f"peer_file/pieces_{self.username}/_part{piece_index}_{desFileName}").st_size
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            filesize = 0
                        else:
                            print(e)
                            s.close()
                    if filesize == 0:
                        # write_to_file(f"pieces_{self.username}/_part{piece_index}_{filename}", raw_data, piece_length)
                        with open(f"peer_file/pieces_{self.username}/_part{piece_index}_{desFileName}", mode="wb+") as file_obj:
                            file_obj.truncate(piece_length)
                            with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_WRITE, offset=0) as mmap_obj:
                                mmap_obj.write(raw_data)
                                while(piece_length - mmap_obj.tell() > 0):
                                    info = s.recv(piece_length - mmap_obj.tell())
                                    mmap_obj.write(info)
                                    print(mmap_obj.tell())
                                print("received", mmap_obj.tell())
                        print(f"Successfully download piece {piece_index} from {ip}:{port}")
                    else:
                        print("Overlap now")
                    s.close()
                    # print("I am ready to terminate")
                break
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
    def contact_tracker(self):
        while True:
            checked = False
            message = {
                "peer-ip": self.peer_host,
                "peer-port": self.my_parse.peer_port,
                "peer-id": self.username,
                "message": "I am a new user"
            }
            new_message = json.dumps(message).encode('utf-8')
            time.sleep(1)
            self.connect_tracker.send(new_message)
            while True:
               resp = self.connect_tracker.recv(1024)
               if resp:
                    if resp == b"Invalid ID":
                        print("Your port number is duplicated. Please choose another port!")
                        self.my_parse.peer_port = int(input("Enter your new peer port: "))
                        self.username = myGenHash(self.peer_host + str(self.my_parse.peer_port))
                    else:
                        checked = True
                    break
            if checked == True:
               flush_folder(f"peer_file/files_{self.username}")
               flush_folder(f"peer_file/pieces_{self.username}")
               create_sub_fold(f"peer_file/files_{self.username}")
               break
            # break
    def process_filename(self, raw_filename: str):
        return [item[::-1] for item in raw_filename[::-1].partition(".")]
    def submit_info(self):
        directory = f"peer_file/files_{self.username}"
        filename = input("Enter your filename: ")
        filepath = os.path.join(directory, filename)
        info_hash = myGenHash(filename + self.username + str(datetime.now())) + "." + self.process_filename(filename)[0]
        try:
            filesize = os.stat(filepath).st_size
        except OSError as e:
            if e.errno == errno.ENOENT:
                filesize = 0
            else:
                print(e)
        if filesize > 0:
            message = {
                "peer-ip": self.peer_host,
                "peer-port": self.my_parse.peer_port,
                "peer-id": self.username,
                'info_hash': info_hash,
                'length': filesize,
                'piece_length': 524288,
                "message": "Submit new file"
            }
            new_message = json.dumps(message).encode('utf-8')
            time.sleep(1)
            self.connect_tracker.send(new_message)
            print(generate_magnet_link(info_hash,filename, self.my_parse.tracker_ip, self.my_parse.tracker_port))
        else:
            print("File not found")
    def assemble_file(self, fileName, pieceCount, length):
        with open(f"peer_file/files_{self.username}/{fileName}", "wb+") as file_obj:
            file_obj.truncate(length)
            for i in range(pieceCount):
                try:
                    with open(f"peer_file/pieces_{self.username}/_part{i}_{fileName}", mode="rb") as file_obj_item:
                            file_obj.write(file_obj_item.read())
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        print(f"Pieces {i} not found!")
                        return None
                    else:
                        print(e)
        return True
    def download_file(self, magnet_link, cur_peer):
        create_sub_fold(f"peer_file/pieces_{self.username}")
        decode_result = decode_magnet(magnet_link)
        author_file = self.get_files(decode_result["info_hash"]) #trả về địa chỉ các peer đang chứa file
        if len(author_file) != 0:
            tor_item = author_file[0]
            for i in range(tor_item['piece_count']):
                if i == tor_item['piece_count'] - 1:
                    sizePiece = tor_item["file_size"] - tor_item["piece_length"] * i
                else:
                    sizePiece = tor_item["piece_length"]
                for peer in cur_peer:
                    if peer["peer-ip"] == tor_item["auth_ip"] and peer["peer-port"] == tor_item["auth_port"]:
                        fileName = decode_result["file_name"]
                    else:
                        fileName = decode_result["info_hash"]
                    tcon = Thread(target=self.peer_connect, args=(peer["peer-ip"], peer["peer-port"], i, fileName, decode_result["info_hash"], sizePiece))
                    tcon.start()
            time.sleep(10)
            if self.assemble_file(decode_result["info_hash"], tor_item["piece_count"], tor_item["file_size"]) == None:
                try:
                    os.remove(f"peer_file/files_{self.username}/{decode_result['info_hash']}")
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        pass
                    else:
                        print(e)
        else:
            print("Filename not found")
    def get_list(self):
        message = {
            "peer-ip": self.peer_host,
            "peer-port": self.my_parse.peer_port,
            "peer-id": self.username,
            "message": "Send me a list of current peer"
        }
        new_message = json.dumps(message).encode('utf-8')
        time.sleep(1)
        self.connect_tracker.send(new_message)
        try:
            while True:
                cur_list = self.connect_tracker.recv(1024).decode('utf-8')
                if cur_list:
                    return json.loads(cur_list)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                print(e)
                return None
            else:
                pass
    def get_files(self, info_hash):
        # hàm con hỗ trợ lấy địa chỉ các peer (all peer)
        message = {
            "peer-ip": self.peer_host,
            "peer-port": self.my_parse.peer_port,
            "peer-id": self.username,
            "info_hash": info_hash,
            "message": "Send me a list of peers with file"
        }
        new_message = json.dumps(message).encode('utf-8')
        time.sleep(1)
        self.connect_tracker.send(new_message)
        list_address = self.connect_tracker.recv(1024).decode('utf-8')
        return json.loads(list_address)
    def run(self):
        self.contact_tracker()
        thread_server = Thread(target=self.thread_server, args=())
        thread_server.daemon = True
        thread_server.start()
        print(f"Peer server is running on {self.peer_host}:{self.my_parse.peer_port}")
        while True:
            choice = int(input("Enter your choice:\n1. Get list of peers.\n2. Submit info.\n3. Download file.\nOtherwise. Exit\n"))
            if choice == 1:
                print(self.get_list())
            elif choice == 2:
                self.submit_info()
            elif choice == 3:
                num_magnet = int(input("Enter number of files you want to download: "))
                magnet_link = []
                for i in range(num_magnet):
                    temp_link = input("Enter magnet link " + str(i+ 1) + ": ")
                    magnet_link.append(temp_link)
                cur_peer = self.get_list()
                for i in range(num_magnet):
                    Thread(target=self.download_file, args=(magnet_link[i], cur_peer)).start()
                    time.sleep(2)
            else:
                break
        self.connect_tracker.close()
if __name__ == "__main__":
    Node().run()