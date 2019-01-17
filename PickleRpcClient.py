"""
picklerpc Client
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import logging
import pickle
import socket

from contextlib import closing


class PickleRpcClient:
    """A client for PickleRpcServer. Use the client to connect to a server."""

    def __init__(self, server, port, protocol=None):
        """
        Prepare a PickleRpcClient instance for use.

        Args:
            server (str): Hostname or IP address to connect to.
            port (int): Port to connect to.
        """
        self._log.debug(locals())
        self.cli_server = server
        self.cli_port = port
        self.cli_protocol = protocol
        # Create socket
        self._setup_obj()

    @property
    def _log(self):
        """Logger."""
        return logging.getLogger('picklerpc.PickleRpcClient')

    def _setup_obj(self):
        """Dynamically assign the methods from the server to this instance."""
        self._log.debug(locals())
        # Register remote methods
        methods = self._send_command('_ext_methods')
        for method, docstring in methods:
            if method in dir(self):
                self._log.warning('Method already exists: %s', method)
            else:
                self._log.debug('Creating method: %s', method)
                setattr(self, method, self._method_call(method, docstring))

    def _method_call(self, method_name, docstring=''):
        """
        Wrap a remote method on this object, so we can call it like we'd call
        it on the remote object. Sets the docstring in the process.

        Args:
            method_name (str): Name of the method.
            docstring (str): Docstring of the remote method. Defaults to
                empty string.
            called (bool): Is this a callable method or a property?

        Returns (func):
            Wrapped method.
        """
        wrapped_method = lambda *args, **kwargs: self._send_command(method_name, *args, **kwargs)
        wrapped_method.__doc__ = docstring
        return wrapped_method

    def _send_command(self, command, *args, **kwargs):
        """
        Send a command to the PickleRpcServer.

        Args:
            command (str): Method to call.
            *args (tuple): Tuple of positional arguments.
            **kwargs (dict): Dict of keyword arguments.

        Returns (object):
            Whatever value the remote method returned.

        Raises:
            Exception: If the method returned an exception object, raise it.
        """
        self._log.debug(locals())
        self._log.debug(
            'Remote calling %s(%s) on %s:%i',
            command,
            ', '.join([repr(a) for a in args] +
                      ['{}={}'.format(k, repr(v)) for k, v in kwargs.items()]),
            self.cli_server,
            self.cli_port,
        )
        payload = {'command': command, 'args': args, 'kwargs': kwargs}
        payload = pickle.dumps(payload, protocol=self.cli_protocol)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            self._log.debug('Connecting to %s:%i', self.cli_server,
                            self.cli_port)
            sock.connect((self.cli_server, self.cli_port))
            send_cmd = payload
            self._log.debug('Sending:\n\n%r\n', send_cmd)
            sock.sendall(send_cmd)
            data = sock.recv(4096)
            self._log.debug('Received:\n\n%r\n', data)
        # Process the data
        o_data = pickle.loads(data)
        self._log.debug('Loaded %s: %r', type(o_data), o_data)
        # Raise if this is an exception.
        if isinstance(o_data, Exception):
            raise o_data
        return o_data


if __name__ == '__main__':
    # Setup logging.
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)s.%(funcName)s %(message)s')

    # Setup client.
    client = PickleRpcClient('127.0.0.1', 62000, protocol=2)
    # Print the method name and docstring of each method.
    for item in [m for m in dir(client) if not m.startswith('_')]:
        logging.info('%s\nMethod: %s()\n\n%s\n', '-' * 80, item,
                     getattr(client, item).__doc__)
    # Call the ping() method and print its output.
    logging.info('ping()')
    logging.info(client.ping())
    # Call the echo() method and print its output.
    logging.info('echo()')
    logging.info(client.echo('Marco'))
    # Call story() with keyword arguments.add()
    logging.info('story()')
    logging.info(client.story(effect='delicious', food='cake'))
    # Call the raise_exception method.
    logging.info('raise_exception()')
    try:
        logging.info(client.raise_exception())
    except Exception:
        logging.info('Got an exception', exc_info=True)
    # Call the pong() method (which shouldn't exist...)
    logging.info('pong()')
    try:
        logging.info(client.parrot())
    except Exception:
        logging.info('Got an exception', exc_info=True)
    # Try explicitly calling pong() on the other end.add()
    logging.info('pong() [via _send_command()]')
    try:
        client._send_command('parrot')
    except Exception:
        logging.info('Got an exception', exc_info=True)
