"""Remote procedure call library using Pickle and TCP."""

from picklerpc.client import PickleRpcClient
from picklerpc.server import PickleRpcServer

__all__ = ["PickleRpcClient", "PickleRpcServer"]
