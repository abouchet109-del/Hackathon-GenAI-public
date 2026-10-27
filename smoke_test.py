# smoke_test.py: checks your Data and Power layers
# Install once:
#   pip install openai python-dotenv requests
import os
import uuid

import requests
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
results = []


def check(name, fn):
    try:
        fn()
        results.append(("PASS", name, ""))
    except Exception as error:
        results.append(("FAIL", name, str(error)[:150]))


def need(*names):
    for name in names:
        assert os.environ.get(name), f"{name} is missing from .env"


def zetaris_web():
    url = os.environ.get("ZETARIS_BASE_URL", "http://localhost:3000")
    requests.get(url, timeout=10).raise_for_status()


def zetaris_sql():
    need("ZETARIS_REST_URL", "ZETARIS_ORG_ID", "ZETARIS_API_KEY")
    response = requests.post(
        os.environ["ZETARIS_REST_URL"].rstrip("/") + "/sql-editor/sqls/run",
        headers={
            "Authorization": "Bearer " + os.environ["ZETARIS_API_KEY"],
            "X-Org-ID": os.environ["ZETARIS_ORG_ID"],
            "X-Request-ID": str(uuid.uuid4()),
        },
        json={"queryId": str(uuid.uuid4()), "sql": "SELECT 1",
              "source": "SqlEditor", "limit": 1},
        timeout=60,
    )
    response.raise_for_status()
    data = response.json().get("data")
    assert data and str(data[0][0]) == "1", \
        "unexpected reply: " + response.text[:80]


def nemotron():
    """Nightshift answers on the deep lane, and the model that answered is a Nemotron (read from the receipt)."""
    need("METERLESS_BASE_URL", "METERLESS_RUNTIME_TOKEN")
    model = os.environ.get("METERLESS_MODEL_DEEP") or os.environ.get("NEMOTRON_MODEL") or "meterless/deep"
    client = OpenAI(
        base_url=os.environ["METERLESS_BASE_URL"],
        api_key=os.environ["METERLESS_RUNTIME_TOKEN"],
        default_headers={"meterless-app": os.environ.get("METERLESS_APP", "osef-hackathon"), "meterless-scope": "user"},
    )
    reply = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": "Reply with the single word: ready"}],
    )
    assert reply.choices, "no reply from the model"
    from app.llm import served_model
    served, receipt = served_model(reply, model)
    assert "nemotron" in served.lower(), f"answered by {served}, not a Nemotron model: set the NVIDIA key in Nightshift"
    results.append(("INFO", "Power: model that answered", served + (f" (receipt {receipt})" if receipt else "")))


def hmem():
    url = os.environ.get("HMEM_URL", "http://127.0.0.1:8787")
    r = requests.get(f"{url}/health", timeout=3)
    assert r.status_code == 200, f"{url}/health -> {r.status_code}"


check("Data: Zetaris web interface", zetaris_web)
check("Data: Zetaris runs SQL over its REST API", zetaris_sql)
check("Power: Nightshift answers with a Nemotron model", nemotron)
check("Build: Meterless H-MEM service", hmem)

for status, name, detail in results:
    print(f"{status} {name} {detail}")
