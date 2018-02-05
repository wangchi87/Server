import time

threshold = 1

class ClientInfo(dict):
    '''
    This class is mainly used to maintain the status of each client.
    The client will send 'heart beat' package ("-^-^-pyHB-^-^-") to the server

    There are two benefits of doing this:
    1. the heart beat package will allow the server to be aware of whether the client is ALIVE or not
    2. the heart beat package also serve as PASSWORD to maintain a connection with the server,
       so that the connection which is NOT raised from our client program will be rejected(closed by the server)
    '''
    sock = None

    loginTime = None

    lastCheckInTime = None

    def __init__(self, sock):
        self.sock = sock
        self.loginTime = time.localtime()
        self.updateOnlineStatus()

    def updateOnlineStatus(self):
        self.lastCheckInTime = time.time()

    def isClientOffline(self):
        delta = time.time() - self.lastCheckInTime

        if delta <= threshold:
            return False
        else:
            return True

    def lastCheckedIn(self):
        return self.lastCheckInTime


if __name__ == '__main__':
    ci = ClientInfo(sock=1)

    print ci.lastCheckedIn()

    time.sleep(2.1)

    print ci.isClientOffline()
