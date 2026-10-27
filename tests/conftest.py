"""The suite runs the real logic on the sample copies, whatever the shell says: SAMPLE_MODE is set here before
any application module is imported, so `python -m pytest -q` is green with or without the variable.
HMEM_URL points at a closed port unless the shell names a running H-MEM service: the tests then use the local
fallback memory and never touch a company space."""
import os

os.environ["SAMPLE_MODE"] = "true"
os.environ.setdefault("HMEM_URL", "http://127.0.0.1:1")
