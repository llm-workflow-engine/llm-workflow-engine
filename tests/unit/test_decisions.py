"""Exercise decision schema enforcement, retries, and workflow boundaries."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import cast

import pytest
from pydantic import JsonValue, ValidationError

from lwe.decisions import (
    Choice,
    DecisionError,
    DecisionRequest,
    DecisionService,
    DecisionSettings,
    Noul,
    Score,
)


class ScriptedProvider:
    """Return a controlled provider response or a sequence of failures."""

    def __init__(self, failures: list[DecisionError] | None = None) -> None:
        self.calls: int = 0
        self.preparations: int = 0
        self.failures = list(failures or [])
        self.response: dict[str, object] = {
            "model": "test-model",
            "answers": {
                "urgent": {"type": "noul", "noul": 0.0},
                "team": {
                    "type": "choice",
                    "choice": "support",
                    "probabilities": {"support": 0.9, "other": 0.1},
                    "confidence": 0.7,
                },
                "severity": {
                    "type": "score",
                    "score": 0.25,
                    "probabilities": {"0": 0.75, "1": 0.25},
                    "legend": {"0": "low", "1": "high"},
                },
            },
            "usage": {"input_tokens": 42},
        }

    def validate(self, request: DecisionRequest, settings: DecisionSettings) -> None:
        """Accept already validated inputs."""

    def invoke(self, request: DecisionRequest, settings: DecisionSettings) -> dict[str, object]:
        """Record calls and return the next scripted outcome."""
        self.calls += 1
        if self.failures:
            raise self.failures.pop(0)
        return copy.deepcopy(self.response)

    def prepare(self, request: DecisionRequest, settings: DecisionSettings) -> DecisionRequest:
        """Keep the in-memory test input unchanged."""
        self.preparations += 1
        return request


@pytest.fixture
def decision_request() -> DecisionRequest:
    """A realistic multi-question request sharing one structured state."""
    return DecisionRequest(
        state={"message": "Checkout is unavailable.", "account": 42},
        questions={
            "urgent": Noul(instructions="Does this need urgent attention?"),
            "team": Choice(
                instructions="Which team?",
                criteria={"support": "Help", "other": "Other"},
            ),
            "severity": Score(instructions="How severe?", criteria=["low", "high"]),
        },
    )


def test_result_preserves_semantics_and_rejects_invalid_answers(
    decision_request: DecisionRequest,
) -> None:
    """Never route workflows using missing, invented, or inconsistent answers."""
    provider = ScriptedProvider()
    service = DecisionService(DecisionSettings(provider="test", model="test-model"), provider)
    result = service.decide(decision_request).model_dump(mode="json")
    assert result["answers"]["urgent"]["noul"] == 0.0
    assert result["answers"]["severity"]["score"] == 0.25
    assert result["answers"]["team"]["confidence"] == 0.7
    assert result["usage"] == {"input_tokens": 42}
    valid_answers = copy.deepcopy(provider.response["answers"])
    corrupt_answers = [
        {},
        {"urgent": {"type": "noul", "noul": True}},
        {"urgent": {"type": "noul", "noul": float("nan")}},
        {
            "team": {
                "type": "choice",
                "choice": "invented",
                "probabilities": {"support": 0.9, "other": 0.1},
            }
        },
        {
            "team": {
                "type": "choice",
                "choice": "support",
                "probabilities": {"support": 0.9},
            }
        },
        {
            "severity": {
                "type": "score",
                "score": 1.0,
                "probabilities": {"0": 0.75, "1": 0.25},
                "legend": {"0": "low", "1": "high"},
            }
        },
    ]
    for replacements in corrupt_answers:
        provider.response["answers"] = (
            {**cast(dict[str, object], valid_answers), **replacements} if replacements else {}
        )
        with pytest.raises(DecisionError, match="response failed validation"):
            service.decide(decision_request)


def test_independently_rounded_scores_and_distributions(
    decision_request: DecisionRequest,
) -> None:
    """Accept Cloudflare's rounded output without accepting inconsistent scores."""
    provider = ScriptedProvider()
    service = DecisionService(DecisionSettings(provider="test", model="test-model"), provider)
    criteria: list[JsonValue] = ["No impact", "Minor", "Major", "Critical"]
    decision_request.questions["severity"] = Score(instructions="How severe?", criteria=criteria)
    answers = cast(dict[str, object], provider.response["answers"])
    severity = {
        "type": "score",
        "score": 1.3925,
        "probabilities": {"0": 0.218, "1": 0.3113, "2": 0.3311, "3": 0.1396},
        "legend": {str(i): value for i, value in enumerate(criteria)},
        "confidence": 0.0314,
    }
    answers["severity"] = severity
    assert service.decide(decision_request).model_dump()["answers"]["severity"] == severity
    for changes in (
        {"score": 1.393},
        {"legend": {"0": "Wrong", "1": "Minor", "2": "Major", "3": "Critical"}},
        {"score": -0.0001, "probabilities": {"0": 1.0, "1": 0.0, "2": 0.0, "3": 0.0}},
        {"score": 3.0001, "probabilities": {"0": 0.0, "1": 0.0, "2": 0.0, "3": 1.0}},
    ):
        answers["severity"] = {**severity, **changes}
        with pytest.raises(DecisionError, match="response failed validation"):
            service.decide(decision_request)
    answers["severity"] = severity
    options: dict[str, JsonValue] = {f"team{i}": f"Team {i}" for i in range(6)}
    decision_request.questions["team"] = Choice(instructions="Which team?", criteria=options)
    probabilities = {key: 0.1667 for key in options}
    answers["team"] = {"type": "choice", "choice": "team0", "probabilities": probabilities}
    service.decide(decision_request)
    probabilities["team0"] = 0.167
    with pytest.raises(DecisionError, match="response failed validation"):
        service.decide(decision_request)


