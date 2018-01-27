
import socket

def socketCreation():
    try:
        sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    except socket.error as err:
        print "failed to create socket: ", err
    else:
        return sock

def socketBind(sock, host, port):
    try:
        sock.bind((host,port))
    except socket.error as err:
        print "failed to bind address: ", err

def socketListen(sock):
    try:
        sock.listen(5)
    except socket.error as err:
        print "failed to listen socket: ", err

def socketAccept(sock):
    try:
        s, a = sock.accept()
    except socket.error as err:
        print "failed to accept client: ", err
    else:
        return s, a

def socketConnection(sock, host, port):
    try:
        sock.connect((host,port))
    except socket.gaierror as err:
        print "failed to connect to server: ", err

def socketSend(sock, data):

    # we add EOD as the segmentation of data stream
    data += 'EOD'

    try:
        sock.send(data)
    except socket.error as err:
        print "failed to send data: ", err

def socketRecv(sock, recvBuffSize):

    data = ''
    while 1:
        try:
            buf = sock.recv(recvBuffSize)
        except socket.error as err:
            print "failed to receive data", err
        else:
            data = data + buf
            if data[-3:] == 'EOD':
                break

    return data[:-3]