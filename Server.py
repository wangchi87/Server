# -*- coding: utf-8 -*-

import select
import sys
import threading

from ClientOnlineTimeInfo import *
from SocketWrapper import *
from Utilities import *


class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 4096

    sockCollections = []

    # store all usernames and passwords
    # the KEY is username, the VALUE is user password
    __usrLoginData = {}

    # record whether user is online or not
    # the KEY is username, the VALUE is True or False
    __usrOnlineStatus = {}

    # associate username and socket
    # the KEY is a socket, the VALUE is corresponding username
    __usrnameSocketAssociation = {}

    # we apply a dict to manage client sock
    # detecting the status of connected sock
    # the KEY is a socket, the VALUE is an object of ClientOnlineTimeInfo
    __usrAliveStatus = {}

    # heart beat loop status and thread
    hbLoop = True
    hbThread = None

    def __init__(self):
        self.sockCollections = []
        self.messageList = {}
        self.host = '127.0.0.1'  # socket.gethostname()

        self.__loadUsrData()

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
                    socketSend(sock, packageChatMsg(self.__getUsrName(msgSock) + ": " + msg))
            except socket.error:
                self.__closeDeadClient(sock)

    def __broadcastServerMsg(self, msg):
        for sock in self.sockCollections:
            try:
                if sock != self.serverSock and type(sock) == socket._socketobject:
                    socketSend(sock, packageChatMsg('server msg: ' + msg))
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
        self.__usrOnlineStatus[self.__getUsrName(sock)] = False
        self.__updateUsrOnlineTime(sock)
        self.__usrAliveStatus.__delitem__(sock)
        self.sockCollections.remove(sock)
        sock.close()
        self.__dumpUsrData()

    def __updateUsrOnlineTime(self, sock):
        usrname = self.__getUsrName(sock)
        self.__usrLoginData[usrname]['lastOnlineTime'] = self.__usrAliveStatus[sock].getLoginTimeStamp()
        self.__usrLoginData[usrname]['allOnlineDuration'] += self.__usrAliveStatus[sock].getOnlineDuration()


    def __detectClientStatus(self):
        print "start detecting client status"
        while self.hbLoop:
            time.sleep(2)
            for sock, client in self.__usrAliveStatus.items():
                if client.isClientOffline():
                    print sock, "is OFFLINE"
                    self.__closeDeadClient(sock)
        print 'end of client status detection'


    def __processRecvedData(self, sock, recvedData):
        '''
        This method process the received data from socket

        There are four types of received data:
        1. recvedData == '':
            when the client is closed unexpectedly, server will receive lots of empty string ''
            we take advantage of it, use it as a sign that client is closed.
        2. recvedData == "CLIENT_SHUTDOWN"
            this message means the client is closed manually
        3. recvedData == "-^-^-pyHB-^-^-"
            this is the heart beat message
        4. other message needs to be parsed with self.__parseRecvdData() method

        :param sock: the socket from which we get the received data
        :param recvedData: received data

        '''
        if (not recvedData) or recvedData == "CLIENT_SHUTDOWN":
            self.__broadcastClientMsg(sock, "client disconnected\n")
            self.__closeDeadClient(sock)
        elif recvedData == "-^-^-pyHB-^-^-":
            self.__usrAliveStatus[sock].updateOnlineStatus()
        else:
            # parse recvedData
            needServerReply, msg = self.__parseRecvdData(sock, recvedData)

            if needServerReply:
                socketSend(sock, msg)
            else:
                print 'msg from :', self.__getUsrName(sock), msg
                self.__broadcastClientMsg(sock, msg)

    def __parseRecvdData(self, sock, msg):
        '''
        This method parse the received message.
        We will firstly parse the received json data
        , and return
        the corresponding message

        There are two types of message:
        1. the message that server needs to reply, for example
            the LOGIN and REGISTER request from client.
        2. the message that server do NOT need to reply, that is usually
            a CONVERSATION message that the server needs to broadcast to other client

        :param sock: the socket from which we get msg
        :param msg: received message
        :return: (a, b) a is True or False, which means whether the server needs to reply to client or not
                        b is the message that the function returned
        '''

        try:
            data = json.loads(msg)
        except Exception as e:
            print 'exception in loading json data', e
        else:
            if type(data) == dict:
                for k, v in data.items():
                    if k == 'SysLoginRequest' and type(v) == dict:
                        usrName = v.keys()[0]
                        usrPwd = v.values()[0]
                        return True, self.__usrLogin(sock, usrName, usrPwd)
                    elif k == 'SysRegisterRequest' and type(v) == dict:
                        usrName = v.keys()[0]
                        usrPwd = v.values()[0]
                        return True, self.__registNewUsr(usrName, usrPwd)
                    elif k == 'Chat':
                        return False, v

    def __usrLogin(self, sock, usrName, usrPwd):

        if not self.__usrLoginData.has_key(usrName):
            print "account not exists"
            return packageMsg('SysLoginAck', "Account Not exists")

        if self.__usrOnlineStatus.has_key(usrName) and self.__usrOnlineStatus[usrName] == True:
            print "usr is already online"
            return packageMsg('SysLoginAck', "This User is already online")

        if self.__usrLoginData[usrName]['pwd'] == usrPwd:
            self.__usrnameSocketAssociation[sock] = usrName
            self.__usrOnlineStatus[usrName] = True
            self.__usrAliveStatus[sock].clientLogin()
            return packageMsg('SysLoginAck', "Successful login")
        else:
            return packageMsg('SysLoginAck', "Invalid login")

    def __getUsrName(self, sock):
        if self.__usrnameSocketAssociation.has_key(sock):
            return self.__usrnameSocketAssociation[sock]
        else:
            return str(sock.getpeername())

    def __registNewUsr(self, usrName, usrPwd):

        if self.__usrLoginData.has_key(usrName):
            print "Account Already Registered"
            return packageMsg('SysRegisterAck', "Account has already been registered")

        self.__usrLoginData[usrName] = {'pwd': usrPwd, 'lastOnlineTime': 0.0, 'allOnlineDuration': 0.0}

        self.__dumpUsrData()
        return packageMsg('SysRegisterAck', "Successful registration")

    def __dumpUsrData(self):
        data = json.dumps(self.__usrLoginData)
        try:
            f = open('usrdata.dat', 'w')
            f.write(data.encode('utf-8'))
            f.close()
        except IOError as e:
            print "Could not dump data"

    def __loadUsrData(self):
        try:
            f = open('usrdata.dat', 'r')
            data = f.read().decode('utf-8')
            self.__usrLoginData = json.loads(data)
            f.close()
        except IOError as e:
            print "Could not open or find 'usrdata.dat' file"
        else:
            for k in self.__usrLoginData.keys():
                self.__usrOnlineStatus[k] = False

    def __acceptNewClient(self, sock):
        self.__usrAliveStatus[sock] = ClientOnlineTimeInfo()
        self.sockCollections.append(sock)
        print "new client connected ", sock.getpeername()
        self.__broadcastClientMsg(sock, "new client connected \n")

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