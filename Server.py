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

    # collection of all sockets,
    # including server and client sockets
    sockCollections = []

    # store all usernames and passwords
    # the KEY is username, the VALUE is user password
    __usrLoginData = {}

    # record whether user has logged in or not
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
    __subThreadAlive = True
    __hbThread = None
    __usrTimeThread = None

    def __init__(self):
        self.sockCollections = []
        self.host = '127.0.0.1'  # socket.gethostname()

        self.__loadUsrData()

        self.__hbThread = threading.Thread(target=self.__detectClientStatus)
        self.__hbThread.setDaemon(True)
        self.__hbThread.start()

        self.__usrTimeThread = threading.Thread(target=self.__updateOnlineClientsStatus)
        self.__usrTimeThread.setDaemon(True)
        self.__usrTimeThread.start()

        self.__mainLoop()

    # ******************** socket management method ********************
    def assignHostAddr(self, host):
        self.host = host

    def assignPort(self, port):
        self.port = port

    def __initSocket(self):
        self.serverSock = socketCreation()
        socketBind(self.serverSock, self.host, self.port)
        self.serverSock.setblocking(False)
        socketListen(self.serverSock)

        self.sockCollections.append(self.serverSock)
        self.sockCollections.append(sys.stdin)

    def __closeServer(self):
        print "close server !!"
        self.__subThreadAlive = False
        self.__broadcastServerSysMsg("SERVER_SHUTDOWN", '')
        self.serverSock.close()

    def __acceptNewClient(self, sock):
        self.__usrAliveStatus[sock] = ClientOnlineTimeInfo()
        self.sockCollections.append(sock)
        print "new client connected ", self.__getUsrName(sock)
        # self.__broadcastServerSysMsg("UsrLogin", self.__getUsrName(sock))

    def __closeDeadClient(self, sock):
        print "client disconnected", self.__getUsrName(sock)
        self.__broadcastServerSysMsg('SysUsrLogOut', self.__getUsrName(sock))
        self.__usrOnlineStatus[self.__getUsrName(sock)] = False
        self.__updateUsrOnlineTime(sock)
        self.__usrAliveStatus[sock].clientLogOut()
        self.__usrAliveStatus.__delitem__(sock)
        self.sockCollections.remove(sock)
        sock.close()
        self.__dumpUsrData()

    def __safeSocketSend(self, sock, msg):
        if not socketSend(sock, msg):
            self.__closeDeadClient(sock)

    def __broadcastClientChatMsg(self, msgSock, msg):
        '''
        send msg from msgSock to other clients
        '''
        for sock in self.sockCollections:
            if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packagePublicChatMsg(self.__getUsrName(msgSock) + ": " + msg))

    def __broadcastServerChatMsg(self, msg):
        # send server msg to all clients
        for sock in self.sockCollections:
            if sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packagePublicChatMsg('server msg: ' + msg))

    def __broadcastServerSysMsg(self, key, msg):
        '''
        send server system msg to all clients
        :param key: key is the type of system msg, for example "SysLoginRequestAck"
        :param msg: msg we want to send
        :return:
        '''
        for sock in self.sockCollections:
            if sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packageSysMsg(key, msg))

    # ************************* sub-thread methods **************************
    def __detectClientStatus(self):
        '''
        detect heart beat signal from client
        '''
        print "start detecting client status"
        while self.__subThreadAlive:
            time.sleep(2)
            for sock, client in self.__usrAliveStatus.items():
                if client.isClientOffline():
                    print sock, "is OFFLINE"
                    self.__closeDeadClient(sock)
        print 'end of client status detection'

    def __updateOnlineClientsStatus(self):
        '''
        update the online duration information of each client every 60 seconds
        '''
        while self.__subThreadAlive:
            for sock in self.__usrAliveStatus.keys():
                # send client online informaton
                self.__sendClientOnlineDurationMsg(sock)
            time.sleep(60)

    def __sendClientOnlineDurationMsg(self, sock):
        if self.__usrAliveStatus[sock].hasLoggedIn():
            usrName = self.__getUsrName(sock)
            lastOnlineTimeStr = datetime.datetime.fromtimestamp(
                self.__usrLoginData[usrName]['lastOnlineTime']).strftime(
                "%Y-%m-%d-%H-%M")
            totalSeconds = self.__usrLoginData[usrName]['totalOnlineDuration'] + self.__usrAliveStatus[
                sock].getOnlineDuration()
            totalOnlintTimeStr = secondsToHMS(totalSeconds)
            timeMsg = packageSysMsg("SysUsrOnlineDurationMsg", lastOnlineTimeStr + ";" + totalOnlintTimeStr)
            self.__safeSocketSend(sock, timeMsg.encode('utf-8'))

    def __updateUsrOnlineTime(self, sock):
        usrname = self.__getUsrName(sock)
        if self.__usrAliveStatus[sock].hasLoggedIn():
            self.__usrLoginData[usrname]['lastOnlineTime'] = self.__usrAliveStatus[sock].getLoginTimeStamp()
            self.__usrLoginData[usrname]['totalOnlineDuration'] += self.__usrAliveStatus[sock].getOnlineDuration()

    # ********************** process client request *************************

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
            self.__broadcastClientChatMsg(sock, "client disconnected\n")
            self.__closeDeadClient(sock)
        elif recvedData == "-^-^-pyHB-^-^-":
            self.__usrAliveStatus[sock].updateOnlineStatus()
        else:
            # parse recvedData
            needServerReply, msg = self.__parseRecvdData(sock, recvedData)

            if needServerReply:
                # process sys msg
                self.__safeSocketSend(sock, msg)
                if msg == '''{"SysMsg": {"SysLoginAck": "Successful login"}}''':
                    # print msg
                    self.__sendClientOnlineDurationMsg(sock)
                    # time.sleep(0.1)
                    # self.__broadcastServerChatMsg(self.__getUsrName(sock) + ' is online\n')
            else:
                # process chat msg
                for k, v in msg.items():
                    if k == "toAll":
                        # process lobby chat
                        print 'msg to all from :', self.__getUsrName(sock), v
                        self.__broadcastClientChatMsg(sock, v)
                    else:
                        # process private chat
                        # get the socket so which owns username k
                        so = None
                        for i, j in self.__usrnameSocketAssociation.items():
                            if j == k:
                                so = i
                                break
                        # send private chat msg
                        if so is not None:
                            print so, recvedData
                            self.__safeSocketSend(so, recvedData)

    def __parseRecvdData(self, sock, msg):
        '''
        This method parse the received message.
        We will firstly parse the received json data, and return
        the corresponding message

        There are two types of message:
        1. the message that server needs to make a reply, for example
            the LOGIN and REGISTER request from client.
        2. the message that server do NOT have to reply, that is usually
            a CHAT message that the server needs to broadcast to other client

        the protocol of msg we used here are as following:
        all the message are packed in a dict structure:

        message can be attributed as system message or chat message, which leads to the dict structure:
        1. {'SysMsg': {a:b}}:
            a field are used to identify the types of system msg, for instance: "SysLoginRequest"
            b field are usually the real msg that we want to send, it could be a str or dict, according to the type of a field
        2. {'ChatMsg': {a:b}}:
            a field here is to identify to whom the chat msg is to send:
                'toAll' means: we want to broadcast the msg
                if a field is a user name, it means we want to send msg privately
            b field is the msg we want to send

        :param sock: the socket from which we get msg
        :param msg: received message
        :return: (a, b) a is True or False, which means whether the server needs to reply to client or not
                        b is the message that the function returned
        '''
        data = ''
        try:
            data = json.loads(msg)
        except Exception as e:
            print 'exception in loading json data: ', e
        finally:
            if type(data) == dict:
                for k, v in data.items():
                    if k == 'ChatMsg':
                        # v will be a dict {'toAll': msg} or {'XXX': msg}
                        return False, v
                    elif k == 'SysMsg':
                        # v will be a dict, {'SysLoginRequest': {}} or {'SysRegisterRequest': {}}
                        for i, j in v.items():
                            if i == 'SysLoginRequest':
                                # case: {'SysLoginRequest': {usrname:usrpwd}}
                                usrName = j.keys()[0]
                                usrPwd = j.values()[0]
                                return True, self.__usrLogin(sock, usrName, usrPwd)

                            if i == 'SysRegisterRequest':
                                # case: {'SysRegisterRequest': {usrname:usrpwd}}
                                usrName = j.keys()[0]
                                usrPwd = j.values()[0]
                                return True, self.__registNewUsr(usrName, usrPwd)

                            if i == 'SysAllOnlineClientsRequest':
                                # v : {'SysLoginRequest': {usrname:usrpwd}}
                                return True, self.__replyAllOnlineUsrnames()

    def __replyAllOnlineUsrnames(self):
        try:
            usrname = []
            repliedStr = {"allOnlineUsernames": usrname}

            for k, v in self.__usrOnlineStatus.items():
                if v == True:
                    repliedStr['allOnlineUsernames'].append(k)
            # print "*****", allUsernameStr
            return packageSysMsg("SysAllOnlineClientsAck", repliedStr)
        except Exception as e:
            print "exception in replying all online username", e

    # *********************** user login and registration ********************
    def __usrLogin(self, sock, usrName, usrPwd):

        if not self.__usrLoginData.has_key(usrName):
            print "account not exists"
            return packageSysMsg('SysLoginAck', "Account Not exists")

        if self.__usrOnlineStatus.has_key(usrName) and self.__usrOnlineStatus[usrName] == True:
            print "usr is already online"
            return packageSysMsg('SysLoginAck', "This User is already online")

        if self.__usrLoginData[usrName]['pwd'] == usrPwd:
            self.__usrnameSocketAssociation[sock] = usrName
            self.__usrOnlineStatus[usrName] = True
            self.__usrAliveStatus[sock].clientLogin()
            self.__broadcastServerSysMsg("SysUsrLogin", usrName)
            return packageSysMsg('SysLoginAck', "Successful login")
        else:
            return packageSysMsg('SysLoginAck', "Invalid login")

    def __getUsrName(self, sock):
        if self.__usrnameSocketAssociation.has_key(sock):
            return self.__usrnameSocketAssociation[sock]
        else:
            return str(sock.getpeername())

    def __registNewUsr(self, usrName, usrPwd):

        if self.__usrLoginData.has_key(usrName):
            print "Account Already Registered"
            return packageSysMsg('SysRegisterAck', "Account has already been registered")

        self.__usrLoginData[usrName] = {'pwd': usrPwd, 'lastOnlineTime': time.time(), 'totalOnlineDuration': 0.0}
        self.__dumpUsrData()
        return packageSysMsg('SysRegisterAck', "Successful registration")

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

    # ***************************** main loop of server program *********************
    def __mainLoop(self):

        self.__initSocket()
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
                                self.__closeDeadClient(sock)
                            else:
                                self.__processRecvedData(sock, recvedData)

                        if type(sock) == file:
                            msg = sys.stdin.readline()
                            if msg == 'esc\n' or msg == '':
                                quitProgram = True
                            else:
                                self.__broadcastServerChatMsg(msg)

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