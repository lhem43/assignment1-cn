import socket
import argparse
import json
import time
import errno
import os
import shutil
import mmap
from threading import Thread, Lock
from datetime import datetime
import hashlib

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
# def read_file(filepath: str, offst: int, num_bytes : int = 524288):
#     # with open(filepath, mode="rb", encoding="utf-8") as file_obj:
#     with open(filepath, mode="rb") as file_obj:
#         file_obj.seek(offst)
#         # print(file_obj.tell())
#         return file_obj.read(num_bytes)
# def write_to_file(filepath: str, data, size_of_file : int = 100000):
#     # with open(filepath, mode="wb+", encoding="utf-8") as file_obj:
#     with open(filepath, mode="wb+") as file_obj:
#         file_obj.truncate(size_of_file)
#         with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_WRITE, offset=0) as mmap_obj:
#             mmap_obj.write(data)
# def write_to_file(filepath: str, data, size_of_file : int = 100000):
#     # with open(filepath, mode="wb+", encoding="utf-8") as file_obj:
#     with open(filepath, mode="wb+") as file_obj:
#         file_obj.truncate(size_of_file)
#         file_obj.write(data)
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
        self.username = input("Enter your peer id: ")
        self.priv_lock = Lock()
        flush_folder(f"files_{self.username}")
        flush_folder(f"pieces_{self.username}")
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
                            completed_files = os.listdir(f"files_{self.username}")
                            for file in completed_files:
                                if file == self.process_pieceName(piece_name)[0]:
                                    founded = True
                                    piece_index = int(self.process_pieceName(piece_name)[1])
                                    try:
                                        piece_content = read_file(f"files_{self.username}/{file}", piece_index * 524288, data["length"])
                                    except Exception as e:
                                        print(e)
                                        message = {
                                            "notification": "This peer does not have the piece"
                                        }
                                        time.sleep(1)
                                        conn.send(json.dumps(message).encode('utf-8'))
                                        return None
                                    break
                        except Exception as e:
                            print(e)
                            message = {
                                "notification": "This peer does not have the piece"
                            }
                            time.sleep(1)
                            conn.send(json.dumps(message).encode('utf-8'))
                            break
                        if founded == False:
                            try:
                                completed_files = os.listdir(f"pieces_{self.username}")
                                for file in completed_files:
                                    if file == piece_name:
                                        founded = True
                                        piece_index = int(self.process_pieceName(piece_name)[1])
                                        try:
                                            piece_content = read_file(f"pieces_{self.username}/{piece_name}", piece_index * 524288, data["length"])
                                        except Exception as e:
                                            print(e)
                                            message = {
                                            "notification": "This peer does not have the piece"
                                            }
                                            time.sleep(1)
                                            conn.send(json.dumps(message).encode('utf-8'))
                                            return None
                                        break
                            except Exception as e:
                                print(e)
                                message = {
                                    "notification": "This peer does not have the piece"
                                }
                                time.sleep(1)
                                conn.send(json.dumps(message).encode('utf-8'))
                                break
                        if founded == True:
                            # message = {
                            #     "notification": "Founded pieces!",
                            #     "content": piece_content.decode('utf-8')
                            # }
                            time.sleep(1)
                            # conn.send(json.dumps(message).encode('utf-8'))
                            conn.sendall(piece_content)
                            # conn.send(piece_content)
                            break
                        else:
                            message = {
                                "notification": "This peer does not have the piece"
                            }
                            time.sleep(1)
                            conn.send(json.dumps(message).encode('utf-8'))
                            break
    def peer_connect(self, ip, port, piece_index, filename, lengthFile ,piece_length = 524288):
        s = socket.socket()
        s.connect((ip, port))
        message = {
            "peer-ip": ip,
            "peer-port": port,
            "length": piece_length,
            "message": f"I am requesting for filename:_part{piece_index}_{filename}"
        }
        time.sleep(1)
        # print(piece_length)
        s.send(json.dumps(message).encode('utf-8'))
        # with self.priv_lock:
        #     try:
        #         filesize = os.stat(f"pieces_{self.username}/_part{piece_index}_{filename}").st_size
        #     except OSError as e:
        #         if e.errno == errno.ENOENT:
        #             filesize = 0
        #         else:
        #             print(e)
        #     if filesize == 0:
        #                 # write_to_file(f"pieces_{self.username}/_part{piece_index}_{filename}", raw_data, piece_length)
        #         with open(f"pieces_{self.username}/_part{piece_index}_{filename}", mode="wb+") as file_obj:
        #             file_obj.truncate(piece_length)
        #             print(file_obj.tell())
        #             while(piece_length - file_obj.tell() > 0):
        #                 info = s.recv(piece_length - file_obj.tell())
        #                 # if b"\x00"*5 not in info:
        #                 file_obj.write(info)
        #                 print(file_obj.tell())
        #             print('received ',file_obj.tell())
        #         print(f"Successfully download piece {piece_index} from {ip}:{port}")
        #     else:
        #         print("Overlap now")
        #         s.close()
        while True:
            # time.sleep(1)
            raw_data = s.recv(piece_length)
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
                        filesize = os.stat(f"pieces_{self.username}/_part{piece_index}_{filename}").st_size
                    except OSError as e:
                        if e.errno == errno.ENOENT:
                            filesize = 0
                        else:
                            print(e)
                            s.close()
                    if filesize == 0:
                        # write_to_file(f"pieces_{self.username}/_part{piece_index}_{filename}", raw_data, piece_length)
                        with open(f"pieces_{self.username}/_part{piece_index}_{filename}", mode="wb+") as file_obj:
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
                        print("Your peer ID has been duplicated. Try again!")
                        self.username = input("Enter your peer id: ")
                    else:
                        checked = True
                    break
            if checked == True:
                break
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
                    # print(cur_list)
                    return json.loads(cur_list)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                print(e)
                return None
            else:
                pass
    def process_filename(self, raw_filename: str):
        return [item[::-1] for item in raw_filename[::-1].partition(".")]
    def submit_info(self):
        create_sub_fold(f"files_{self.username}")
        filename = input("Enter your filename: ")
        try:
            filesize = os.stat(filename).st_size
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
                'filename': myGenHash(self.process_filename(filename)[2] + self.username + str(datetime.now())) + "." + self.process_filename(filename)[0],
                'length': filesize,
                'piece_length': 524288,
                "message": "Submit new file"
            }
            new_message = json.dumps(message).encode('utf-8')
            time.sleep(1)
            self.connect_tracker.send(new_message)
            shutil.copy(filename, f"files_{self.username}/{message['filename']}")
            # shutil.move(filename, f"files_{self.username}/{message['filename']}.jpg")
        else:
            print("File not found")
    def get_metainfo(self, filename):
        message = {
            "peer-ip": self.peer_host,
            "peer-port": self.my_parse.peer_port,
            "peer-id": self.username,
            "filename": filename,
            "message": "Request metainfo"
        }
        new_message = json.dumps(message).encode('utf-8')
        time.sleep(1)
        self.connect_tracker.send(new_message)
        try:
            while True:
                cur_list = self.connect_tracker.recv(1024).decode('utf-8')
                if cur_list:
                    # print(cur_list)
                    return json.loads(cur_list)
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                print(e)
                return None
            else:
                pass
    # def assemble_file(self, fileName, pieceCount, length):
    #     # with open(f"files_{self.username}/{fileName}", "wb+", encoding="utf-8") as file_obj:
    #     with open(f"files_{self.username}/{fileName}", "wb+") as file_obj:
    #         file_obj.truncate(length)
    #         with mmap.mmap(file_obj.fileno(), length=0, access=mmap.ACCESS_WRITE, offset=0) as mmap_obj:
    #             for i in range(pieceCount):
    #                 # with self.priv_lock:
    #                 #     if i == pieceCount - 1:
    #                 #         sizePiece = length - 524288 * i
    #                 #     else:
    #                 #         sizePiece = 524288
    #                     try:
    #                         with open(f"pieces_{self.username}/_part{i}_{fileName}", mode="rb") as file_obj_item:
    #                         # with open(f"pieces_{self.username}/_part{i}_{fileName}", mode="rb", encoding="utf-8") as file_obj_item:
    #                             with mmap.mmap(file_obj_item.fileno(), length=0, access=mmap.ACCESS_READ, offset=0) as mmap_obj_item:
    #                                 mmap_obj.write(mmap_obj_item.read())
    #                     except OSError as e:
    #                         if e.errno == errno.ENOENT:
    #                             print(f"Pieces {i} not found!")
    #                             return None
    #                         else:
    #                             print(e)
    #     return True
    def assemble_file(self, fileName, pieceCount, length):
        # with open(f"files_{self.username}/{fileName}", "wb+", encoding="utf-8") as file_obj:
        with open(f"files_{self.username}/{fileName}", "wb+") as file_obj:
            file_obj.truncate(length)
            for i in range(pieceCount):
                    # with self.priv_lock:
                    #     if i == pieceCount - 1:
                    #         sizePiece = length - 524288 * i
                    #     else:
                    #         sizePiece = 524288
                try:
                    with open(f"pieces_{self.username}/_part{i}_{fileName}", mode="rb") as file_obj_item:
                            file_obj.write(file_obj_item.read())
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        print(f"Pieces {i} not found!")
                        return None
                    else:
                        print(e)
        return True
    def download_file(self):
        create_sub_fold(f"files_{self.username}")
        create_sub_fold(f"pieces_{self.username}")
        filename = input("Enter the file name that you want to download: ")
        list_file = self.get_files()
        checker = False
        metainfo_filename = ''
        for file in list_file:
            if file["filename"] == filename:
                checker = True
                metainfo_filename = file["id"]
                break
        if checker == True:
            list_peer = self.get_list()
            tor_item = self.get_metainfo(metainfo_filename)
            # print(list_peer)
            # print(tor_item)
            for i in range(tor_item['piece_count']):
                if i == tor_item['piece_count'] - 1:
                   sizePiece = tor_item["length"] - 524288 * i
                else:
                   sizePiece = 524288
                for peer in list_peer:
                   tcon = Thread(target=self.peer_connect, args=(peer["peer-ip"], peer["peer-port"], i, filename, tor_item["length"], sizePiece))
                #    tcon.daemon = True
                   tcon.start()
            time.sleep(10)
            if self.assemble_file(filename, tor_item["piece_count"], tor_item["length"]) == None:
                try:
                    os.remove(f"files_{self.username}/{filename}")
                except OSError as e:
                    if e.errno == errno.ENOENT:
                        pass
                    else:
                        print(e)
        else:
            print("Filename not found")
    def get_files(self):
        message = {
            "peer-ip": self.peer_host,
            "peer-port": self.my_parse.peer_port,
            "peer-id": self.username,
            "message": "Send me a list of files"
        }
        new_message = json.dumps(message).encode('utf-8')
        time.sleep(1)
        self.connect_tracker.send(new_message)
        try:
            while True:
                cur_file = self.connect_tracker.recv(1024).decode('utf-8')
                if cur_file:
                    if "{" in cur_file:
                        return json.loads(cur_file)
                    else:
                        return cur_file
        except socket.error as e:
            if e.errno == errno.ECONNRESET:
                print(e)
                return None
            else:
                pass
    def run(self):
        self.contact_tracker()
        thread_server = Thread(target=self.thread_server, args=())
        thread_server.daemon = True
        thread_server.start()
        print(f"Peer server is running on {self.peer_host}:{self.my_parse.peer_port}")
        while True:
            choice = int(input("Enter your choice:\n1. Get list of files.\n2. Submit info.\n3. Download file.\nOtherwise. Exit\n"))
            if choice == 1:
                # self.get_list()
                print(self.get_files())
            elif choice == 2:
                self.submit_info()
            elif choice == 3:
                self.download_file()
            else:
                break
        self.connect_tracker.close()
if __name__ == "__main__":
    Node().run()