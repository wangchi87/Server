# -*- coding: utf-8 -*-

import select
import sys
import threading
import json

from ClientInfo import *
from SocketWrapper import *


class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 4096

    sockCollections = []

    messageList = {}

    # we apply a dict to manage client sock
    # detecting the status of connected sock
    clientManagement = {}
    clientManagementLock = None
    # heart beat loop status and thread
    hbLoop = True
    hbThread = None

    def __init__(self):
        self.sockCollections = []
        self.messageList = {}
        self.host = '127.0.0.1'  # socket.gethostname()

        self.clientManagementLock = threading.Lock()
        self.hbThread = threading.Thread(target=self.__detectClientStatus)
        self.hbThread.setDaemon(True)
        self.hbThread.start()

        self.__mainLoop()

    def assignHostAddr(self, host):
        self.host = host

    def assignPort(self, port):
        self.port = port

    def __broadcastClientMsg(self, msgSock, msg):

        sockAddr = msgSock.getpeername()[0]
        sockPort = str(msgSock.getpeername()[1])

        # send msg to all clients except for msgSock and serverSock
        for sock in self.sockCollections:
            try:
                if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, sockAddr + ", "+ sockPort + ": "+ msg)
            except:
                sock.close()
                self.sockCollections.remove(sock)
                #print "client socket", str(sock.getpeername()), "is closed"

    def __broadcastServerMsg(self, msg):

        for sock in self.sockCollections:
            try:
                if sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, 'server msg: ' + msg)
            except:
                sock.close()
                self.sockCollections.remove(sock)

    def __initSocket(self):
        self.serverSock = socketCreation()
        socketBind(self.serverSock, self.host, self.port)
        self.serverSock.setblocking(False)
        socketListen(self.serverSock)

        self.sockCollections.append(self.serverSock)
        self.sockCollections.append(sys.stdin)

    def __closeServer(self):
        print "close server !!"
        self.hbLoop = False
        self.__broadcastServerMsg("SERVER_SHUTDOWN")
        self.serverSock.close()

    def __closeDeadClient(self, sock):
        print "client disconnected", str(sock.getpeername())
        #self.clientManagementLock.acquire()
        sock.close()
        self.clientManagement.__delitem__(sock)
        self.sockCollections.remove(sock)
        #self.clientManagementLock.release()

    def __detectClientStatus(self):
        print "start detecting client status"
        while self.hbLoop:
            #print "detect client status", self.clientManagement, self.hbLoop
            time.sleep(2)
            for sock, client in self.clientManagement.items():
                if client.isClientOffline():
                    print sock, "is OFFLINE"
                    self.__closeDeadClient(sock)
        print 'end of client status detection'


    def __processRecvedData(self, sock, recvedData):
        if (not recvedData) or recvedData == "CLIENT_SHUTDOWN":
            self.__broadcastClientMsg(sock, "client disconnected \n")
            self.__closeDeadClient(sock)
        elif recvedData == "-^-^-pyHB-^-^-":
            self.clientManagement[sock].updateOnlineStatus()
        else:
            self.messageList[sock].append(recvedData)
            print 'msg from :', str(sock.getpeername()), recvedData, json.loads(recvedData)
            self.__broadcastClientMsg(sock, recvedData)

    def __acceptNewClient(self, sock):
        self.clientManagement[sock] = ClientInfo(sock)
        self.sockCollections.append(sock)
        print "new client connected ", sock.getpeername()
        self.__broadcastClientMsg(sock, "new client connected \n")
        self.messageList[sock] = []

    def __mainLoop(self):

        self.__initSocket()
        self.messageList[self.serverSock] = []

        quitProgram = False

        try:
            while not quitProgram:
                #print 'selecting', self.sockCollections
                readList, writeList, errorList = select.select(self.sockCollections, [], self.sockCollections)


                for sock in readList:

                    if sock == self.serverSock:
                        # new client
                        newClient, newAddr = socketAccept(sock)
                        #self.set_keepalive_osx(newClient)
                        self.__acceptNewClient(newClient)
                    else:
                        if type(sock) == socket._socketobject:
                            # msg received from client
                            try:
                                recvedData = socketRecv(sock, self.RECV_BUFFER)
                            except socket.error as err:
                                print "failed to receive data", err
                                self.__closeDeadClient(sock)
                            else:
                                self.__processRecvedData(sock, recvedData)

                        if type(sock) == file:
                            msg = sys.stdin.readline()
                            self.messageList[self.serverSock] = msg
                            if msg == 'esc\n' or msg == '':
                                quitProgram = True
                            else:
                                self.__broadcastServerMsg(msg)

                for sock in errorList:
                    self.__closeDeadClient(sock)

                if quitProgram:
                    self.__closeServer()
                    break

        except select.error as e:
            print 'Select error', e

        except Exception as e:
            # choose exception type
            print 'Find Exception', e
            self.__closeServer()

        except KeyboardInterrupt:
            print 'Find KeyboardInterrupt'
            self.__closeServer()

        finally:
            print "end of server program"
            #print self.messageList

    def set_keepalive_linux(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
        """Set TCP keepalive on an open socket.

        It activates after 1 second (after_idle_sec) of idleness,
        then sends a keepalive ping once every 3 seconds (interval_sec),
        and closes the connection after 5 failed ping (max_fails), or 15 seconds
        """
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, after_idle_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, interval_sec)
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, max_fails)

    def set_keepalive_osx(sock, after_idle_sec=1, interval_sec=3, max_fails=5):
        """Set TCP keepalive on an open socket.

        sends a keepalive ping once every 3 seconds (interval_sec)
        """
        # scraped from /usr/include, not exported by python's socket module
        TCP_KEEPALIVE = 0x10
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
        sock.setsockopt(socket.IPPROTO_TCP, TCP_KEEPALIVE, interval_sec)

if __name__ == "__main__":

    server = ServerEnd()