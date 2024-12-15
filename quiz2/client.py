import socket
import struct
from threading import Thread
import time
class Client:
    def __init__(self, name):
        self.name = name
        self.isNameSet = False

    def ListenMessage(self, tcpClient):
        while True:
            data = tcpClient.recv(1024)
            print(f"\n{self.name} received data: {data.decode('utf-8')}")

    def SendMessage(self, tcpClient):
        if not self.isNameSet:
            intro = struct.pack("50s50s", self.name.encode('utf-8'), self.name.encode('utf-8'))
            tcpClient.send(intro)
            self.isNameSet = True

        while True:
            time.sleep(1)
            receiver = input("Enter receiver name: ")
            message = input("Enter message: ")
            packed_data = struct.pack("50s1024s", receiver.encode('utf-8'), message.encode('utf-8'))
            tcpClient.send(packed_data)
            time.sleep(2)

    def start(self):
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        host = local_ip
        port = 2004

        tcpClient = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpClient.connect((host, port))

        listenThread = Thread(target=self.ListenMessage, args=(tcpClient,))
        sendThread = Thread(target=self.SendMessage, args=(tcpClient,))
        listenThread.start()
        sendThread.start()
        listenThread.join()
        sendThread.join()

if __name__ == '__main__':
    name = input("Client Name: ")
    client = Client(name)
    client.start()