@pytest.mark.parametrize(
    "changes",
    [
        {"questions": {}},
        {"questions": {"bad id": {"type": "noul", "instructions": "Urgent?"}}},
        {
            "questions": {
                "severity": {
                    "type": "score",
                    "instructions": "Severity?",
                    "criteria": ["low"],
                }
            }
        },
    ],
)
def test_invalid_requests_fail_before_invocation(
    decision_request: DecisionRequest, changes: dict[str, object]
) -> None:
    """Reject bad question schemas and unsupported media representations locally."""
    with pytest.raises(ValidationError):
        DecisionRequest.model_validate({**decision_request.model_dump(), **changes})


def test_retries_only_transient_failures_and_obeys_limit(
    decision_request: DecisionRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Bound billable attempts and never retry authentication or malformed results."""
    delays: list[int] = []
    monkeypatch.setattr("lwe.decisions.service.time.sleep", delays.append)
    settings = DecisionSettings(provider="test", model="test-model", max_retries=1)
    provider = ScriptedProvider([DecisionError("busy", retryable=True)])
    DecisionService(settings, provider).decide(decision_request)
    assert provider.calls == 2 and delays == [1]
    assert provider.preparations == 1
    for failures, expected_calls in [
        ([DecisionError("unauthorized")], 1),
        ([DecisionError("busy", retryable=True)] * 3, 2),
    ]:
        provider = ScriptedProvider(failures)
        with pytest.raises(DecisionError):
            DecisionService(settings, provider).decide(decision_request)
        assert provider.calls == expected_calls


def test_profile_and_import_work_without_loading_chat(tmp_path: Path) -> None:
    """Decision-only Python usage must not initialize or import chat infrastructure."""
    profile_dir = tmp_path / "profiles" / "triage"
    profile_dir.mkdir(parents=True)
    (profile_dir / "config.yaml").write_text(
        "decisions:\n  presets:\n    clef:\n      provider: cloudflare\n      model: clef-omni\n",
        encoding="utf-8",
    )
    program = (
        "import sys\n"
        "from lwe.decisions import DecisionSettings\n"
        "settings = DecisionSettings.from_preset('clef', profile='triage', config_dir=sys.argv[1], data_dir=sys.argv[1])\n"
        "assert settings.provider == 'cloudflare'\n"
        "assert 'lwe.backends.api.backend' not in sys.modules\n"
        "assert 'langchain_typesafe' not in sys.modules\n"
    )
    subprocess.run([sys.executable, "-c", program, str(tmp_path)], check=True, capture_output=True)


def test_ansible_returns_structured_results_and_skips_calls_in_check_mode(
    decision_request: DecisionRequest, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Exercise actual Ansible parsing and output without a network or credentials."""
    from ansible.module_utils import basic
    from lwe.backends.api.workflow.library.lwe_decide import main

    provider = ScriptedProvider()
    monkeypatch.setattr(DecisionService, "_load_provider", staticmethod(lambda name: provider))
    outputs: list[dict[str, object]] = []

    def capture_exit(module: object, **result: object) -> None:
        outputs.append(result)
        raise SystemExit(0)

    monkeypatch.setattr(basic.AnsibleModule, "exit_json", capture_exit)
    monkeypatch.setattr(basic, "_ANSIBLE_PROFILE", "legacy", raising=False)
    for check_mode in (False, True):
        arguments = {
            **decision_request.model_dump(mode="json"),
            "settings": {"provider": "test", "model": "test-model"},
            "_ansible_check_mode": check_mode,
        }
        monkeypatch.setattr(
            basic,
            "_ANSIBLE_ARGS",
            json.dumps({"ANSIBLE_MODULE_ARGS": arguments}).encode(),
        )
        with pytest.raises(SystemExit) as exited:
            main()
        assert exited.value.code == 0
    assert provider.calls == 1
    assert outputs[0]["changed"] is False
    assert outputs[0]["answers"] == provider.response["answers"]
    assert outputs[1]["skipped"] is True
    assert "answers" not in outputs[1]
