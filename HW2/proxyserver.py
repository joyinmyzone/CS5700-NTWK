# import the socket module, the sys module and the thred module
import socket
import sys
import _thread

# Constants and System Setting 
bufsize = 4096
queue_size = 5
host_name = socket.gethostname()
host_ip = socket.gethostbyname(host_name)
try:
    listenning_port = int(input("[System] Please Enter Listenning Port Number: \n[System] Enter Ctrl + C to exit.\n"))
except KeyboardInterrupt:
    print("\n[System] User Requested An Interrupt")
    print("\n[System] Application Existing ...")
    sys.exit()

# Make Connection to End Server
# GIVEN:    the name of the end server as a string
#           the end port number as an int
#           the conn (the socket used to talk to the client)
#           the proxy server's address as a string
#           the data from the client as a bytes
# DO:       forward the bytes from the client to the end server
#           forward the reply from the end server to the client
#           close the connections of both sides
def proxy_server(web_server,port,conn,addr,data):
    try:
        server_ip = socket.gethostbyname(web_server)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((server_ip,port))
        #Forward the client's request exactly as it is to the end server
        s.sendall(data)

        listenning = True
        while listenning:
            reply = s.recv(bufsize)
            if (len(reply) > 0):
                #Send the reply back to client
                conn.send(reply)
                dar = float(len(reply))
                dar = float(dar/1024)
                dar = '%.3s' % (str(dar))
                dar = '%s KB' % (dar)
                print('[System] Request Done: %s -> %s <-' %(str(addr[0]),str(dar)))
            #Break the connection if receiving data failed (finished)
            else:
                break
        #Close the socket used to talk to the end server
        s.close()
        #Close the connection with the end client
        conn.close()
    except socket.error as e:
        print(e,'proxy_server')
        s.close()
        conn.close()
        sys.exit(1)


# Receive Connection Details from Original Client
# GIVEN: a connection stream, a client data, an address from the connection
# DO: Retrive connection details
def conn_string(conn,data,addr):
    try:
        str_data = data.decode('utf-8')
        los_data = str_data.split('\r\n')
        request_line = los_data[0]
        print('[System]', request_line)
        print('[System]', los_data[1])
        #GET http://www.foo.com/mumbo.html HTTP/1.1
        req_type = request_line.split(' ')[0] 
        #Proxy server only needs to support GET method
        if req_type != 'GET':
            print('[System] Support GET Only')
            print('[System] Back to listenning ...')
            return
        #URL: http://www.foo.com/munbo.html
        url = request_line.split(' ')[1]
        print('[System] URL: ',url)
        http_position = url.find('http://')
        #If URL name not found, set temp as null
        if http_position == -1:
            temp = url
        #If URL name found, set temp as url
        else:
            temp = url[(http_position + 7):]
        #Find the start index of the port number (if any)
        port_position = temp.find(':')
        #Find the end of the web server
        #www.foo.com/
        end_server_name = temp.find('/')
        if end_server_name == -1:
            end_server_name = len(temp)
        web_server = ''
        port = -1
        #If no port number found or no specific web server name found
        #set port number as 80 by default, set web server as null
        if port_position == -1 or end_server_name == -1:
            port = 80 #Port by default is 80 for HTTP protocol
            web_server = temp[:end_server_name]
        #Else set the port number given by the client request
        #set web server name given by the client request
        else:
            port = int((temp[(port_position+1):])[:end_server_name-port_position-1])
            web_server = temp[:port_position]
        #Check and modify the connection setting to close
        if los_data[1].split(':')[0] != 'Connection':
            print('[System] Modifying Connection setting to close')
            los_data.insert(1,'Connection: close')
            string_data = '\r\n'.join(los_data)
            data = string_data.encode('utf-8')
        #Forward the request to the end server
        print('[System] Forwarding request to End Server {} on port {}'.format(web_server,port))
        proxy_server(web_server,port,conn,addr,data)
    except Exception as e:
        print(e,'conn_string')
        pass


# main()
# Instantiates a socket, bind it to the host on port, and start listenning
def main():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print('[System] Initializing Sockets ...')
        print('[System] Sockets Initialized ...')
        s.bind((host_ip,listenning_port))
        print('[System] Sockets Binded to Port {} ...'.format(listenning_port))
        s.listen(queue_size)
        print('[System] Server Started Successfully, Listenning On {} Port {}'.format(host_ip,listenning_port))
    except Exception:
        print("[System] Unable to Initialize Socket")
        sys.exit(2)

    listenning = True
    while listenning:
        try:
            conn, addr = s.accept()
            data = conn.recv(bufsize)
            _thread.start_new(conn_string,(conn,data,addr))
        except KeyboardInterrupt:
            s.close()
            print('[System] Proxy Server Shutting Down ...')
            print('[System] Bye!')
            sys.exit(1)
    s.close()

# main
if __name__ == '__main__':
    main()