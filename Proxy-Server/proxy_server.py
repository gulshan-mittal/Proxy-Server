#!/usr/bin/python2

import os
import sys
import time
import socket
import ast

# Proxy Server Host and Port
PROXY_HOST = ''
PROXY_PORT = 7777
#Web Server Host and Port
WEB_HOST = '127.0.0.1'
WEB_PORT = 7776

RESPONSE_CODES = {
    200: 'OK',
    304: 'Not Modified',
    400: 'Bad Request',
    404: 'Not Found',
    405: 'Method Not Allowed',
    414: 'Request URI too long',
}
CACHE = {}
CACHE_SIZE = 3

class ProxyServer:
    """ Proxy Server Class """

############################    Proxy Server as a Server    ########################################
    
    def __init__(self):
        """ Setup the proxy server to listen to the client """
        try :
            self.proxy_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, err:
            print("Error creating server socket: %s" %err)
            sys.exit(1)

        try :
            self.proxy_sock.bind((PROXY_HOST, PROXY_PORT))
        except socket.error, err:
            print("Error in binding host and port: %s" %err)

        self.proxy_sock.listen(5)
        print('Server listening....')

        """ Making Cache When Proxy Server restart """
        for file in os.listdir('.'):
            if file != 'proxy_server.py':
                with open(file,'r') as f:
                    raw_data = f.read().replace('\n', '')
                f.close
                data = ast.literal_eval(raw_data)
                cache_url = "http://localhost:7776/" + file[:-4]
                CACHE[cache_url] = {'count': 1, 'last_used': data['headers']['Date:'], 'first_used': data['headers']['Date:']}

    def initClientRequest(self):
        """ Initiate the Client request and set rfile and wfile for read and write """
        self.connection, self.client_addr = self.proxy_sock.accept()
        self.connection.settimeout(10)
        print('Got connection from', self.client_addr)

        # We default rfile to buffered because otherwise it could be
        # really slow for large data (a getc() call per byte); we make
        # wfile unbuffered because (a) often after a write() we want to
        # read and we need to flush the line; (b) big writes to unbuffered
        # files are typically optimized by stdio even when big reads
        # aren't.
        self.rfile = self.connection.makefile('rb', -1)
        self.wfile = self.connection.makefile('wb',  0)

        self.raw_request = ""
        self.method = ""
        self.url = ""
        self.version = ""
        self.request_headers = {}
        self.raw_response = ""
        self.response_headers = {}

    def finishClientRequest(self):
        """ Called to shutdown and close an individual request """
        if not self.wfile.closed:
            self.wfile.flush()
        self.wfile.close()
        self.rfile.close()

        try:
            self.connection.shutdown(socket.SHUT_WR)
        except socket.error, err:
            pass
        
        self.connection.close()
        print("Connection closed\n")

    def processClientRequest(self):
        """ Process the request of the client """
        lfu_url = ''
        lfu_count = sys.maxint
        
        # Search for response in the cache
        if (self.method != 'GET'):
            #self.send_error(405)
            return 
        for request_url in CACHE:
            print(request_url, CACHE[request_url])
            if (request_url == self.url):
                cached_response_time = time.mktime(time.strptime(CACHE[request_url]['first_used'], "%a, %d  %b %Y %H:%M:%S %Z"))
                current_time = time.mktime(time.gmtime())
                if (current_time - cached_response_time > 86400):
                    CACHE.pop(request_url)
                    os.remove(request_url.split('/')[3] + '.txt') 
                    break

                print("found in cache")

                with open(self.url.split('/')[3]+".txt",'r') as f:
                    data = f.read().replace('\n', '')
                f.close
                data = ast.literal_eval(data)
                

                self.raw_response = data['raw']
                CACHE[request_url]['count'] += 1
                CACHE[request_url]['last_used'] = time.strftime("%a, %d  %b %Y %H:%M:%S %Z", time.gmtime())
                return
            else:
                if CACHE[request_url]['count'] < lfu_count:
                    lfu_count = CACHE[request_url]['count']
                    lfu_url = request_url 
                elif CACHE[request_url]['count'] == lfu_count:
                    lfu_url_time = time.strptime(CACHE[lfu_url]['last_used'], "%a, %d  %b %Y %H:%M:%S %Z")
                    request_url_time = time.strptime(CACHE[request_url]['last_used'], "%a, %d  %b %Y %H:%M:%S %Z")
                    if lfu_url_time > request_url_time:
                        lfu_count = CACHE[request_url]['count']
                        lfu_url = request_url

        
        # Get the response from the Web Server
        print("Connecting to web server")
        self.connectToWebServer()
        print("Sending request to the web server")
        self.sendServerRequest(self.raw_request)
        print("Receiving response from the web server...")
        self.recvServerResponse()
        print("Disconnecting the web server")
        self.disconnectWebServer()
        
        #Update Cache
        if len(CACHE) >= CACHE_SIZE:
            CACHE.pop(lfu_url)
            os.remove(lfu_url.split('/')[3] + '.txt') 
        
        if self.response_headers['Cache-control:'] != 'no-cache':
            response = {'raw': self.raw_response, 'headers': self.response_headers}
            with open(self.url.split('/')[3] + '.txt','w+') as f:
            	f.write(str(response))
            f.close
            CACHE[self.url] = {'count': 1, 'last_used': str(self.response_headers['Date:']), 'first_used': str(self.response_headers['Date:'])}

    def recvClientRequest(self):
        """ Receive Client Request """
        raw_requestline = self.rfile.readline(8193)
        while raw_requestline != '\r\n':
            if (len(raw_requestline) > 8192):
                #self.send_error(414)
                return 

            print(raw_requestline)
            requestline = raw_requestline.rstrip('\r\n').split()
            if (len(requestline) == 3 and requestline[0] == 'GET'):
                self.method = requestline[0]
                self.url = requestline[1]
                # WEB_HOST, WEB_PORT = requestline[1].split('/')[2].split(':')
                self.version = requestline[2]
                self.raw_request += self.method + ' /' + self.url.split('/')[3] + ' ' + self.version + '\r\n'
            elif len(requestline) > 0:
                self.request_headers[requestline[0]] = ' '.join(requestline[1:])
                self.raw_request += raw_requestline
            
            raw_requestline = self.rfile.readline(8193)
        self.raw_request += '\r\n'

    def sendClientResponse(self, response):
        """ Send response to the client as per the request of the client """
        self.wfile.write(response)

    def handleRequest(self):
        """ Handle the request of the connected client """
        self.recvClientRequest()
        print(self.raw_request)
        self.processClientRequest()
        if (self.raw_response != ""):
            print(self.raw_response)
            self.sendClientResponse(self.raw_response)
        else:
            self.sendClientResponse("Error")

    #def sendStatus(self, code):
    #    """ Send status of the response to the client """
    #    self.wfile.write("%s %d %s\r\n" %(self.protocol_version, code, RESPONSE_CODES[code]))
    #
    #def sendHeaderLine(self, field_name, value):
    #    """ Send a header line """
    #    self.wfile.write("%d: %s\r\n" %(field_name, value))

