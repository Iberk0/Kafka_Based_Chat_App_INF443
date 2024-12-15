import socket
from threading import Thread, Lock
import struct

connectedNames = []
connectedCons = []
lock = Lock()

class Server2Client(Thread):
    def __init__(self, ip, port, conn):
        Thread.__init__(self)
        self.ip, self.port = ip, port
        self.conn = conn
        self.isNameSet = False
        self.connectionName = ""

    def FindTargetAndSend(self, data):
        try:
            targetName, messageContent = struct.unpack("50s1024s", data)
            targetName = targetName.strip(b'\x00').decode('utf-8')
            messageContent = messageContent.strip(b'\x00').decode('utf-8')

            with lock:
                if targetName not in connectedNames:
                    return f"{targetName} has not connected to server yet! Connected users: {connectedNames[:]}"

                targetIndex = connectedNames.index(targetName)
                selectedConnection = connectedCons[targetIndex]
                sentMessage = f"{messageContent} from {self.connectionName}"
                
                if self.connectionName == targetName:
                    return "Can't send a message to yourself"

                selectedConnection.send(sentMessage.encode('utf-8'))
                return f"Message sent successfully from {self.connectionName} to {targetName}"
        except Exception as e:
            return f"Error: {str(e)}"

    def run(self):
        global connectedNames, connectedCons

        while True:
            try:
                data = self.conn.recv(1074)
                if not data:
                    break

                if not self.isNameSet:
                    # Introduction Protocol
                    try:
                        name1, name2 = struct.unpack("50s50s", data)
                        name1 = name1.strip(b'\x00').decode('utf-8')
                        name2 = name2.strip(b'\x00').decode('utf-8')

                        if name1 != name2:
                            self.conn.send(b"Error: Introduction names do not match")
                            continue

                        self.isNameSet = True
                        self.connectionName = name1

                        with lock:
                            connectedNames.append(self.connectionName)
                            connectedCons.append(self.conn)

                        print(f"{self.connectionName} added to table")
                        self.conn.send(f"{self.connectionName}, this is server. Welcome!".encode('utf-8'))
                    except:
                        self.conn.send(b"Error: Invalid introduction format")
                    continue

                # Handle special command: GET_ONLINE_USERS
                if data == b"GET_ONLINE_USERS":
                    with lock:
                        users = ",".join(connectedNames)
                    self.conn.send(users.encode('utf-8'))
                    continue

                # Handle normal messages
                message = self.FindTargetAndSend(data)
                self.conn.send(message.encode('utf-8'))

            except Exception as e:
                print(f"Error: {e}")
                break

        # Cleanup
        with lock:
            if self.connectionName in connectedNames:
                index = connectedNames.index(self.connectionName)
                connectedNames.pop(index)
                connectedCons.pop(index)

        print(f"{self.connectionName} has been disconnected!")
        self.conn.close()

if __name__ == '__main__':
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    TCP_IP = local_ip
    TCP_PORT = 2004
    BUFFER_SIZE = 1024

    tcpServer = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcpServer.bind((TCP_IP, TCP_PORT))
    tcpServer.listen(10)

    threads = []
    print("Server started... Waiting for connections.")

    try:
        while True:
            conn, (ip, port) = tcpServer.accept()
            s = Server2Client(ip, port, conn)
            s.start()
            threads.append(s)
    except KeyboardInterrupt:
        print("Shutting down server.")
    finally:
        for t in threads:
            t.join()
        tcpServer.close()
