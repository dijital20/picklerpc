"""Client class which can be initialized to connect to a server."""

import logging
import pickle
import socket
from collections.abc import Callable
from contextlib import closing
from typing import Any

LOG = logging.getLogger(__name__)


class PickleRpcClient:
    """A client for PickleRpcServer. Use the client to connect to a server."""

    def __init__(
        self: "PickleRpcClient",
        server: str,
        port: int,
        protocol: int | None = None,
    ) -> None:
        """Prepare a PickleRpcClient instance for use.

        Args:
            server: Hostname or IP address to connect to.
            port: Port to connect to.
            protocol: Pickle protocol to use.
        """
        LOG.debug(locals())
        self.cli_server = server
        self.cli_port = port
        self.cli_protocol = protocol
        # Create socket
        self._setup_obj()

    def _setup_obj(self: "PickleRpcClient") -> None:
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

    def _method_call(
        self: "PickleRpcClient",
        method_name: str,
        docstring: str = "",
    ) -> Callable:
        """Wrap a remote method on this object.

        Args:
            method_name (str): Name of the method.
            docstring (str): Docstring of the remote method. Defaults to
                empty string.
            called (bool): Is this a callable method or a property?

        Returns (func):
            Wrapped method.
        """

        def wrapped_method(*args: Any, **kwargs: Any) -> Any:  # noqa: ANN401
            """Call _send_command with the arguments.

            Args:
                *args: Positional args.
                **kwargs: Keyword args.
            """
            return self._send_command(method_name, *args, **kwargs)

        wrapped_method.__doc__ = docstring
        return wrapped_method

    def _send_command(
        self: "PickleRpcClient",
        command: str,
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> Any:  # noqa: ANN401
        """Send a command to the PickleRpcServer.

        Args:
            command: Method to call.
            *args: Tuple of positional arguments.
            **kwargs: Dict of keyword arguments.

        Returns:
            Whatever value the remote method returned.

        Raises:
            Exception: If the method returned an exception object, raise it.
        """
        LOG.debug(locals())
        LOG.debug(
            "Remote calling %s(%s) on %s:%i",
            command,
            ", ".join(
                [repr(a) for a in args] + [f"{k}={v!r}" for k, v in kwargs.items()],
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