############################    Proxy Server as a Client    ########################################

    def connectToWebServer(self):
        """ Setup a connection to web server and set web_rfile and web_wfile for read and write """
        try :
            self.pclient_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, err :
            print("Error creating server socket: %s" %err)
            sys.exit(1)
        
        try:
            self.pclient_sock.connect((WEB_HOST, WEB_PORT))
        except socket.gaierror, err:
            print("Address-related error connecting to server: %s" % err)
            sys.exit(1)
        except socket.error, err:
            print("Connection Error: %s" %err)
            sys.exit(1)

        self.pclient_sock.settimeout(10)
        self.web_rfile = self.pclient_sock.makefile('rb', -1)
        self.web_wfile = self.pclient_sock.makefile('wb',  0)

    def sendServerRequest(self, request):
        """ Send client request to the web server """
        self.web_wfile.write(request)

    def recvServerResponse(self):
        """ Receive response from the Web Server to send it to the client """
        raw_responseline = self.web_rfile.readline()
        while raw_responseline != '\r\n':
            responseline = raw_responseline.rstrip('\r\n').split()
            if len(responseline) > 0:
                self.response_headers[responseline[0]] = ' '.join(responseline[1:])
            self.raw_response += raw_responseline

            raw_responseline = self.web_rfile.readline()
        self.raw_response += '\r\n'
        
        #total_data_size = -1
        #if self.response_headers.has_key('Content-Length:') :
        #    total_data_size = int(self.response_headers['Content-Length:'])
        #current_data_size = 0
        raw_responseline = self.web_rfile.readline()
        while raw_responseline != '':
            #current_data_size += len(raw_responseline)
            self.raw_response += raw_responseline
            raw_responseline = self.web_rfile.readline()

    def disconnectWebServer(self):
        """ Disconnect from the web server after the response has been received """
        if not self.web_wfile.closed:
            self.web_wfile.flush()
        self.web_wfile.close()
        self.web_rfile.close()
        
        try:
            self.pclient_sock.shutdown(socket.SHUT_RD)
        except socket.error, err:
            pass
        
        self.pclient_sock.close()
        print("Connection to the web server closed")


if __name__ == '__main__':

    proxy_server = ProxyServer()
    while True:
        print("Connecting to the client")
        proxy_server.initClientRequest()
        print("\nHandling the client request")
        proxy_server.handleRequest()
        print("\nDisconnecting the client")
        proxy_server.finishClientRequest()
