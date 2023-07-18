import logging
import time
from threading import Thread

import pytest
from picklerpc import PickleRpcClient, PickleRpcServer


log = logging.getLogger()


@pytest.fixture
def client():
    return PickleRpcClient("127.0.0.1", 62000, protocol=2)


@pytest.fixture
def server():
    # Create a new subclass with a ping method.
    class Pinger(PickleRpcServer):
        """Example class"""

        def __init__(self, host="0.0.0.0", port=62000, protocol=None):
            """Prepare a Pinger for use."""
            super(Pinger, self).__init__(host=host, port=port, protocol=protocol)
            self.name = "foo"

        def ping(self):
            """
            Returns PONG, and just for testing.

            Returns (str):
                PONG.
            """
            return "PONG"

        def echo(self, message):
            """
            Responds back to the caller.

            Args:
                message (str): Message to receive.

            Returns (str):
                Response.
            """
            self._log.debug("Hey, we got a message: %r", message)
            return "I received: {}".format(message)

        def story(self, food="cheese", effect="moldy"):
            """
            Responds back to the caller with food.

            Args:
                food (str): Food to work with.
                effect (str): What food does.

            Returns (str):
                Response.
            """
            self._log.debug("We got food=%s and effect=%s", food, effect)
            return "The {} is {}".format(food, effect)

        def raise_exception(self):
            """
            Just raises an exception.

            Raises:
                NotImplementedError: Just because.
            """
            raise NotImplementedError("Foo!")

    # Start the server and run it for 2 minutes.
    return Pinger(protocol=2)


def test_server_init(server):
    assert server


def test_server_running(server):
    def waiter():
        stop_at = time.time() + 10
        log.info("Looking for svr_running for at least 10 seconds.")
        while time.time() < stop_at:
            if server.svr_running:
                log.info("Found it.")
                return True
            time.sleep(0.1)
        else:
            log.info("Not found in time.")
            return False

    assert not server.svr_running
    waiter = Thread(target=waiter)
    waiter.start()
    server.run(1)
    assert waiter
    assert not server.svr_running
