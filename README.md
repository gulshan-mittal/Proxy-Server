# HTTP Proxy Server

### Gulshan Kumar - 20161082


### How to run code

- Proxy-Server

  - ./proxy_server.py

- Web-Server

  - ./web_server.py

- On terminal or Browser

  - terminal

    - curl -iv --raw -x `http://localhost:7777 http://127.0.0.1:7776/<file-name>`

  - Browser

    - Set the proxy e.g in firefox open the preference option inside network use `proxy= 127.0.0.1` and `port = 7777`

    ![proxy-setting](proxy-setting.png)

    - open any file



#### <u>Proxy Server</u>

A proxy server is a dedicated computer or a software system running on a computer that acts as an intermediary between an endpoint device, such as a computer, and another server from which a user or client is requesting a service. The proxy server may exist in the same machine as a firewall server or it may be on a separate server, which forwards requests through the [firewall](http://searchsecurity.techtarget.com/definition/firewall).



#### <u>Caching</u>

When the proxy server gets a request, it checks if the requested object is cached (i.e. server
already has the request webpage or file), and if yes, it returns the object from the cache, without
contacting the server.If the object is not cached, the proxy retrieves the object from the server, returns it to you and caches a copy of this webpage for future requests.In case of any further requests for the same, the proxy must utilize the “If Modified Since” header to check if any updates have been made, and if not, then serve the response from the cache.
