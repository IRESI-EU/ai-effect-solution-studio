"""Focused checks for the opt-in harness, not provider/runtime acceptance."""
import socket

import pytest

from deploy.composition_walkthrough.harness import deny_network


@pytest.mark.parametrize("method", ["connect", "connect_ex", "create_connection"])
def test_outbound_connections_are_denied_before_network_access(monkeypatch, method):
    # Register original values for automatic restoration of this isolated test.
    monkeypatch.setattr(socket.socket, "connect", socket.socket.connect)
    monkeypatch.setattr(socket.socket, "connect_ex", socket.socket.connect_ex)
    monkeypatch.setattr(socket, "create_connection", socket.create_connection)
    deny_network()
    with pytest.raises(RuntimeError, match="outbound network prohibited"):
        if method == "create_connection":
            socket.create_connection(("203.0.113.1",443))
        else:
            with socket.socket() as connection:
                getattr(connection,method)(("203.0.113.1",443))
    first, second = socket.socketpair()
    first.close(); second.close()
