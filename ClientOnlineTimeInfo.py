# -*- coding: utf-8 -*-

import time

threshold = 1000

class ClientOnlineTimeInfo:
    '''
    This class is mainly used to maintain the status of each client.
    The client will send 'heart beat' package ("-^-^-pyHB-^-^-") to the server

    There are two benefits of doing this:
    1. the heart beat package will allow the server to be aware of whether the client is ALIVE or not
    2. the heart beat package also serve as PASSWORD to maintain a connection with the server,
       so that the connection which is NOT raised from our client program will be rejected(closed by the server)
    '''
    __hasLoggedIn = False
    # record how long the user keeps online this time
    __onlineDuration = None
    __lastOnlineTimeStamp = None

    __loginTimeStamp = None

    # record the time stamp that a heart beat signal came in
    __lastCheckInTimeStamp = None

    def __init__(self):
        self.updateOnlineStatus()

    def clientLogin(self):
        self.__hasLoggedIn = True
        self.__loginTimeStamp = time.time()

    def clientLogOut(self):
        self.__hasLoggedIn = False

    def hasLoggedIn(self):
        return self.__hasLoggedIn

    def updateOnlineStatus(self):
        self.__lastCheckInTimeStamp = time.time()

    def isClientOffline(self):
        delta = time.time() - self.__lastCheckInTimeStamp

        if delta <= threshold:
            return False
        else:
            return True

    def lastCheckedIn(self):
        return self.__lastCheckInTimeStamp

    def getOnlineDuration(self):
        self.__onlineDuration = time.time() - self.__loginTimeStamp
        return self.__onlineDuration

    def getLoginTimeStamp(self):
        return self.__loginTimeStamp


if __name__ == '__main__':
    ci = ClientOnlineTimeInfoInfo()

    time.sleep(2.1)

    ci.recordOfflineTime()

    print ci.isClientOffline()
