"""Checks the Meterless Runtime provider against a fake runtime (contract v4).

Run from the project folder:  .venv\\Scripts\\python.exe -m unittest -v
"""
import json
import os
import shutil
import socket
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from unittest import mock

from agent import llm

TOKEN = "test-runtime-token"
MODEL_IDS = ["meterless/auto", "meterless/fast", "meterless/code.deep",
             "meterless/brand-new-mode", "gpt-not-meterless"]


class FakeRuntime(BaseHTTPRequestHandler):
    seen = []  # (path, headers, body) of each request

    def log_message(self, *args):
        pass

    def _reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self):
        return self.headers.get("Authorization") == f"Bearer {TOKEN}"

    def do_GET(self):
        FakeRuntime.seen.append((self.path, dict(self.headers), None))
        if self.path == "/healthz":
            self._reply(200, {"ok": True})
        elif self.path == "/v1/models":
            if not self._authorized():
                self._reply(401, {"error": "unauthorized"})
            else:
                self._reply(200, {"object": "list", "data": [{"id": i} for i in MODEL_IDS]})
        else:
            self._reply(404, {})

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        FakeRuntime.seen.append((self.path, dict(self.headers), body))
        if self.path != "/v1/chat/completions":
            self._reply(404, {})
        elif not self._authorized():
            self._reply(401, {"error": "unauthorized"})
        else:
            self._reply(200, {"choices": [{"message": {"role": "assistant",
                                                       "content": "This connection works."}}]})


class HealthOnly(FakeRuntime):
    """A process that is up but serves no models."""

    def do_GET(self):
        self._reply(200, {"ok": True}) if self.path == "/healthz" else self._reply(404, {})


