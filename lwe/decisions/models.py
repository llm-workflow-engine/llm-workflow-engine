"""Validated requests and results for probabilistic decision models."""

from __future__ import annotations

import math
from typing import Annotated, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from lwe.decisions.media import MediaLoader, MediaPolicy

State: TypeAlias = str | dict[str, JsonValue] | list[JsonValue]
Probability: TypeAlias = Annotated[float, Field(ge=0, le=1)]
QuestionId: TypeAlias = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]{1,100}$")]
RESPONSE_ROUNDING_ERROR = 0.5 * 10**-4
FLOAT_COMPARISON_EPSILON = 1e-12


class DecisionModel(BaseModel):
    """Reject misspelled fields, coercions, and non-finite numbers."""

    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class Noul(DecisionModel):
    """Ask for the probability that a statement is true."""

    type: Literal["noul"] = "noul"
    instructions: State
    criteria: dict[Literal["true", "false"], JsonValue] | None = None


class Choice(DecisionModel):
    """Select one of the named alternatives."""

    type: Literal["choice"] = "choice"
    instructions: State
    criteria: dict[str, JsonValue] = Field(min_length=1)


class Score(DecisionModel):
    """Evaluate an ordered rubric whose levels start at zero."""

    type: Literal["score"] = "score"
    instructions: State
    criteria: list[JsonValue] = Field(min_length=2)


Question: TypeAlias = Annotated[Noul | Choice | Score, Field(discriminator="type")]


class DecisionRequest(DecisionModel):
    """Supply structured state, typed questions, and optional embedded media."""

    state: State
    questions: dict[QuestionId, Question] = Field(min_length=1, max_length=64)
    images: list[str] = Field(default_factory=list, repr=False)
    audio: list[str] = Field(default_factory=list, repr=False)
    videos: list[str] = Field(default_factory=list, repr=False)

    def validate_media(
        self, policy: MediaPolicy, *, loader: MediaLoader | None = None, resolve: bool = False
    ) -> DecisionRequest:
        """Apply a plugin's media policy, optionally resolving sources into a new request."""
        media = {"images": self.images, "audio": self.audio, "videos": self.videos}
        normalized = (loader or MediaLoader()).validate_media(media, policy, resolve=resolve)
        return self.model_copy(update=normalized)

    @property
    def has_media(self) -> bool:
        """Whether this request requires a multimodal provider."""
        return bool(self.images or self.audio or self.videos)


class NoulAnswer(DecisionModel):
    """Probability of yes, including valid zero and one endpoints."""

    type: Literal["noul"]
    noul: Probability


class ChoiceAnswer(DecisionModel):
    """Selected label with its distribution and optional provider confidence."""

    type: Literal["choice"]
    choice: str
    probabilities: dict[str, Probability]
    confidence: Probability | None = None


class ScoreAnswer(DecisionModel):
    """Fractional expected rubric position and its probability distribution."""

    type: Literal["score"]
    score: float
    probabilities: dict[str, Probability]
    legend: dict[str, JsonValue]
    confidence: Probability | None = None


Answer: TypeAlias = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]


class DecisionResult(DecisionModel):
    """Provider-independent result suitable for Python and JSON serialization."""

    provider: str
    model: str = Field(min_length=1)
    answers: dict[str, Answer]
    usage: dict[str, JsonValue] = Field(default_factory=dict)
    request_id: str | None = None
    elapsed_seconds: float = Field(ge=0)

    def validate_answers(self, request: DecisionRequest) -> None:
        """Reject incomplete answers and distributions outside the supplied schema.

        :raises ValueError: If any answer contradicts the request's types or options.
        """
        if self.answers.keys() != request.questions.keys():
            raise ValueError("Response answer IDs do not match the request")
        for name, question in request.questions.items():
            answer = self.answers[name]
            if answer.type != question.type:
                raise ValueError(f"Answer type does not match question {name!r}")
            if isinstance(answer, ChoiceAnswer) and isinstance(question, Choice):
                if answer.choice not in question.criteria:
                    raise ValueError(f"Unknown choice for question {name!r}")
                self._validate_distribution(answer.probabilities, set(question.criteria))
            elif isinstance(answer, ScoreAnswer) and isinstance(question, Score):
                legend = {str(i): value for i, value in enumerate(question.criteria)}
                self._validate_distribution(answer.probabilities, set(legend))
                expected = math.fsum(int(i) * p for i, p in answer.probabilities.items())
                tolerance = self._rounding_tolerance(1 + sum(range(len(legend))))
                if (
                    answer.legend != legend
                    or not 0 <= answer.score <= len(legend) - 1
                    or not math.isclose(answer.score, expected, rel_tol=0, abs_tol=tolerance)
                ):
                    raise ValueError(f"Score does not match the rubric/distribution for {name!r}")

    @staticmethod
    def _rounding_tolerance(weight: int) -> float:
        """Bound independent four-decimal rounding errors, weighted by rubric index.

        Scores also contribute one rounding error because providers calculate them
        before rounding the individual probabilities. Include a small allowance
        for binary floating-point arithmetic at the boundary.
        """
        return weight * RESPONSE_ROUNDING_ERROR + FLOAT_COMPARISON_EPSILON

    @classmethod
    def _validate_distribution(
        cls, probabilities: dict[str, float], expected: set[str]
    ) -> None:
        """Require a complete normalized distribution, allowing rounding error."""
        if set(probabilities) != expected or not math.isclose(
            math.fsum(probabilities.values()),
            1.0,
            rel_tol=0,
            abs_tol=cls._rounding_tolerance(len(expected)),
        ):
            raise ValueError("Invalid probability distribution")
