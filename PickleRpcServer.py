"""
picklerpc Server
Author: Josh Schneider (josh.schneider@gmail.com)
"""

import datetime
import logging
import pickle
import socket

from contextlib import closing


def time_from_now(**kwargs):
    """
    Return a datetime object from the future!!

    Args:
        **kwargs (dict): Keyword arguments, which will be passed to
            timedelta().

    Returns (datetime):
        Datetime object from the specified point in the future. No Delorean
        needed.
    """
    return datetime.datetime.now() + datetime.timedelta(**kwargs)


class PickleRpcServer(object):
    """Pickle RPC Server. Subclass, add your own methods, and watch it go!"""
    def __init__(self, host='', port=62000):
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
        self._log.debug('Initialized.')

    def __str__(self):
        """Displays detailed information with str()."""
        return '{} Details\n{}\nExternal Methods\n{}'.format(
            self.__class__.__name__,
            '\n'.join([
                '  {:10}: {}'.format(k, v) for k, v in self._dict.items()
            ]),
            '\n'.join('  {}'.format(m) for m in self._ext_methods),
        )

    @property
    def _log(self):
        """Logger."""
        return logging.getLogger('picklerpc.PickleRpcServer')

    @property
    def _dict(self):
        """Dictionary of non-protected properties."""
        return {
            k: getattr(self, k) for k in dir(self)
            if not k.startswith('_')
               and not callable(getattr(self, k))
        }

    @property
    def _ext_methods(self):
        """
        List of methods that should be externally accessible (public, and not
        run()).
        """
        return [
            (i, getattr(self, i).__doc__) for i in dir(self)
            if i not in ['run']
               and not i.startswith('_')
               and callable(getattr(self, i))
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
        self._log.debug(locals())
        if hasattr(self, command):
            if callable(getattr(self, command)):
                try:
                    self._log.debug('Method found: {}'.format(command))
                    return getattr(self, command)(*args, **kwargs)
                except Exception as e:
                    self._log.error('Got error: {}'.format(e))
                    return e
            else:
                try:
                    self._log.debug('Property found: {}'.format(command))
                    return getattr(self, command)
                except Exception as e:
                    self._log.error('Got error: {}'.format(e))
                    return e
        else:
            self._log.debug('Not found: {}'.format(command))
            return AttributeError('Unable to find member: {}'.format(command))

    def run(self, timeout=None):
        """
        Run the server.

        Args:
            timeout (int): Number of seconds to run for. Defaults to None (
                run indefinitely).
        """
        self._log.debug(locals())
        if timeout:
            stop_time = time_from_now(seconds=timeout)
            self._log.info('Running until {}'.format(stop_time))
            stopper = lambda: bool(datetime.datetime.now() < stop_time)
        else:
            self._log.info('Running indefinitely')
            stopper = lambda: False
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            s.settimeout(5)
            self._log.info('Starting listening on {}:{}'.format(
                self.svr_host, self.svr_port))
            s.bind((self.svr_host, self.svr_port))
            while stopper():
                try:
                    try:
                        r = s.listen(0)
                        c, a = s.accept()
                        self._log.debug('Received from: {}'.format(a))
                        with closing(c):
                            data = c.recv(4096)
                            self._log.debug('Received data: {}'.format(repr(data)))
                            payload = pickle.loads(data)
                            self._log.info('Received: {}'.format(payload))
                            val = self._get_result(**payload)
                            self._log.debug('Packaging {} for return: {}'.format(
                                type(val), repr(val)))
                            retval = pickle.dumps(val)
                            self._log.debug('Sending: {}'.format(repr(retval)))
                            c.sendall(retval)
                    except socket.error as e:
                        self._log.debug('Received nothing ({}).'.format(e))
                except KeyboardInterrupt:
                    self._log.debug('Stopping.')
                    break
            self._log.info('Stopped listening on {}:{}'.format(
                self.svr_host, self.svr_port))


if __name__ == '__main__':
    # Init logging
    log = logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(name)s.%(funcName)s %(msg)s',
    )

    # Create a new subclass with a ping method.
    class Pinger(PickleRpcServer):
        def __init__(self):
            """Prepare a Pinger for use."""
            super(Pinger, self).__init__()
            self.name = 'foo'

        def ping(self):
            """Returns PONG, and just for testing."""
            return 'PONG'

        def raise_exception(self):
            """Just raises an exception."""
            raise NotImplementedError('Foo!')

    # Start the server and run it for 2 minutes.
    j = Pinger()
    logging.info('\n' + str(j))
    j.run(timeout=120)
