# PickleRPC

The Python standard library does include the XmlRPCClient and XmlRPCServer, and it's good. That said, I've never been keen on 2 aspects of it:

- You have to register the methods you want to externalize.
- Data is serialized to/from XML, so you're limited on what types you can send.

To that end, I started looking at the idea of writing my own RPC client and server that would be a little bit simpler and easier to use.

## PickleRPCServer

First up is the server object. Use it by subclassing it and adding your own methods. When you're ready, instantiate your new object, and call the run method. The server will bind to a TCP port, and listen for clients to connect.

```python
from picklerpc import PickleRPCServer


class MyAwesomeClass(PickleRPCServer):
    def ping(self):
        """PONG back"""
        return 'PONG'

    def raise_error(self):
        """Raise an error"""
        raise NotImplementedError('Not today!')



if __name__ == '__main__':
    my_class = MyAwesomeClass(port=64200)
    my_class.run()  # Run the server indefinitely. Use timeout=<int> to specify a timeout.
```

## PickleRPCClient

The client is just as easy. Instantiate the object with the host and port, and it will contact the server to get the list of available methods. The client object automagically populates the object with method calls to the server object, complete with docstring, so you can `dir()` the methods or list their `__doc__` items, and they will appear. The client functions as a mirror of the Server object.

```python
from picklerpc import PickleRPCClient


client = PickleRPCClient(host='localhost', port=64200)

print(dir(client))
# -> [...'cli_port', 'cli_server', 'ping', 'raise_error'...]

print(getattr(client, 'ping').__doc__)
# -> 'PONG back'

dir(client.ping())
# -> 'PONG'
```

All data interchange between the targets is handled via Pickle, so any data type that can be pickled, can be passed back and forth. Exception objects passed back are detected and raised, while data is returned.

PickleRPC works with Python 3.10 and up.