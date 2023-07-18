"""
picklerpc Server
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import logging
import pickle
import socket
import time

from contextlib import closing


LOG = logging.getLogger(__name__)


class PickleRpcServer:
    """Pickle RPC Server. Subclass, add your own methods, and watch it go!"""

    def __init__(self, host="0.0.0.0", port=62000, protocol=None):
        """
        Prepare a PickleRpcServer instance for use.

        Args:
            host (str): Hostname to bind to. Defaults to empty string (all
                hosts).
            port (int): Port to bind to. Defaults to 62000.
        """
        self.svr_fqdn = socket.getfqdn()
        self.svr_host = host
        self.svr_port = int(port)
        self.svr_protocol = protocol
        self.svr_running = False

    def __str__(self):
        """Displays detailed information with str()."""
        return "{} Details\n{}\nExternal Methods\n{}".format(
            self.__class__.__name__,
            "\n".join(["  {:10}: {}".format(k, v) for k, v in self._dict.items()]),
            "\n".join("  {}".format(m) for m in self._ext_methods),
        )

    @property
    def _dict(self):
        """Dictionary of non-protected properties."""
        return {
            k: getattr(self, k)
            for k in dir(self)
            if not k.startswith("_") and not callable(getattr(self, k))
        }

    @property
    def _ext_methods(self):
        """
        List of methods that should be externally accessible (public, and not
        run()).
        """
        return [
            (i, getattr(self, i).__doc__)
            for i in dir(self)
            if i not in ["run"] and not i.startswith("_") and callable(getattr(self, i))
        ]

    def _get_result(self, command=None, args=None, kwargs=None):
        """
        Get a result from a local method.

        Args:
            command (str): Method name to call.
            args (tuple): Tuple of positional arguments.
            kwargs (dict): Dict of keyword arguments.

        Returns (object):
            Returns whatever the method returns, or an exception object if an
            exception occurs.
        """
        LOG.info(
            "Getting: %s(%s)",
            command,
            ", ".join(
                [repr(a) for a in args]
                + ["{}={}".format(k, repr(v)) for k, v in kwargs.items()]
            ),
        )
        try:
            member = getattr(self, command)
            return member(*args, **kwargs) if callable(member) else member
        except Exception as error:
            LOG.error("ERROR getting attribute %s", command, exc_info=True)
            return error

    def run(self, timeout=None):
        """
        Run the server.

        Args:
            timeout (int): Number of seconds to run for. Defaults to None (
                run indefinitely).
        """
        LOG.debug("Running %r with timeout=%r", self, timeout)

        # Set the stopper.
        stop_time = time.time() + timeout if timeout else None

        def stopper():
            return bool(time.time() < stop_time) if timeout else False

        # Open the socket for use.
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)
            LOG.info("Listening on %s:%i", self.svr_host, self.svr_port)
            sock.bind((self.svr_host, self.svr_port))
            self.svr_running = True
            # Loop
            while stopper():
                try:
                    try:
                        sock.listen(0)
                        conn, addr = sock.accept()
                        LOG.debug("--- Got something ---")
                        with closing(conn):
                            data = conn.recv(4096)
                            LOG.debug("Received data from %s:\n\n%r\n", addr, data)
                            payload = pickle.loads(data)
                            LOG.debug("Received %r", payload)
                            val = self._get_result(**payload)
                            LOG.debug("Packaging %s for return", type(val))
                            retval = pickle.dumps(val, protocol=self.svr_protocol)
                            LOG.debug("Sending:\n\n%r\n", retval)
                            conn.sendall(retval)
                    except socket.timeout:
                        pass
                    except socket.error:
                        LOG.error("ERROR getting or sending data.", exc_info=True)
                except KeyboardInterrupt:
                    LOG.debug("Stopping.")
                    break
            LOG.info("Stopped listening on %s:%i", self.svr_host, self.svr_port)
            self.svr_running = False
