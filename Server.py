# -*- coding: utf-8 -*-

import json
import select
import sys
import threading

from ClientInfo import *
from SocketWrapper import *


class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 4096

    sockCollections = []

    __usrLoginData = {}
    __usrLoginStatus = {}
    __usrnameIPAddrAssociation = {}

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

        self.__loadUsrData()

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

        # send msg to all clients except for msgSock and serverSock
        for sock in self.sockCollections:
            try:
                if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, self.__getUsrName(sock) + ": " + msg)
            except socket.error:
                self.__closeDeadClient(sock)

    def __broadcastServerMsg(self, msg):

        for sock in self.sockCollections:
            try:
                if sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, 'server msg: ' + msg)
            except socket.error:
                self.__closeDeadClient(sock)

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
        self.__usrLoginStatus[self.__getUsrName(sock)] = False
        self.clientManagement.__delitem__(sock)
        self.sockCollections.remove(sock)
        sock.close()
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
            self.__broadcastClientMsg(sock, "client disconnected\n")
            self.__closeDeadClient(sock)
        elif recvedData == "-^-^-pyHB-^-^-":
            self.clientManagement[sock].updateOnlineStatus()
        else:

            # parse recvedData
            sysMsg = self.__parseRecvdData(sock, recvedData)
            print sysMsg

            # self.messageList[sock].append(recvedData)
            print 'msg from :', self.__getUsrName(sock), sysMsg
            self.__broadcastClientMsg(sock, sysMsg)

    def __parseRecvdData(self, sock, msg):

        try:
            data = json.loads(msg)
        except Exception as e:
            print 'excepetion in json', e
        else:
            if type(data) == dict:
                for k, v in data.items():
                    if k == 'LoginRequest' and type(v) == dict:
                        usrName = v.keys()[0]
                        usrPwd = v.values()[0]
                        return self.__usrLogin(sock, usrName, usrPwd)
                    elif k == 'RegistRequest' and type(v) == dict:
                        usrName = v.keys()[0]
                        usrPwd = v.values()[0]
                        return self.__registNewUsr(usrName, usrPwd)
                    elif k == 'ChatConversation':
                        return v

    def __usrLogin(self, sock, usrName, usrPwd):

        if not self.__usrLoginStatus.has_key(usrName):
            print "account not exists"
            return "AccountNotExists"

        if self.__usrLoginStatus.has_key(usrName) and self.__usrLoginStatus[usrName] == True:
            print "usr is already online"
            return "UsrIsAlreadyOnline"

        if self.__usrLoginData[usrName] == usrPwd:
            self.__usrnameIPAddrAssociation[str(sock.getpeername())] = usrName
            self.__usrLoginStatus[usrName] = True
            return "SuccesfulLogin\n"
        else:
            return "InvalidLogin"

    def __getUsrName(self, sock):
        name = str(sock.getpeername())
        if self.__usrnameIPAddrAssociation.has_key(name):
            return self.__usrnameIPAddrAssociation[name]
        else:
            return str(name)

    def __registNewUsr(self, usrName, usrPwd):

        if self.__usrLoginData.has_key(usrName):
            print "Account Already Registed"
            return "AccountAlreadyRegisted"

        self.__usrLoginData[usrName] = usrPwd

        data = json.dumps(self.__usrLoginData)

        f = open('usrdata.dat', 'w')
        f.write(data.encode('utf-8'))
        f.close()
        return "SuccesfulRegistration"

    def __loadUsrData(self):
        f = open('usrdata.dat', 'r')
        data = f.read().decode('utf-8')
        self.__usrLoginData = json.loads(data)
        f.close()

        for k in self.__usrLoginData.keys():
            self.__usrLoginStatus[k] = False

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
                readList, writeList, errorList = select.select(self.sockCollections, [], self.sockCollections)

                for sock in readList:

                    if sock == self.serverSock:
                        # new client
                        newClient, newAddr = socketAccept(sock)
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

if __name__ == "__main__":

    server = ServerEnd()