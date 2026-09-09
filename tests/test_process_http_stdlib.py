"""Explicit HTTP/process failures and limits, with loopback or direct children only."""

import json
import os
import subprocess
import sys
import threading
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from utf.thirsty_lang import module_system as ms


@pytest.fixture
def http_server():
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            if self.path == "/redirect":
                self.send_response(302)
                self.send_header("Location", "/target")
                self.end_headers()
                return
            if self.path == "/missing":
                self.send_error(404)
                return
            data = b"x" * 32 if self.path == "/large" else b"hello"
            if self.path == "/invalid":
                data = b"\xff"
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            data = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            body = json.dumps(
                {
                    "method": self.command,
                    "body": data.decode("utf-8"),
                    "content_type": self.headers.get("Content-Type"),
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        do_PUT = do_POST
        do_DELETE = do_GET

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    worker = threading.Thread(
        target=lambda: server.serve_forever(poll_interval=0.01), daemon=True
    )
    worker.start()
    yield f"http://127.0.0.1:{server.server_port}", requests
    server.shutdown()
    server.server_close()
    worker.join(timeout=1)


def test_http_real_success_and_false_json_payloads(http_server):
    url, _ = http_server
    http = ms.STDLIB_MODULES["thirst::http"]()
    assert http["get"](url, 1, 5) == "hello"
    assert http["delete"](url, 1, 5) == "hello"
    for value in (False, 0, [], {}, "", None):
        for method in ("post", "put"):
            response = json.loads(http[method](url, value, 1, 1024))
            assert response["method"] == method.upper()
            assert response["body"] == ("" if value is None else json.dumps(value))
            assert response["content_type"] == "application/json; charset=utf-8"


def test_http_limit_status_redirect_and_decoding_failures(http_server):
    url, requests = http_server
    http = ms.STDLIB_MODULES["thirst::http"]()
    with pytest.raises(ValueError, match="exceeds max_bytes"):
        http["get"](url + "/large", 1, 4)
    with pytest.raises(urllib.error.HTTPError) as missing:
        http["get"](url + "/missing")
    assert missing.value.code == 404
    with pytest.raises(urllib.error.HTTPError) as redirect:
        http["get"](url + "/redirect")
    assert redirect.value.code == 302
    assert "/target" not in requests
    with pytest.raises(UnicodeDecodeError):
        http["get"](url + "/invalid")


@pytest.mark.parametrize(
    "url",
    [
        "file:///private.txt",
        "ftp://127.0.0.1/file",
        "data:text/plain,secret",
        "/relative",
        "http://",
        "http://user:pass@127.0.0.1",
        1,
    ],
)
def test_http_rejects_non_http_and_embedded_credentials_before_transport(
    url, monkeypatch
):
    import urllib.request

    monkeypatch.setattr(
        urllib.request, "build_opener", lambda *args: pytest.fail("transport created")
    )
    with pytest.raises((TypeError, ValueError)):
        ms.STDLIB_MODULES["thirst::http"]()["get"](url)


def test_http_argument_budgets_and_transport_timeout(monkeypatch):
    import urllib.request

    http = ms.STDLIB_MODULES["thirst::http"]()
    for timeout in (0, 61, True, float("nan"), "1"):
        with pytest.raises(ValueError):
            http["get"]("http://127.0.0.1", timeout)
    for maximum in (-1, True, 67108865):
        with pytest.raises(ValueError):
            http["get"]("http://127.0.0.1", 1, maximum)
    with pytest.raises(ValueError, match="request body"):
        http["post"]("http://127.0.0.1", "x" * 1048577)

    def timeout(*args, **kwargs):
        raise TimeoutError("transport timed out")

    monkeypatch.setattr(urllib.request.OpenerDirector, "open", timeout)
    with pytest.raises(TimeoutError):
        http["get"]("http://127.0.0.1")


def test_process_argv_is_literal_and_output_is_real():
    process = ms.STDLIB_MODULES["thirst::process"]()
    argument = "; echo unwanted && exit 9 | shell-meta"
    result = process["run"](
        [sys.executable, "-c", "import sys; print(sys.argv[1])", argument]
    )
    assert result == argument + "\n"
    assert (
        process["run"](
            [
                sys.executable,
                "-u",
                "-c",
                "import sys; print('out'); sys.stderr.write('err')",
            ]
        )
        == "out\nerr"
    )
    with pytest.raises(FileNotFoundError):
        process["run"](["thirsty-nonexistent-executable-unique-0754"])


def test_process_nonzero_exit_and_invalid_utf8_are_errors():
    process = ms.STDLIB_MODULES["thirst::process"]()
    with pytest.raises(subprocess.CalledProcessError) as failure:
        process["run"](
            [sys.executable, "-c", "import sys; print('failed'); sys.exit(7)"]
        )
    assert failure.value.returncode == 7
    assert failure.value.output == ("failed" + os.linesep).encode()
    with pytest.raises(UnicodeDecodeError):
        process["run"](
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(bytes([255]))"]
        )


def test_process_timeout_and_output_overflow_reap_direct_child(monkeypatch):
    original = subprocess.Popen
    children = []

    def launch(*args, **kwargs):
        assert kwargs["shell"] is False
        child = original(*args, **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr(subprocess, "Popen", launch)
    process = ms.STDLIB_MODULES["thirst::process"]()
    with pytest.raises(subprocess.TimeoutExpired):
        process["run"]([sys.executable, "-c", "import time; time.sleep(10)"], 0.05)
    assert children[-1].poll() is not None
    # Allow slow host startup so these cases reach their output-limit checks.
    # The independent 50 ms deadline assertion above remains unchanged.
    with pytest.raises(ValueError, match="output exceeds"):
        process["run"](
            [
                sys.executable,
                "-u",
                "-c",
                "import time; print('x' * 4096); time.sleep(10)",
            ],
            10,
            32,
        )
    assert children[-1].poll() is not None
    assert process["run"]([sys.executable, "-c", "pass"], 10, 0) == ""


def test_process_rejects_implicit_shell_and_invalid_arguments(monkeypatch):
    process = ms.STDLIB_MODULES["thirst::process"]()
    monkeypatch.setattr(
        subprocess, "Popen", lambda *args, **kwargs: pytest.fail("process started")
    )
    for argv in (
        "echo old syntax",
        [],
        [1],
        [""],
        ["tool", "nul\x00value"],
        ["x"] * 1025,
    ):
        with pytest.raises(TypeError):
            process["run"](argv)
    with pytest.raises(ValueError):
        process["run"](["x" * 1048577])
    for timeout in (0, -1, 61, True, float("nan")):
        with pytest.raises(ValueError):
            process["run"]([sys.executable], timeout)
    for maximum in (-1, True, 67108865):
        with pytest.raises(ValueError):
            process["run"]([sys.executable], 1, maximum)
    with pytest.raises(TypeError):
        process["exit"](True)


@pytest.mark.skipif(os.name != "nt", reason="Windows batch execution rule")
def test_windows_batch_file_requires_explicit_shell(tmp_path):
    command = tmp_path / "command.cmd"
    command.write_text("echo this must not execute", encoding="utf-8")
    with pytest.raises(ValueError, match="implicit shell"):
        ms.STDLIB_MODULES["thirst::process"]()["run"]([str(command)])
