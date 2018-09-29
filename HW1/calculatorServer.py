# socket programming TCP multi-thread server
import socket
import time
import _thread

# constants
bufsize = 16

# Get host name, IP address, and port number.
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
host_port = 8181

# Make a TCP socket object
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Bind the socket to server IP and port number
s.bind((host_ip, host_port))

# Listen allow 100 pending connects (like  a queue)
s.listen(100)
print('\nServer on {} port {} started. Waiting for connection...\n'.format(host_ip,host_port))


# Current time on the server
def now(): # define a function called now()
    return time.ctime(time.time())

# CONTRACT: String -> int
# GIVEN:    a problem as a string
# RETURNS:  the answer of the problem as a int
def myCalculate(problem):
    problem = problem + '#'

    def helper(stack,i):
        num = 0
        sign = '+'
        while i < len(problem):
            c = problem[i]
            if c.isdigit():
                num = num * 10 + int(c)
                i += 1
            elif c == '(':
                num, i = helper([], i+1)
            else:
                if sign == '+':
                    stack.append(num)
                if sign == '-':
                    stack.append(-num)
                if sign == '*':
                    stack.append(stack.pop() * num)
                if sign == '/':
                    stack.append(int(stack.pop() / num))
                num = 0
                i += 1
                if c == ')':
                    return sum(stack), i
                sign = c
        return sum(stack)

    return helper([],0)            


# handler defines what to do with one client's request
def handler(conn):
    print('A handler started working...\n')
    # receive a bytes
    # print('Received bytes: ', message)
    # decode the bytes
    # calculate the results
    buffer2 = conn.recv(bufsize)
    allowance = len(buffer2)
    ptr = 0
    number = buffer2[0:2]
    numOfProblems = int.from_bytes(number, byteorder='big')
    print('number of problems: ', numOfProblems)
    ptr += 2
    allowance -= 2
    answers = [0] * numOfProblems # answers of each problem

    # decode each problem and call calculate to get the answer
    print('Server is calculating the problems ...\n')
    for i in range(numOfProblems):
        if allowance < 2:
            tmp = conn.recv(bufsize)
            buffer2 = buffer2 + tmp
            allowance += len(tmp)
        sizebytes = buffer2[ptr:ptr+2]
        size = int.from_bytes(sizebytes,byteorder='big')
        ptr += 2
        allowance -= 2
        while allowance < size:
            tmp = conn.recv(bufsize)
            buffer2 = buffer2 + tmp
            allowance += len(tmp)
        problembytes = buffer2[ptr:ptr+size]
        problem = problembytes.decode("utf-8")
        answer = myCalculate(problem)
        answers[i] = answer
        ptr += size
        allowance -= size
    print('Answers: ', answers, '\n')

    # pack the results to a single byte-sequence
    outbytesarray = []
    outbytesarray.append(number)
    for i in range(numOfProblems):
        ansstr = str(answers[i])
        ansbyte = ansstr.encode('utf-8')
        anslen = len(ansbyte)
        lenbyte = anslen.to_bytes(2,byteorder='big')
        outbytesarray.append(lenbyte)
        outbytesarray.append(ansbyte)
    outbytes = b''.join(outbytesarray)
    print('Outbytes is: ', outbytes, '\n')

    # send the result in the agreed protocol format back to the client
    # close the connection with this specific client
    conn.sendall(outbytes)
    conn.close()


# Keep the server socket open and listenning to a client's request

while True:    
    conn, addr = s.accept()     
    print('Server connected by', addr,'at', now(),'\n')     
    _thread.start_new(handler, (conn,)) 