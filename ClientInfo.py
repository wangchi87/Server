import time

threshold = 2


class ClientInfo(dict):
    sock = None

    loginTime = None

    lastCheckInTime = None

    def __init__(self, sock):
        self.sock = sock
        self.loginTime = time.localtime()
        self.__updateOnlineStatus()

    def __updateOnlineStatus(self):
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
