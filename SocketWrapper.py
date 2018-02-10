
import socket
import struct


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
        sock.connect((host, port))
    except socket.error as err:
        print "failed to connect to server: ", err
        return False
    else:
        return True


# def socketSend(sock, data):
#     '''
#     :return: we return a boolean type of data to indicate whether there is
#     an expection when sending the data
#     '''
#     # print 'socket send data', data
#     # we add EOD(end of data) as the segmentation of data stream
#     data += 'EOD'
#     data.encode('utf-8')
#     try:
#         sock.sendall(data)
#     except socket.error as err:
#         print "failed to send data: ", err
#         return False
#     else:
#         return True

def socketSend(sock, data):
    '''
    :return: we return a boolean type of data to indicate whether there is
    an expection when sending the data
    '''
    # print 'socket send data', data
    # we add a header for each msg, which contains the length of each data
    head = ['msgHeader', len(data)]
    headPack = struct.pack('!9sI', *head)

    data = headPack + data.encode('utf-8')

    try:
        sock.sendall(data)
    except socket.error as err:
        print sock, "failed to send data: ", err
        return False
    else:
        return True


dataBuffer = ''
headerSize = 13

def socketRecv(sock, recvBuffSize):
    ''' socket recv except of this method is caught outside '''
    global dataBuffer

    while 1:

        data = sock.recv(recvBuffSize)

        # client never send ''!
        # this will happen only when the client is terminated unexpectedly
        if not data:
            # print 'receive empty string!'
            return data

        dataBuffer = dataBuffer + data

        while 1:
            if len(dataBuffer) < headerSize:
                break

            headPack = struct.unpack('!9sI', dataBuffer[:headerSize])
            msgBodySize = headPack[1]

            if len(dataBuffer) < headerSize + msgBodySize:
                break

            msg = dataBuffer[headerSize:headerSize + msgBodySize]

            dataBuffer = dataBuffer[headerSize + msgBodySize:]

            return msg

# def socketRecv(sock, recvBuffSize):
#     ''' socket recv except of this method is caught outside '''
#     data = ''
#
#     while 1:
#
#         buf = sock.recv(recvBuffSize)
#         buf.decode('utf-8')
#         data = data + buf
#
#         if data[-3:] == 'EOD':
#              break
#
#         # client never send ''!
#         # this will happen only when the client is terminated unexpectedly
#         if not data:
#             # print 'receive empty string!'
#             return data
#
#     return data[:-3]