def port_is_free(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


def start(handler, port=0):
    server = ThreadingHTTPServer(("127.0.0.1", port), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, f"http://127.0.0.1:{server.server_address[1]}/v1"


class MeterlessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = llm.ROOT / ".test-tmp"
        self.tmp.mkdir(exist_ok=True)
        patches = [
            mock.patch.object(llm, "SETTINGS_FILE", self.tmp / "settings.json"),
            mock.patch.dict(os.environ, {}, clear=False),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)
        for name in ("METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN", "METERLESS_MODEL",
                     "METERLESS_STATE_DIR", "LLM_PROVIDER"):
            os.environ.pop(name, None)
        self.addCleanup(shutil.rmtree, self.tmp, True)
        FakeRuntime.seen.clear()

    def serve(self, handler=FakeRuntime, port=0):
        server, url = start(handler, port)
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return url

    # --- base URL ---------------------------------------------------------

    def test_normalizes_pasted_urls_to_host_v1(self):
        for raw in ["127.0.0.1:8088", "http://127.0.0.1:8088", "http://127.0.0.1:8088/",
                    "http://127.0.0.1:8088/v1", "http://127.0.0.1:8088/v1/",
                    "http://127.0.0.1:8088/v1/chat/completions", "http://127.0.0.1:8088/v1/models",
                    "http://127.0.0.1:8088/healthz", "http://127.0.0.1:8088/v1/v1"]:
            with self.subTest(raw=raw):
                self.assertEqual(llm.normalize_base_url(raw), "http://127.0.0.1:8088/v1")
        self.assertEqual(llm.normalize_base_url(""), "http://127.0.0.1:8088/v1")
        self.assertEqual(llm.normalize_base_url("https://box.local:9000/v1"), "https://box.local:9000/v1")

    def test_connect_link_gives_origin_and_key(self):
        self.assertEqual(llm.parse_connect_link("http://192.168.1.20:8088/connect#k=abc123"),
                         ("http://192.168.1.20:8088/v1", "abc123"))
        self.assertIsNone(llm.parse_connect_link("http://127.0.0.1:8088/v1"))
        base_url = llm.connect("http://127.0.0.1:8090/connect#k=secret-key")
        self.assertEqual(base_url, "http://127.0.0.1:8090/v1")
        settings = llm.load_settings()
        self.assertEqual(settings[llm.TOKEN_KEY], "secret-key")
        self.assertEqual(settings[llm.BASE_URL_KEY], "http://127.0.0.1:8090/v1")

    # --- token ------------------------------------------------------------

    def test_token_is_stored_under_contract_key_and_placeholder_rejected(self):
        with self.assertRaises(ValueError):
            llm.set_token("rt-local")
        llm.set_token(TOKEN)
        self.assertEqual(llm.load_settings()["meterless_runtime_token"], TOKEN)

    def test_reads_proxy_token_from_state_dir(self):
        (self.tmp / "proxy-token").write_text(TOKEN + "\n", encoding="utf-8")
        os.environ["METERLESS_STATE_DIR"] = str(self.tmp)
        self.assertEqual(llm.get_token(), TOKEN)
        (self.tmp / "proxy-token").write_text("rt-local", encoding="utf-8")
        self.assertIsNone(llm.get_token())

    # --- status -----------------------------------------------------------

    def test_wrong_token_is_unauthorized_not_offline(self):
        url = self.serve()
        self.assertEqual(llm.check_status(url, "wrong-token"), "unauthorized")
        self.assertEqual(llm.check_status(url, ""), "unauthorized")

    def test_right_token_is_online(self):
        url = self.serve()
        self.assertEqual(llm.check_status(url, TOKEN), "online")
        path, headers, _ = FakeRuntime.seen[-1]
        self.assertEqual(path, "/v1/models")
        self.assertEqual(headers["meterless-app"], llm.APP_ID)

    def test_healthz_alone_is_offline(self):
        url = self.serve(HealthOnly)
        self.assertEqual(llm.check_status(url, TOKEN), "offline")

    def test_nothing_listening_is_offline(self):
        with socket.socket() as s:
            s.bind(("127.0.0.1", 0))
            port = s.getsockname()[1]
        self.assertEqual(llm.check_status(f"http://127.0.0.1:{port}/v1", TOKEN), "offline")

    # --- models -----------------------------------------------------------

    def test_models_keep_unknown_meterless_ids(self):
        url = self.serve()
        self.assertEqual(llm.list_models(url, TOKEN),
                         ["meterless/auto", "meterless/fast", "meterless/code.deep",
                          "meterless/brand-new-mode"])
        self.assertEqual(llm.describe_model("meterless/code.deep"),
                         {"class": "code", "disposition": "deep"})
        self.assertEqual(llm.describe_model("meterless/auto"), {"class": None, "disposition": "auto"})

    # --- auto detect ------------------------------------------------------

    def test_auto_detect_finds_runtime_and_saves_it(self):
        if not port_is_free(8787):
            self.skipTest("port 8787 is busy")
        earlier = [p for p in llm.DETECT_PORTS[:llm.DETECT_PORTS.index(8787)] if not port_is_free(p)]
        if earlier:
            self.skipTest(f"something already listens on {earlier}")
        url = self.serve(port=8787)
        found, status = llm.auto_detect(token="wrong-token")
        self.assertEqual((found, status), (url, "unauthorized"))
        found, status = llm.auto_detect(token=TOKEN)
        self.assertEqual((found, status), (url, "online"))
        self.assertEqual(llm.load_settings()[llm.BASE_URL_KEY], url)

    # --- chat -------------------------------------------------------------

    def test_plain_text_on_auto_returns_a_string(self):
        url = self.serve()
        llm.save_settings(**{llm.BASE_URL_KEY: url})
        llm.set_token(TOKEN)
        reply = llm.chat("Reply with one sentence confirming this connection works.")
        self.assertIsInstance(reply, str)
        self.assertEqual(reply, "This connection works.")
        path, headers, body = FakeRuntime.seen[-1]
        self.assertEqual(path, "/v1/chat/completions")
        self.assertEqual(body["model"], "meterless/auto")
        self.assertIsInstance(body["messages"][0]["content"], str)
        self.assertEqual(headers["Authorization"], f"Bearer {TOKEN}")
        self.assertEqual(headers["meterless-app"], llm.APP_ID)
        self.assertEqual(headers["meterless-scope"], "user")

    def test_chat_with_wrong_token_raises_unauthorized(self):
        url = self.serve()
        llm.save_settings(**{llm.BASE_URL_KEY: url, llm.TOKEN_KEY: "wrong-token"})
        with self.assertRaises(llm.MeterlessUnauthorized):
            llm.chat("hello")

    def test_chat_uses_180_second_timeout(self):
        self.assertEqual(llm.CHAT_TIMEOUT, 180)


if __name__ == "__main__":
    unittest.main()
