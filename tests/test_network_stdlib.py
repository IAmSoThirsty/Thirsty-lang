"""Real loopback network behavior and bounded failure handling; no external IO."""

import socket

import pytest

from utf.thirsty_lang import module_system as ms


@pytest.fixture
def network():
    module = ms.STDLIB_MODULES["thirst::net"]()
    handles = []
    yield module, handles
    for handle in reversed(handles):
        module["close"](handle)


def connected_pair(network):
    module, handles = network
    server = module["tcp_listen"](0, "127.0.0.1", 4, 0.5)
    handles.append(server["handle"])
    client = module["tcp_connect"]("127.0.0.1", server["port"], 0.5)
    handles.append(client["handle"])
    accepted = module["tcp_accept"](server["handle"])
    handles.append(accepted["handle"])
    return module, server, client, accepted


def receive_exact(module, handle, size):
    result = []
    while len(result) < size:
        chunk = module["tcp_receive"](handle, size - len(result))
        assert not chunk["eof"]
        result.extend(chunk["data"])
    return result


def test_tcp_connect_accept_send_receive_and_close(network):
    module, server, client, accepted = connected_pair(network)
    assert server["listening"] is True and server["port"] > 0
    assert client["connected"] is True and accepted["connected"] is True
    assert len({server["handle"], client["handle"], accepted["handle"]}) == 3
    text = "water \u03a9"
    assert module["tcp_send"](client["handle"], text) == {"sent": len(text.encode())}
    assert (
        bytes(receive_exact(module, accepted["handle"], len(text.encode())))
        == text.encode()
    )
    binary = [0, 255, 128, 10]
    assert module["tcp_send"](accepted["handle"], binary) == {"sent": 4}
    assert receive_exact(module, client["handle"], 4) == binary
    assert module["tcp_send"](accepted["handle"], b"bytes") == {"sent": 5}
    assert bytes(receive_exact(module, client["handle"], 5)) == b"bytes"
    assert module["close"](client["handle"])
    assert module["tcp_receive"](accepted["handle"]) == {
        "data": [],
        "received": 0,
        "eof": True,
    }
    assert module["close"](client["handle"]) is False
    with pytest.raises(ValueError, match="closed"):
        module["tcp_send"](client["handle"], "x")


def test_receive_does_not_corrupt_partial_utf8(network):
    module, _, client, accepted = connected_pair(network)
    module["tcp_send"](client["handle"], "\u03a9")
    first = module["tcp_receive"](accepted["handle"], 1)["data"]
    second = module["tcp_receive"](accepted["handle"], 1)["data"]
    assert bytes(first + second).decode("utf-8") == "\u03a9"


def test_tcp_timeout_is_error_and_connection_remains_usable(network):
    module, _, client, accepted = connected_pair(network)
    with pytest.raises(TimeoutError):
        module["tcp_receive"](accepted["handle"], 1)
    module["tcp_send"](client["handle"], "x")
    assert module["tcp_receive"](accepted["handle"], 1)["data"] == [120]


def test_accept_timeout_and_duplicate_bind_are_errors(network):
    module, handles = network
    server = module["tcp_listen"](0, "127.0.0.1", 1, 0.01)
    handles.append(server["handle"])
    with pytest.raises(TimeoutError):
        module["tcp_accept"](server["handle"])
    with pytest.raises(OSError):
        module["tcp_listen"](server["port"])


def test_failed_connect_never_returns_connected(network):
    module, _ = network
    # Keep an ephemeral port bound but not listening, so it cannot be claimed
    # by another local process between selecting the port and connecting.
    with socket.socket() as reserved:
        reserved.bind(("127.0.0.1", 0))
        with pytest.raises(OSError):
            module["tcp_connect"]("127.0.0.1", reserved.getsockname()[1], 0.05)


def test_udp_real_datagrams_and_zero_length(network):
    module, handles = network
    receiver = module["udp_bind"](0, "127.0.0.1", 0.5)
    handles.append(receiver["handle"])
    for payload in ("message", [0, 255], b"raw bytes", ""):
        expected = payload.encode() if isinstance(payload, str) else bytes(payload)
        sent = module["udp_send"]("127.0.0.1", receiver["port"], payload)
        assert sent["sent"] == len(expected)
        received = module["udp_receive"](receiver["handle"])
        assert bytes(received["data"]) == expected
        assert received["received"] == len(expected)
        assert received["host"] == "127.0.0.1" and received["port"] > 0


