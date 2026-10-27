"""Model providers for the agent.

Two OpenAI-compatible providers:
- "openai": any OpenAI-compatible route configured with MODEL_BASE_URL, MODEL_API_KEY
  and NEMOTRON_MODEL (for example NVIDIA's free API).
- "meterless": Meterless Runtime (Nightshift), following Meterless Runtime 1.4,
  provider contract v4. This is the primary provider.

Command line:
    python -m atlas.llm status | detect | models | token | connect <link> | chat <text>
"""
import getpass
import json
import os
import sys
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
SETTINGS_FILE = ROOT / ".settings.json"  # git-ignored, holds the runtime token
load_dotenv(ROOT / ".env")

PROVIDERS = {
    "openai": "OpenAI-compatible (MODEL_*)",
    "meterless": "Meterless Runtime",
}
DEFAULT_PROVIDER = "meterless"

APP_ID = "open-agent-hack"  # stable lowercase id sent as meterless-app
CHAT_TIMEOUT = 180  # seconds: loading a model can take minutes
PROBE_TIMEOUT = 2

METERLESS_ID = "meterless"
METERLESS_NAME = "Meterless Runtime"
METERLESS_DEFAULT_BASE_URL = "http://127.0.0.1:8088/v1"
METERLESS_DEFAULT_MODEL = "meterless/auto"
TOKEN_KEY = "meterless_runtime_token"
BASE_URL_KEY = "meterless_base_url"
PLACEHOLDER_TOKENS = {"rt-local"}
DISPOSITIONS = ("auto", "fast", "deep", "cheap", "local", "fusion")
DETECT_PORTS = (8088, 8090, 8787, 11434)
DETECT_HOSTS = ("127.0.0.1", "localhost", "[::1]")


class MeterlessUnauthorized(Exception):
    """The runtime refused the token (401/403)."""


# --- settings -------------------------------------------------------------

def load_settings():
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_settings(**changes):
    settings = load_settings()
    settings.update(changes)
    SETTINGS_FILE.write_text(json.dumps(settings, indent=2), encoding="utf-8")


# --- base URL and connect links --------------------------------------------

def normalize_base_url(raw):
    """Turns any pasted runtime address into <scheme>://<host>/v1."""
    url = (raw or "").strip()
    if not url:
        return METERLESS_DEFAULT_BASE_URL
    if "://" not in url:
        url = "http://" + url
    parts = urlsplit(url)
    if not parts.netloc:
        raise ValueError("Not a runtime address")
    # Dropping the whole path covers /v1, /v1/chat/completions, /v1/models and
    # /healthz, and can never produce /v1/v1.
    return f"{parts.scheme}://{parts.netloc}/v1"


def parse_connect_link(text):
    """Returns (base_url, key) for http://<host>:<port>/connect#k=<key>, else None."""
    parts = urlsplit((text or "").strip())
    if not parts.scheme or parts.path.rstrip("/") != "/connect" or not parts.fragment:
        return None
    key = parse_qs(parts.fragment).get("k", [None])[0]
    if not key:
        return None
    return f"{parts.scheme}://{parts.netloc}/v1", key


def get_base_url():
    raw = load_settings().get(BASE_URL_KEY) or os.environ.get("METERLESS_BASE_URL")
    return normalize_base_url(raw)


# --- token ------------------------------------------------------------------

def valid_token(token):
    token = (token or "").strip()
    return token if token and token not in PLACEHOLDER_TOKENS else None


def read_proxy_token(state_dir=None):
    """The runtime writes its token to <stateDir>/proxy-token."""
    state_dir = state_dir or os.environ.get("METERLESS_STATE_DIR")
    if not state_dir:
        return None
    try:
        return valid_token(Path(state_dir, "proxy-token").read_text(encoding="utf-8"))
    except OSError:
        return None


def get_token():
    return (valid_token(load_settings().get(TOKEN_KEY))
            or valid_token(os.environ.get("METERLESS_RUNTIME_TOKEN"))
            or read_proxy_token())


def set_token(token):
    token = valid_token(token)
    if not token:
        raise ValueError("Paste the real token from the Nightshift Console (rt-local is a placeholder).")
    save_settings(**{TOKEN_KEY: token})


def connect(link):
    """Saves base URL and token from a connect link. Never prints or logs the link."""
    parsed = parse_connect_link(link)
    if not parsed:
        raise ValueError("Not a Meterless connect link")
    base_url, key = parsed
    set_token(key)
    save_settings(**{BASE_URL_KEY: base_url})
    return base_url


# --- runtime calls ------------------------------------------------------------

