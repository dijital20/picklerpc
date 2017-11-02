"""
picklerpc Client
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import logging
import pickle
import socket

from contextlib import closing


class PickleRpcClient(object):
    """A client for PickleRpcServer. Use the client to connect to a server."""
    def __init__(self, server, port):
        """
        Prepare a PickleRpcClient instance for use.

        Args:
            server (str): Hostname or IP address to connect to.
            port (int): Port to connect to.
        """
        self._log.debug(locals())
        self.cli_server = server
        self.cli_port = port
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
                self._log.warning('Member exists: {}'.format(method))
                continue
            self._log.debug('Creating method: {}'.format(method))
            setattr(self, method, self._method_call(method, docstring))

    def _method_call(self, method_name, docstring=''):
        """
        Wrap a remote method on this object, so we can call it like we'd call
        it on the remote object. Sets the docstring in the process.

        Args:
            method_name (str): Name of the method.
            docstring (str): Docstring of the remote method. Defaults to
                empty string.

        Returns (func):
            Wrapped method.
        """
        def wrapped_method(*args, **kwargs):
            return self._send_command(method_name, *args, **kwargs)

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
        self._log.debug('Remote calling {}({}) on {}:{}'.format(
            command,
            ', '.join(
                list(args) +
                ['{}={}'.format(k, v) for k, v in kwargs.items()]
            ),
            self.cli_server,
            self.cli_port,
        ))
        payload = {'command': command, 'args': args, 'kwargs': kwargs}
        payload = pickle.dumps(payload)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            self._log.debug('Connecting to {}:{}'.format(
                self.cli_server, self.cli_port))
            s.connect((self.cli_server, self.cli_port))
            send_cmd = payload
            self._log.debug('Sending: {}'.format(send_cmd))
            s.sendall(send_cmd)
            data = s.recv(4096)
            self._log.debug('Received: {}'.format(data))
        # Process the data
        o_data = pickle.loads(data)
        self._log.debug('Loaded {}: {}'.format(type(o_data), repr(o_data)))
        if isinstance(o_data, Exception):
            raise o_data
        return o_data


if __name__ == '__main__':
    # Setup logging.
    logging.basicConfig(
        level=logging.INFO,
        format='%(msg)s'
    )

    # Setup client.
    c = PickleRpcClient('127.0.0.1', 62000)
    # Print the method name and docstring of each method.
    for item in [m for m in dir(c) if not m.startswith('_')]:
        logging.info('{}\nMethod: {}()\n\n{}\n'.format(
            '-' * 80, item, getattr(c, item).__doc__))
    # Call the ping() method and print its output.
    logging.info(c.ping())
    # Call the raise_exception method.
    logging.info(c.raise_exception())
    # Call the pong() method (which shouldn't exist...)
    logging.info(c.pong())
