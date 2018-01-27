
import select, sys

from SocketWrapper import *

class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 1

    sockCollections = []

    def __init__(self):
        self.host = socket.gethostname()

        self.__mainLoop()

    def assignHostAddr(self, host):
        self.host = host

    def assignPort(self, port):
        self.port = port

    def __broadcastClientMsg(self, msgSock, msg):

        # send msg to all clients except for msgSock and serverSock
        for sock in self.sockCollections:
            try:
                if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                    sockAddr = sock.getpeername()[0]
                    sockPort = str(sock.getpeername()[1])
                    socketSend(sock, sockAddr + ", "+ sockPort + ": "+ msg)
            except:
                sock.close()
                self.sockCollections.remove(sock)
                #print "client socket", str(sock.getpeername()), "is closed"

    def __broadcastServerMsg(self, msg):

        for sock in self.sockCollections:
            try:
                if sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, 'server msg:' + msg)
            except:
                sock.close()
                self.sockCollections.remove(sock)


    def __mainLoop(self):

        self.serverSock = socketCreation()
        socketBind(self.serverSock, self.host, self.port)
        socketListen(self.serverSock)

        self.sockCollections.append(self.serverSock)
        self.sockCollections.append(sys.stdin)

        try:
            while 1:
                readList, writeList, errorList = select.select(self.sockCollections, [], [])

                quitProgram = False

                for sock in readList:

                    if sock == self.serverSock:
                        # new client
                        newClient, newAddr = socketAccept(sock)
                        self.sockCollections.append(newClient)
                        print "new client connected ", newAddr
                        self.__broadcastClientMsg(newClient, ("new client connected " + newAddr[0] + " " + str(newAddr[1])))

                    else:
                        if type(sock) == socket._socketobject:
                            # msg received from client
                            recvedData = socketRecv(sock, self.RECV_BUFFER)
                            if recvedData == "CLIENT_SHUTDOWN":
                                self.__broadcastClientMsg(sock, (
                                        "client disconnected " + newAddr[0] + " " + str(newAddr[1])))
                                sock.close()
                                self.sockCollections.remove(sock)
                            else:
                                print 'msg from :', str(sock.getpeername()), recvedData
                                self.__broadcastClientMsg(sock, recvedData)

                        if type(sock) == file:
                            msg = sys.stdin.readline()
                            if msg == 'esc\n':
                                self.__broadcastServerMsg("SERVER_SHUTDOWN")
                                quitProgram = True
                            else:
                                self.__broadcastServerMsg(msg)
                            # broadcastMsg(connections, serverSocket, msg)

                if quitProgram:
                    self.serverSock.close()
                    break

        except Exception as e:
            # choose exception type
            print 'Exception', e
            self.serverSock.close()

        except KeyboardInterrupt:
            print 'KeyboardInterrupt'
            self.serverSock.close()

        finally:
            print "end of server program"



if __name__ == "__main__":

    server = ServerEnd()