def _headers(token, chat=False):
    headers = {"Authorization": f"Bearer {token or ''}", "meterless-app": APP_ID}
    if chat:
        headers["meterless-scope"] = "user"
    return headers


def _meterless_ids(response):
    try:
        data = response.json().get("data") or []
    except ValueError:
        return []
    ids = [item.get("id") for item in data if isinstance(item, dict)]
    return [i for i in ids if isinstance(i, str) and i.startswith("meterless/")]


def check_status(base_url=None, token=None, timeout=PROBE_TIMEOUT):
    """"online", "unauthorized" or "offline". /healthz is not enough: /v1/models decides."""
    base_url = normalize_base_url(base_url) if base_url else get_base_url()
    token = get_token() if token is None else token
    try:
        response = requests.get(f"{base_url}/models", headers=_headers(token), timeout=timeout)
    except requests.RequestException:
        return "offline"
    if response.status_code in (401, 403):
        return "unauthorized"
    if response.status_code == 200 and _meterless_ids(response):
        return "online"
    return "offline"


def list_models(base_url=None, token=None):
    """Every meterless/* routing mode the runtime offers, including ones we don't know."""
    base_url = normalize_base_url(base_url) if base_url else get_base_url()
    token = get_token() if token is None else token
    response = requests.get(f"{base_url}/models", headers=_headers(token), timeout=PROBE_TIMEOUT)
    if response.status_code in (401, 403):
        raise MeterlessUnauthorized("Meterless Runtime refused the token")
    response.raise_for_status()
    return _meterless_ids(response)


def describe_model(model_id):
    """Splits meterless/<disposition>, meterless/<class> or meterless/<class>.<disposition>."""
    name = model_id.removeprefix("meterless/")
    if name in DISPOSITIONS:
        return {"class": None, "disposition": name}
    model_class, _, disposition = name.partition(".")
    if disposition in DISPOSITIONS:
        return {"class": model_class, "disposition": disposition}
    return {"class": name, "disposition": None}


def auto_detect(token=None, ports=DETECT_PORTS, hosts=DETECT_HOSTS, save=True):
    """Saves and returns (base_url, status) for the first online or unauthorized runtime."""
    token = get_token() if token is None else token
    for port in ports:
        for host in hosts:
            base_url = f"http://{host}:{port}/v1"
            status = check_status(base_url, token, timeout=1)
            if status in ("online", "unauthorized"):
                if save:
                    save_settings(**{BASE_URL_KEY: base_url})
                return base_url, status
    return None, "offline"


def chat(prompt, model=None, provider=None):
    """Sends a prompt (plain string, or a list of messages) and returns the reply text."""
    provider = provider or os.environ.get("LLM_PROVIDER") or DEFAULT_PROVIDER
    if provider == METERLESS_ID:
        base_url = get_base_url()
        headers = _headers(get_token(), chat=True)
        model = model or os.environ.get("METERLESS_MODEL") or METERLESS_DEFAULT_MODEL
    elif provider == "openai":
        base_url = os.environ["MODEL_BASE_URL"].rstrip("/")
        headers = {"Authorization": f"Bearer {os.environ['MODEL_API_KEY']}"}
        model = model or os.environ["NEMOTRON_MODEL"]
    else:
        raise ValueError(f"Unknown provider {provider!r}, expected one of {list(PROVIDERS)}")

    messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
    response = requests.post(f"{base_url}/chat/completions", headers=headers,
                             json={"model": model, "messages": messages}, timeout=CHAT_TIMEOUT)
    if provider == METERLESS_ID and response.status_code in (401, 403):
        raise MeterlessUnauthorized("Meterless Runtime refused the token")
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# --- command line -------------------------------------------------------------

def _ask_for_token():
    if not sys.stdin.isatty():
        print("Set the token with: python -m atlas.llm token")
        return
    set_token(getpass.getpass("Paste the Meterless Runtime token (hidden): "))
    print("Token saved. Status:", check_status())


def main(argv):
    command = argv[0] if argv else "status"
    if command == "status":
        status = check_status()
        print(f"{METERLESS_NAME} at {get_base_url()}: {status}")
        if status == "unauthorized":
            _ask_for_token()
    elif command == "detect":
        base_url, status = auto_detect()
        print(f"Found {base_url} ({status})" if base_url else "No Meterless Runtime found")
        if status == "unauthorized":
            _ask_for_token()
    elif command == "models":
        print("\n".join(list_models()))
    elif command == "token":
        _ask_for_token()
    elif command == "connect" and len(argv) > 1:
        print(f"Connected to {connect(argv[1])}")
    elif command == "chat" and len(argv) > 1:
        print(chat(" ".join(argv[1:])))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
