"""
picklerpc Client
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import logging
import pickle
import socket

from contextlib import closing

LOG = logging.getLogger(__name__)


class PickleRpcClient:
    """A client for PickleRpcServer. Use the client to connect to a server."""

    def __init__(self, server, port, protocol=None):
        """
        Prepare a PickleRpcClient instance for use.

        Args:
            server (str): Hostname or IP address to connect to.
            port (int): Port to connect to.
        """
        LOG.debug(locals())
        self.cli_server = server
        self.cli_port = port
        self.cli_protocol = protocol
        # Create socket
        self._setup_obj()

    def _setup_obj(self):
        """Dynamically assign the methods from the server to this instance."""
        LOG.debug(locals())
        # Register remote methods
        methods = self._send_command("_ext_methods")
        for method, docstring in methods:
            if method in dir(self):
                LOG.warning("Method already exists: %s", method)
            else:
                LOG.debug("Creating method: %s", method)
                setattr(self, method, self._method_call(method, docstring))

    def _method_call(self, method_name, docstring=""):
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
        LOG.debug(locals())
        LOG.debug(
            "Remote calling %s(%s) on %s:%i",
            command,
            ", ".join(
                [repr(a) for a in args]
                + ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
            ),
            self.cli_server,
            self.cli_port,
        )
        payload = {"command": command, "args": args, "kwargs": kwargs}
        payload = pickle.dumps(payload, protocol=self.cli_protocol)
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            LOG.debug("Connecting to %s:%i", self.cli_server, self.cli_port)
            sock.connect((self.cli_server, self.cli_port))
            send_cmd = payload
            LOG.debug("Sending:\n\n%r\n", send_cmd)
            sock.sendall(send_cmd)
            data = sock.recv(4096)
            LOG.debug("Received:\n\n%r\n", data)
        # Process the data
        o_data = pickle.loads(data)
        LOG.debug("Loaded %s: %r", type(o_data), o_data)
        # Raise if this is an exception.
        if isinstance(o_data, Exception):
            raise o_data
        return o_data