def test_udp_truncation_and_timeout_are_explicit(network):
    module, handles = network
    receiver = module["udp_bind"](0, "127.0.0.1", 0.01)
    handles.append(receiver["handle"])
    module["udp_send"]("127.0.0.1", receiver["port"], "too much")
    with pytest.raises((ValueError, OSError)):
        module["udp_receive"](receiver["handle"], 2)
    with pytest.raises(TimeoutError):
        module["udp_receive"](receiver["handle"])


@pytest.mark.parametrize("timeout", [0, -1, 61, True, "1", float("nan"), float("inf")])
def test_invalid_timeouts_fail_before_socket_creation(network, monkeypatch, timeout):
    module, _ = network
    monkeypatch.setattr(socket, "socket", lambda *args: pytest.fail("socket created"))
    with pytest.raises(ValueError):
        module["tcp_connect"]("127.0.0.1", 1, timeout)


@pytest.mark.parametrize(
    "host,port",
    [
        ("example.com", 80),
        ("not-an-ip", 1),
        ("127.0.0.1", True),
        ("127.0.0.1", 65536),
        ("127.0.0.1", 0),
        (7, 1),
    ],
)
def test_invalid_destinations_fail_before_socket_creation(
    network, monkeypatch, host, port
):
    module, _ = network
    monkeypatch.setattr(socket, "socket", lambda *args: pytest.fail("socket created"))
    with pytest.raises((TypeError, ValueError)):
        module["udp_send"](host, port, "x")


@pytest.mark.parametrize(
    "payload",
    [
        [True],
        [-1],
        [256],
        [1.5],
        {"unsupported": "dictionary"},
        "x" * 1048577,
        [0] * 1048577,
        "\u03a9" * 524289,
    ],
    ids=[
        "bool",
        "negative",
        "large_byte",
        "float",
        "dictionary",
        "large_text",
        "large_array",
        "large_utf8",
    ],
)
def test_invalid_tcp_payloads_are_rejected(network, payload):
    module, _ = network
    with pytest.raises((TypeError, ValueError)):
        module["tcp_send"]("unused", payload)


def test_udp_limit_and_handle_type_checks(network):
    module, handles = network
    listener = module["tcp_listen"](0)
    handles.append(listener["handle"])
    with pytest.raises(ValueError, match="tcp handle"):
        module["tcp_send"](listener["handle"], "x")
    with pytest.raises(ValueError):
        module["udp_send"]("127.0.0.1", 1, "x" * 65508)
    with pytest.raises(TypeError):
        module["tcp_receive"](1)
    with pytest.raises(TypeError):
        module["close"](1)
    for size in (0, -1, True, 1048577):
        with pytest.raises(ValueError):
            module["tcp_receive"](listener["handle"], size)
    for size in (0, True, 65508):
        with pytest.raises(ValueError):
            module["udp_receive"](listener["handle"], size)


def test_every_network_callable_has_capability_metadata():
    assert set(ms.STDLIB_MODULES["thirst::net"]()) == set(
        ms.SENSITIVE_STDLIB_CAPABILITIES["thirst::net"]
    )
    assert set(ms.SENSITIVE_STDLIB_CAPABILITIES["thirst::net"].values()) == {"network"}


def test_network_handle_budget_preserves_existing_handles(network):
    module, handles = network
    for _ in range(256):
        handles.append(module["udp_bind"](0)["handle"])
    with pytest.raises(OSError, match="handle limit"):
        module["udp_bind"](0)
    assert module["close"](handles.pop())
    handles.append(module["udp_bind"](0)["handle"])


def test_invalid_backlog_does_not_create_listener(network):
    module, _ = network
    for backlog in (0, 129, True):
        with pytest.raises(ValueError, match="backlog"):
            module["tcp_listen"](0, "127.0.0.1", backlog)


def test_wait_budget_exhaustion_skips_socket_io(network, monkeypatch):
    module, _, client, accepted = connected_pair(network)
    readings = iter((100.0, 101.0))
    with monkeypatch.context() as patch:
        patch.setattr(ms.time, "monotonic", lambda: next(readings))
        with pytest.raises(TimeoutError, match="deadline expired"):
            module["tcp_receive"](accepted["handle"], 1)
    # Deadline denial leaves both the handle and its timeout usable.
    module["tcp_send"](client["handle"], "x")
    assert module["tcp_receive"](accepted["handle"], 1)["data"] == [120]
