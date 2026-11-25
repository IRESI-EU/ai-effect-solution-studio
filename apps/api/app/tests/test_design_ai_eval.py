from types import SimpleNamespace

from app.design_ai.eval.scoring import case_current, load_cases, load_snapshot, score_case, summarise, validate_case

SNAP = load_snapshot()
CASES = load_cases()


def _result(workflow=None, reply="", question=None, errors=None, attempts=1):
    return SimpleNamespace(workflow=workflow, reply=reply, clarifying_question=question, errors=errors or [], attempts=attempts)


def _workflow(aliases, settings=None):
    settings = settings or {}
    return {"steps": [{"service_id": SNAP.resolve(a), "settings": settings.get(a, {})} for a in aliases], "connections": []}


def _case(cid):
    return next(c for c in CASES if c["id"] == cid)


def test_every_case_is_well_formed():
    assert len(CASES) >= 80
    assert len({c["id"] for c in CASES}) == len(CASES)
    problems = {c["id"]: validate_case(c, SNAP) for c in CASES}
    assert {k: v for k, v in problems.items() if v} == {}


def test_current_workflow_is_built_as_a_chain():
    current = case_current(_case("followup-03"), SNAP)
    assert [s["ref"] for s in current["steps"]] == ["s1", "s2", "s3"]
    assert current["steps"][0]["settings"] == {"how_many": 5}
    assert len(current["connections"]) == 2


def test_correct_settings_pass_and_wrong_or_extra_settings_fail():
    case = _case("settings-nl-01")
    ok = score_case(case, SNAP, _result(_workflow(["nl_synth", "nl_bench"], {"nl_synth": {"seed": 7, "loading_level": "H"}})))
    assert ok.passed
    wrong = score_case(case, SNAP, _result(_workflow(["nl_synth", "nl_bench"], {"nl_synth": {"seed": 7, "loading_level": "M"}})))
    assert not wrong.passed and wrong.settings_ok is False
    extra = score_case(_case("pipeline-nl-01"), SNAP, _result(_workflow(["nl_synth", "nl_bench"], {"nl_synth": {"seed": 3}})))
    assert not extra.passed
    default = score_case(_case("pipeline-nl-01"), SNAP, _result(_workflow(["nl_synth", "nl_bench"], {"nl_synth": {"seed": 42}})))
    assert default.passed and default.explicit_defaults == 1


def test_optional_default_may_be_set_or_left_out():
    case = _case("settings-de-05")
    assert score_case(case, SNAP, _result(_workflow(["de_provider", "de_chronics", "de_format"]))).passed
    assert score_case(case, SNAP, _result(_workflow(["de_provider", "de_chronics", "de_format"], {"de_chronics": {"round_decimals": 3}}))).passed


def test_refusal_and_partial_rules():
    refusal = _case("refusal-01")
    assert score_case(refusal, SNAP, _result(None, "No service predicts prices.")).passed
    assert not score_case(refusal, SNAP, _result(_workflow(["nl_synth", "nl_bench"]))).passed

    partial = _case("partial-01")
    pt = ["pt_loader", "pt_features", "pt_trainer", "pt_generator"]
    assert score_case(partial, SNAP, _result(_workflow(pt), "Anomaly detection is not available in the catalogue.")).passed
    assert not score_case(partial, SNAP, _result(_workflow(pt), "Here is your workflow.")).passed
    assert score_case(partial, SNAP, _result(None, "Anomaly detection is not available.", "Shall I build the synthetic-data part?")).passed
    assert not score_case(partial, SNAP, _result(None, "Not possible.", "Shall I build something else?")).passed


def test_invalid_workflow_and_extra_service_fail():
    case = _case("pipeline-de-01")
    assert not score_case(case, SNAP, _result(_workflow(["de_provider"]), errors=["broken"], attempts=3)).passed
    extra = score_case(case, SNAP, _result(_workflow(["de_provider", "de_chronics", "de_format", "pt_pipeline_config"])))
    assert not extra.passed and extra.services_ok is False


def test_offline_composer_runs_end_to_end():
    from app.design_ai.composer import compose
    from app.design_ai.eval.scoring import case_history
    from app.design_ai.providers import OfflineModel

    scores = [score_case(c, SNAP, compose(OfflineModel(), SNAP.cards, case_history(c), case_current(c, SNAP))) for c in CASES[:10]]
    summary = summarise(scores)
    assert summary["cases"] == 10 and summary["pass_rate"] is not None
