#!/usr/bin/python2

import os
import time
import SocketServer
import SimpleHTTPServer

PORT = 7776

class HTTPCacheRequestHandler(SimpleHTTPServer.SimpleHTTPRequestHandler):
    def send_head(self):
        print(self.headers)
        if self.command != "POST" and self.headers.get('If-Modified-Since', None):
            filename = self.path.strip("/")
            if os.path.isfile(filename):
                a = time.strptime(time.ctime(os.path.getmtime(filename)), "%a %b %d %H:%M:%S %Y")
                b = time.strptime(self.headers.get('If-Modified-Since', None), "%a, %d  %b %Y %H:%M:%S %Z")
                if a < b:
                    self.send_response(304)
                    self.end_headers()
                    return None
        return SimpleHTTPServer.SimpleHTTPRequestHandler.send_head(self)

    def end_headers(self):
        filename = self.path.strip("/")
        if filename == "2.binary":
            self.send_header('Cache-control', 'no-cache')
        else:
            self.send_header('Cache-control', 'must-revalidate')
        SimpleHTTPServer.SimpleHTTPRequestHandler.end_headers(self)

s = SocketServer.ThreadingTCPServer(("", PORT), HTTPCacheRequestHandler)
s.allow_reuse_address = True
print "Serving on port", PORT
s.serve_forever()
