"""The model written in every trace is the one that answered, read from Nightshift's receipt."""
from types import SimpleNamespace

from app.llm import served_model


class _Resp:
    def __init__(self, data):
        self._data = data
        self.model = data.get("model")

    def model_dump(self):
        return dict(self._data)


def test_receipt_wins_over_the_requested_lane():
    resp = _Resp({"model": "meterless/deep",
                  "meterless": {"routed_model": "nvidia/nemotron-3-ultra-550b-a55b", "receipt_id": "rcpt-1"}})
    assert served_model(resp, "meterless/deep") == ("nvidia/nemotron-3-ultra-550b-a55b", "rcpt-1")


def test_openai_model_field_when_no_receipt():
    assert served_model(_Resp({"model": "nvidia/nemotron-3.5-lightning-30b-a3b"}), "x") == \
        ("nvidia/nemotron-3.5-lightning-30b-a3b", None)


def test_requested_lane_when_nothing_else():
    assert served_model(SimpleNamespace(), "meterless/fast") == ("meterless/fast", None)
