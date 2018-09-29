# This exampel is using Python 3 
# socket programming - TCP client
import socket

# variables and constants
bufsize = 16
server_ip = '10.138.0.2'
server_port = 8181
# test cases
problems0 = [b'\x00\x00']
problems1 = [b'\x00\x04', b'\x00\x04', b'3*12', #36
                        b'\x00\x06',  b'1*12/3',  #4
                        b'\x00\x04', b'3*12', 
                        b'\x00\x06',  b'1*12/3']

problems2 = [b'\x00\x02', b'\x00\x04', b'3*12', 
                        b'\x00\x06',  b'1*12/3']

problems3 = [b'\x00\x01', b'\x00\x04', b'3*12'] 

problem4 = [b'\x00\x04', b'\x00\x06', b'1*12/3', 
                        b'\x00\x13', b'(1+8)/2-(19-288)*31', # 8343
                        b'\x00\x04', b'3*12', 
                        b'\x00\x13', b'(1+8)/2-(19-288)*31'] 
problem5 = [b'\x00\x01', b"\x00'", b'((1+8)/2-(19-288))*(31+1234567)-2345678'] # 334699576

# Make a TCP socket object.
# API: socket(address_family, socket_type)
#             |AF_INET: IPv4  |SOCK_STREAM: TCP socket
#             |AF_INET6: IPv6 |SOCK_DGRAM: UDP socket
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Connect to server machine and port
# API: connect(address)
#   connect to a remote socket at the given address.
s.connect((server_ip, server_port))
print('Connected to server ', server_ip, ':', server_port)

# join the byte list
byproblems = b''.join(problem4)

# send the problems in bytes through the connection built
s.sendall(byproblems)

# receive the answers in bytes

# visualize the answers
buffer2 = s.recv(bufsize)
ptr = 0
allowance = len(buffer2)
numberofAnswers = int.from_bytes(buffer2[0:2], byteorder='big')
answers = [''] * numberofAnswers
ptr += 2
allowance -= 2
for i in range(numberofAnswers):
    if allowance < 2:
        tmp = s.recv(bufsize)
        buffer2 = buffer2 + tmp
        allowance += len(tmp)
    answersize =  int.from_bytes(buffer2[ptr:ptr+2], byteorder='big')
    ptr += 2
    allowance -= 2
    while allowance < answersize:
        tmp = s.recv(bufsize)
        buffer2 = buffer2 + tmp
        allowance += len(tmp)
    oneansbytes = buffer2[ptr:ptr+answersize]
    answers[i] = oneansbytes.decode('utf-8')
    ptr += answersize
    allowance -= answersize
print('Here are your answers: ', answers)

# close the socket to send EOF to server
s.close()