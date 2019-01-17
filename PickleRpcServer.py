"""
picklerpc Server
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import logging
import pickle
import socket
import time
import traceback

from contextlib import closing


class PickleRpcServer:
    """Pickle RPC Server. Subclass, add your own methods, and watch it go!"""

    def __init__(self, host='0.0.0.0', port=62000, protocol=None):
        """
        Prepare a PickleRpcServer instance for use.

        Args:
            host (str): Hostname to bind to. Defaults to empty string (all
                hosts).
            port (int): Port to bind to. Defaults to 62000.
        """
        self._log.debug(locals())
        self.svr_fqdn = socket.getfqdn()
        self.svr_host = host
        self.svr_port = int(port)
        self.svr_protocol = protocol
        self._log.debug('Initialized.')

    def __str__(self):
        """Displays detailed information with str()."""
        return '{} Details\n{}\nExternal Methods\n{}'.format(
            self.__class__.__name__,
            '\n'.join(
                ['  {:10}: {}'.format(k, v) for k, v in self._dict.items()]),
            '\n'.join('  {}'.format(m) for m in self._ext_methods),
        )

    @property
    def _log(self):
        """Logger."""
        return logging.getLogger('picklerpc.{}'.format(self.__class__.__name__))

    @property
    def _dict(self):
        """Dictionary of non-protected properties."""
        return {
            k: getattr(self, k)
            for k in dir(self)
            if not k.startswith('_') and not callable(getattr(self, k))
        }

    @property
    def _ext_methods(self):
        """
        List of methods that should be externally accessible (public, and not
        run()).
        """
        return [(i, getattr(self, i).__doc__)
                for i in dir(self)
                if i not in ['run'] and not i.startswith('_') and
                callable(getattr(self, i))]

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
        self._log.info(
            'Getting: %s(%s)', command,
            ', '.join([repr(a) for a in args] +
                      ['{}={}'.format(k, repr(v)) for k, v in kwargs.items()]))
        try:
            member = getattr(self, command)
            return member(*args, **kwargs) if callable(member) else member
        except Exception as error:
            self._log.error(
                'ERROR getting attribute %s', command, exc_info=True)
            return error

    def run(self, timeout=None):
        """
        Run the server.

        Args:
            timeout (int): Number of seconds to run for. Defaults to None (
                run indefinitely).
        """
        self._log.debug(locals())

        # Set the stopper.
        stop_time = time.time() + timeout if timeout else None
        stopper = lambda: bool(time.time() < stop_time) if timeout else False

        # Open the socket for use.
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)
            self._log.info('Listening on %s:%i', self.svr_host, self.svr_port)
            sock.bind((self.svr_host, self.svr_port))
            # Loop
            while stopper():
                try:
                    try:
                        sock.listen(0)
                        conn, addr = sock.accept()
                        self._log.debug('--- Got something ---')
                        with closing(conn):
                            data = conn.recv(4096)
                            self._log.debug('Received data from %s:\n\n%r\n',
                                            addr, data)
                            payload = pickle.loads(data)
                            self._log.debug('Received %r', payload)
                            val = self._get_result(**payload)
                            self._log.debug('Packaging %s for return',
                                            type(val))
                            retval = pickle.dumps(
                                val, protocol=self.svr_protocol)
                            self._log.debug('Sending:\n\n%r\n', retval)
                            conn.sendall(retval)
                    except socket.timeout:
                        pass
                    except socket.error:
                        self._log.error(
                            'ERROR getting or sending data.', exc_info=True)
                except KeyboardInterrupt:
                    self._log.debug('Stopping.')
                    break
            self._log.info('Stopped listening on %s:%i', self.svr_host,
                           self.svr_port)


if __name__ == '__main__':
    # Init logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s %(name)s.%(funcName)s %(message)s')

    # Create a new subclass with a ping method.
    class Pinger(PickleRpcServer):
        """Example class"""

        def __init__(self, *args, **kwargs):
            """Prepare a Pinger for use."""
            super(Pinger, self).__init__(*args, **kwargs)
            self.name = 'foo'

        def ping(self):
            """
            Returns PONG, and just for testing.

            Returns (str):
                PONG.
            """
            return 'PONG'

        def echo(self, message):
            """
            Responds back to the caller.

            Args:
                message (str): Message to receive.
            
            Returns (str):
                Response.
            """
            self._log.debug('Hey, we got a message: %r', message)
            return 'I received: {}'.format(message)

        def story(self, food='cheese', effect='moldy'):
            """
            Responds back to the caller with food.

            Args:
                food (str): Food to work with.
                effect (str): What food does.

            Returns (str):
                Response.
            """
            self._log.debug('We got food=%s and effect=%s', food, effect)
            return 'The {} is {}'.format(food, effect)

        def raise_exception(self):
            """
            Just raises an exception.

            Raises:
                NotImplementedError: Just because.
            """
            raise NotImplementedError('Foo!')

    # Start the server and run it for 2 minutes.
    j = Pinger(protocol=2)
    logging.info('\n%s', j)
    j.run(timeout=120)
