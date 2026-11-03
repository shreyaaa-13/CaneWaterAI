"""All tests use mocked clients; no real Groq call is made."""
from datetime import date
import pytest
import genai_explainer as g
from irrigation_scheduler import build_schedule
from response_validator import validate_explanation, collect_facts
from water_requirement_engine import EngineConfig, FieldInputs, estimate_water_requirement

TODAY = date(2026, 10, 20)


class FakeClient:
    def __init__(self, replies=None, exc=None):
        self.replies, self.exc, self.calls, self.messages = list(replies or []), exc, 0, []
        self.chat = type("C", (), {"completions": self})()

    def create(self, **kw):
        self.calls += 1
        self.messages.append(kw["messages"])
        if self.exc:
            raise self.exc
        text = self.replies[min(self.calls - 1, len(self.replies) - 1)]
        msg = type("M", (), {"content": text})()
        return type("R", (), {"choices": [type("Ch", (), {"message": msg})()]})()


@pytest.fixture
def ctx():
    r = estimate_water_requirement(FieldInputs(eto_mm_day=4.0, soil_moisture_pct=25, moisture_is_volumetric=True,
                                               field_capacity_pct=30, wilting_point_pct=15, root_depth_m=0.5,
                                               area=1.0, irrigation_efficiency_pct=50.0), EngineConfig(), TODAY)
    return r, build_schedule(r, TODAY)


def test_fallback_passes_own_validator_all_languages(ctx):
    r, s = ctx
    facts = collect_facts(r, s)
    for lang in ("en", "hi", "mr"):
        text = g.fallback_explanation(r, s, lang)
        assert validate_explanation(text, facts, lang)["passed"], (lang, validate_explanation(text, facts, lang)["feedback"])


def test_fallback_for_insufficient_data():
    r = estimate_water_requirement(FieldInputs(), EngineConfig(), TODAY)
    s = build_schedule(r, TODAY)
    assert "insufficient" in g.fallback_explanation(r, s, "en")


def test_no_api_key_uses_fallback(ctx, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(g, "load_dotenv", lambda *a, **k: None)
    out = g.explain(*ctx, "en")
    assert out["source"] == "fallback" and out["api_error_category"] == "no_api_key" and out["attempts"] == 0


@pytest.mark.parametrize("exc,cat", [(TimeoutError("x"), "timeout"), (RuntimeError("secret sk-123"), "api_error")])
def test_api_failure_falls_back_without_leaking(ctx, exc, cat):
    out = g.explain(*ctx, "en", client=FakeClient(exc=exc))
    assert out["source"] == "fallback" and out["api_error_category"] == cat
    assert "sk-123" not in out["text"] and "secret" not in str(out)


def test_status_code_classification():
    e = Exception(); e.status_code = 429
    assert g.classify_error(e) == "rate_limit"
    e.status_code = 404
    assert g.classify_error(e) == "model_unavailable"


def good_text(r, s):
    n = collect_facts(r, s)["numeric"]
    return (f"This is an educational prototype. Plan irrigation later, around {s['review_date']}. Net need is "
            f"{n['net_irrigation_mm']['value']:g} mm and gross is {n['gross_irrigation_mm']['value']:g} mm. "
            "The numbers are uncertain estimates with some assumptions.")


def test_valid_first_attempt(ctx):
    c = FakeClient([good_text(*ctx)])
    out = g.explain(*ctx, "en", client=c)
    assert out["source"] == "ai" and out["attempts"] == 1 and not out["corrected"] and c.calls == 1


def test_correction_succeeds_on_second_attempt(ctx):
    c = FakeClient(["Educational prototype. Apply 999 mm now.", good_text(*ctx)])
    out = g.explain(*ctx, "en", client=c)
    assert out["source"] == "ai" and out["attempts"] == 2 and out["corrected"] and out["validation_failures"] == 1
    assert "failed automatic validation" in c.messages[1][1]["content"]


def test_retries_are_bounded_then_fallback(ctx):
    c = FakeClient(["Educational prototype. Apply 999 mm."])
    out = g.explain(*ctx, "en", client=c, max_retries=2)
    assert c.calls == 3 and out["attempts"] == 3 and out["source"] == "fallback"
    assert out["fallback_reason"] == "validation_failed"
    c2 = FakeClient(["bad 999 mm"])
    g.explain(*ctx, "en", client=c2, max_retries=0)
    assert c2.calls == 1


def test_inputs_not_modified(ctx):
    import copy
    r, s = ctx
    r0, s0 = copy.deepcopy(r), copy.deepcopy(s)
    g.explain(r, s, "en", client=FakeClient(["Educational prototype. Apply 999 mm."]))
    assert r == r0 and s == s0


def test_invalid_inputs_never_call_api():
    r = estimate_water_requirement(FieldInputs(soil_moisture_pct=500), EngineConfig(), TODAY)
    c = FakeClient(["x"])
    out = g.explain(r, build_schedule(r, TODAY), "en", client=c)
    assert c.calls == 0 and out["source"] == "fallback"
