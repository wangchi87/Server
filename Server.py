# -*- coding: utf-8 -*-

import select, sys

from SocketWrapper import *

class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 4096

    sockCollections = []

    messageList = {}

    def __init__(self):
        self.sockCollections = []
        self.messageList = {}
        self.host = socket.gethostname()
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

    def __closeServer(self):
        self.__broadcastServerMsg("SERVER_SHUTDOWN")
        self.serverSock.close()

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

    def __mainLoop(self):

        self.serverSock = socketCreation()
        socketBind(self.serverSock, self.host, self.port)
        self.serverSock.setblocking(False)
        socketListen(self.serverSock)

        self.sockCollections.append(self.serverSock)
        self.sockCollections.append(sys.stdin)

        self.messageList[self.serverSock] = []

        try:
            while 1:
                #print self.sockCollections

                # print 'select'
                readList, writeList, errorList = select.select(self.sockCollections, [], self.sockCollections)

                quitProgram = False

                # print readList


                for sock in readList:

                    if sock == self.serverSock:
                        # new client
                        newClient, newAddr = socketAccept(sock)
                        #self.set_keepalive_osx(newClient)
                        self.sockCollections.append(newClient)
                        print "new client connected ", newAddr
                        self.__broadcastClientMsg(newClient, "new client connected \n")
                        self.messageList[newClient] = []
                    else:
                        if type(sock) == socket._socketobject:
                            # msg received from client
                            try:
                                recvedData = socketRecv(sock, self.RECV_BUFFER)
                            except socket.error as err:
                                print "failed to receive data", err
                                sock.close()
                                self.sockCollections.remove(sock)
                            else:
                                self.messageList[sock].append(recvedData)
                                if recvedData == "CLIENT_SHUTDOWN" or recvedData == '':
                                    print "client disconnected", str(sock.getpeername())
                                    self.__broadcastClientMsg(sock, "client disconnected \n")
                                    sock.close()
                                    self.sockCollections.remove(sock)
                                else:
                                    print 'msg from :', str(sock.getpeername()), recvedData
                                    self.__broadcastClientMsg(sock, recvedData)

                        if type(sock) == file:
                            msg = sys.stdin.readline()
                            self.messageList[self.serverSock] = msg
                            if msg == 'esc\n' or msg == '':
                                quitProgram = True
                            else:
                                self.__broadcastServerMsg(msg)
                            # broadcastMsg(connections, serverSocket, msg)

                for sock in errorList:
                    sock.close()
                    self.sockCollections.remove(sock)

                if quitProgram:
                    self.__closeServer()
                    break

        except Exception as e:
            # choose exception type
            print 'Exception', e
            self.__closeServer()

        except KeyboardInterrupt:
            print 'KeyboardInterrupt'
            self.__closeServer()

        finally:
            print "end of server program"
            #print self.messageList


if __name__ == "__main__":

    server = ServerEnd()