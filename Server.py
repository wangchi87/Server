# -*- coding: utf-8 -*-

import datetime
import select
import sys
import threading

from ClientStatus import *
from SocketWrapper import *
from Utilities import *


class ServerEnd:

    serverSock = None
    port = 12354
    host = None

    RECV_BUFFER = 4096

    # collection of all sockets,
    # including server and client sockets
    __sockCollections = []
    __sockLock = None

    # store all usernames and passwords
    # the KEY is username, the VALUE is a dict which has three fields:
    # 1. "PWD"      : password
    # 2. "lastLogin": last login time
    # 3. "totalTime": total online time
    __usrLoginData = {}

    # record whether user has logged in or not
    # this is NOT the same with the status of socket
    # the KEY is username, the VALUE is True or False
    __usrLogInOrOut = {}

    # associate username and socket
    # the KEY is a socket, the VALUE is corresponding username
    __usrnameSocketAssociation = {}

    # we apply a dict to manage the status of client sock
    # detecting the status of connected sock
    # the KEY is a socket, the VALUE is an object of ClientStatus
    # ClientStatus is created since the client is connected, not when logging
    __usrStatusManage = {}

    # we have two sub thread:
    # 1. heart beat thread
    # 2. updating usr online time thread
    __subThreadAlive = True

    # heart beat loop status and thread
    __hbThread = None

    # update usr online time thread
    __usrTimeThread = None

    def __init__(self):
        self.__sockCollections = []
        self.__sockLock = threading.Lock()
        self.host = socket.gethostname()
        # self.host = '127.0.0.1'  # socket.gethostname()

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

        self.__sockCollections.append(self.serverSock)
        self.__sockCollections.append(sys.stdin)

    def __closeServer(self):
        print "close server !!"
        self.__subThreadAlive = False
        self.__broadcastServerSysMsg("SERVER_SHUTDOWN", '')
        self.serverSock.close()

    def __acceptNewClient(self, sock):
        self.__usrStatusManage[sock] = ClientStatus()
        self.__sockCollections.append(sock)
        print "new client connected ", self.__getUsrName(sock)
        # self.__broadcastServerSysMsg("UsrLogin", self.__getUsrName(sock))

    def __closeDeadClient(self, sock):
        self.__sockLock.acquire()

        # print "sock to close:", sock
        # print "sock list", self.__sockCollections

        usrName = self.__getUsrName(sock)
        print "client disconnected", usrName

        if self.__usrLogInOrOut.has_key(usrName):
            self.__usrLogInOrOut[usrName] = False

        self.__updateUsrOnlineTime(sock)

        if self.__usrStatusManage.has_key(sock):
            self.__usrStatusManage[sock].clientLogOut()
            self.__usrStatusManage.__delitem__(sock)

        if self.__usrnameSocketAssociation.has_key(sock):
            self.__usrnameSocketAssociation.__delitem__(sock)

        if sock in self.__sockCollections:
            self.__sockCollections.remove(sock)

        sock.close()
        self.__dumpUsrData()
        self.__sockLock.release()

    def __safeSocketSend(self, sock, msg):
        # TODO: check sock is alive!
        if self.__checkSocketAlive(sock):
            if not socketSend(sock, msg):
                traceback.print_exc()
                self.__closeDeadClient(sock)

    def __checkSocketAlive(self, sock):
        try:
            sock.sendall('*')
        except socket.error as e:
            print sock, 'is down', e
            return False
        else:
            return True

    # ************************* broadcast usr or system msg methods **************************

    def __broadcastClientChatMsg(self, msgSock, msg):
        '''
        send chat msg from msgSock to other clients
        '''
        for sock in self.__sockCollections:
            if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packagePublicChatMsg(self.__getUsrName(msgSock) + ": " + msg))

    def __broadcastServerChatMsg(self, msg):
        # send server msg to all clients
        for sock in self.__sockCollections:
            if sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packagePublicChatMsg('server msg: ' + msg))

    def __broadcastServerSysMsg(self, key, msg):
        '''
        send server system msg to all clients
        :param key: key is the type of system msg, for example "SysLoginRequestAck"
        :param msg: msg we want to send
        :return:
        '''
        for sock in self.__sockCollections:
            if sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packageSysMsg(key, msg))

    def __broadcastClientSysMsg(self, msgSock, key, msg):
        '''
        send msg from msgSock to other clients, if client want to broadcast a SYSTEM LEVEL msg
        for example, one client declaims that he is logging out
        '''
        for sock in self.__sockCollections:
            if sock != msgSock and sock != self.serverSock and type(sock) == socket._socketobject:
                self.__safeSocketSend(sock, packageSysMsg(key, msg))

    # ************************* two sub-thread methods **************************
    def __detectClientStatus(self):
        '''
        detect heart beat signal from client
        '''
        print "start detecting client status"
        while self.__subThreadAlive:
            time.sleep(2)
            for sock, client in self.__usrStatusManage.items():
                if client.isClientOffline():
                    print sock, "is OFFLINE"
                    # self.__broadcastServerSysMsg('SysUsrLogOut', self.__getUsrName(sock))
                    # self.__usrStatusManage.__delitem__(sock)
                    self.__closeDeadClient(sock)
        print 'end of client status detection'

    def __updateOnlineClientsStatus(self):
        '''
        update the online duration information of each client every 60 seconds
        '''
        while self.__subThreadAlive:
            for sock in self.__usrStatusManage.keys():
                # send client online informaton
                self.__sendClientOnlineDurationMsg(sock)
            time.sleep(60)

    def __sendClientOnlineDurationMsg(self, sock):
        if self.__usrStatusManage[sock].hasLoggedIn():
            usrName = self.__getUsrName(sock)
            usrData = self.__usrLoginData[usrName]

            lastOnlineTimeStr = datetime.datetime.fromtimestamp(usrData['lastLogin']).strftime(
                "%Y-%m-%d-%H-%M")

            # historical online time + current online time
            totalTime = usrData['totalTime'] + self.__usrStatusManage[sock].getOnlineDuration()
            totalTimeStr = secondsToHMS(totalTime)
            timeMsg = packageSysMsg("SysUsrOnlineDurationMsg", lastOnlineTimeStr + ";" + totalTimeStr)

            self.__safeSocketSend(sock, timeMsg.encode('utf-8'))

    def __updateUsrOnlineTime(self, sock):
        usrName = self.__getUsrName(sock)
        if self.__usrStatusManage[sock].hasLoggedIn():
            self.__usrLoginData[usrName]['lastLogin'] = self.__usrStatusManage[sock].getLoginTimeStamp()
            self.__usrLoginData[usrName]['totalTime'] += self.__usrStatusManage[sock].getOnlineDuration()

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
        # print "Received command", recvedData
        if (not recvedData) or recvedData == "CLIENT_SHUTDOWN":
            try:
                self.__broadcastClientSysMsg(sock, 'SysUsrLogOut', self.__getUsrName(sock))
                self.__broadcastClientChatMsg(sock, "client disconnected\n")
                self.__closeDeadClient(sock)
            except Exception as e:
                print e
        elif recvedData == "-^-^-pyHB-^-^-":
            self.__usrStatusManage[sock].updateOnlineStatus()
        else:
            # parse recvedData
            needsReply, msg = self.__parseRecvdData(sock, recvedData)

            if needsReply:
                # process sys msg
                self.__safeSocketSend(sock, msg)
                if msg == '''{"SysMsg": {"SysLoginAck": "Successful login"}}''':
                    self.__sendClientOnlineDurationMsg(sock)
            else:
                # process chat msg:
                # msg will be like {'toAll':'abc'} or {'netease1':'abc'}
                # k is username, v is msg text
                for k, v in msg.items():
                    if k == "toAll":
                        # process BROADCAST chat msg
                        print 'msg to all from :', self.__getUsrName(sock), v
                        self.__broadcastClientChatMsg(sock, v)
                    else:
                        # process PRIVATE chat msg
                        receiverSock = None
                        # get the socket so which owns username k,
                        for i, j in self.__usrnameSocketAssociation.items():
                            # k is the one who will receive private msg
                            if j == k:
                                receiverSock = i
                                break
                        prvtMsg = packagePrivateChatMsg(self.__getUsrName(sock), v)
                        # send private chat msg
                        if receiverSock is not None:
                            # print so, recvedData
                            self.__safeSocketSend(receiverSock, prvtMsg)

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

            for k, v in self.__usrLogInOrOut.items():
                if v == True:
                    repliedStr['allOnlineUsernames'].append(k)

            return packageSysMsg("SysAllOnlineClientsAck", repliedStr)
        except Exception as e:
            print "exception in replying all online username", e

    # *********************** user login and registration ********************
    def __usrLogin(self, sock, usrName, usrPwd):
        '''
        process user login request
        and make a reply
        '''
        if not self.__usrLoginData.has_key(usrName):
            print "account not exists"
            return packageSysMsg('SysLoginAck', "Account Not exists")

        if self.__usrLogInOrOut.has_key(usrName) and self.__usrLogInOrOut[usrName] == True:
            print "usr is already online"
            return packageSysMsg('SysLoginAck', "This User is already online")

        if self.__usrLoginData[usrName]['pwd'] == usrPwd:
            self.__usrnameSocketAssociation[sock] = usrName
            self.__usrLogInOrOut[usrName] = True
            self.__usrStatusManage[sock].clientLogin()
            self.__broadcastClientSysMsg(sock, "SysUsrLogin", usrName)
            return packageSysMsg('SysLoginAck', "Successful login")
        else:
            return packageSysMsg('SysLoginAck', "Invalid login")

    def __registNewUsr(self, usrName, usrPwd):
        '''
        process user register request
        and make a reply
        '''
        if self.__usrLoginData.has_key(usrName):
            print "Account Already Registered"
            return packageSysMsg('SysRegisterAck', "Account has already been registered")

        self.__usrLoginData[usrName] = {'pwd': usrPwd, 'lastLogin': time.time(), 'totalTime': 0.0}
        self.__dumpUsrData()
        return packageSysMsg('SysRegisterAck', "Successful registration")

    def __getUsrName(self, sock):
        if self.__usrnameSocketAssociation.has_key(sock):
            return self.__usrnameSocketAssociation[sock]
        else:
            try:
                name = str(sock.getpeername())
            except BaseException:
                return ''
            else:
                return name

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
            if data:
                self.__usrLoginData = json.loads(data)
            else:
                print "invalid usrdata.dat"
            f.close()
        except IOError as e:
            print "Could not open or find 'usrdata.dat' file"
        else:
            for k in self.__usrLoginData.keys():
                self.__usrLogInOrOut[k] = False

    # ***************************** main loop of server program *********************
    def __mainLoop(self):

        self.__initSocket()
        quitProgram = False

        try:
            while not quitProgram:
                readList, writeList, errorList = select.select(self.__sockCollections, [], self.__sockCollections)

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
                                print "failed to receive data, close invalid socket, then"
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