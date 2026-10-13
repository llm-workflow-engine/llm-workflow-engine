"""Execute decision providers without chat, conversation, or CLI dependencies."""

from __future__ import annotations

import json
import logging
import time
from importlib.metadata import entry_points
from typing import Protocol, cast

from pydantic import ValidationError

from lwe.decisions.config import DecisionSettings
from lwe.decisions.models import DecisionRequest, DecisionResult

logger = logging.getLogger(__name__)
ENTRY_POINT_GROUP = "lwe_decision_providers"


class DecisionError(RuntimeError):
    """Report a sanitized provider failure and whether retrying may help."""

    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class DecisionProvider(Protocol):
    """Contract implemented by independently installed provider plugins."""

    def validate(self, request: DecisionRequest, settings: DecisionSettings) -> None:
        """Check provider capabilities without credentials or network access."""
        ...

    def invoke(self, request: DecisionRequest, settings: DecisionSettings) -> dict[str, object]:
        """Return model, answers, usage, and optional request_id as JSON-compatible data.

        :raises DecisionError: If the provider cannot return a successful response.
        """
        ...

    def prepare(self, request: DecisionRequest, settings: DecisionSettings) -> DecisionRequest:
        """Resolve external inputs once before the inference retry loop."""
        ...


class DecisionService:
    """Validate and execute decisions with bounded transient-failure retries.

    :param settings: Explicit connection settings or settings loaded from a profile.
    :param provider: Optional adapter instance, useful for embedding and tests.
    """

    def __init__(
        self, settings: DecisionSettings, provider: DecisionProvider | None = None
    ) -> None:
        self.settings = settings
        self.provider = provider if provider is not None else self._load_provider(settings.provider)

    @staticmethod
    def _load_provider(name: str) -> DecisionProvider:
        """Load exactly one explicitly requested decision provider entry point."""
        matches = list(entry_points(group=ENTRY_POINT_GROUP, name=name))
        if len(matches) != 1:
            raise DecisionError(
                f"Expected one installed decision provider named {name!r}, found {len(matches)}. "
                f"Install the corresponding lwe-plugin-decision-{name.replace('_', '-')} package."
            )
        try:
            factory = matches[0].load()
            return cast(DecisionProvider, factory())
        except Exception as error:
            raise DecisionError(f"Could not load decision provider {name!r}") from error

    def validate(self, request: DecisionRequest) -> DecisionRequest:
        """Validate requests without resolving credentials or making API calls."""
        validated = DecisionRequest.model_validate(request.model_dump())
        json.dumps(validated.model_dump(mode="json"), allow_nan=False)
        self.provider.validate(validated, self.settings)
        return validated

    def decide(self, request: DecisionRequest) -> DecisionResult:
        """Execute one request and preserve typed answers, usage, and timing.

        :raises DecisionError: On provider failure or an invalid response.
        :raises ValueError: On invalid input or unsupported provider capabilities.
        :return: A complete result whose answers match the supplied questions.
        """
        request = self.validate(request)
        started = time.monotonic()
        request = self.provider.prepare(request, self.settings)
        logger.debug(
            "Starting decision provider=%s questions=%d",
            self.settings.provider,
            len(request.questions),
        )
        for attempt in range(self.settings.max_retries + 1):
            try:
                payload = self.provider.invoke(request, self.settings)
                result = DecisionResult.model_validate(
                    {
                        **payload,
                        "provider": self.settings.provider,
                        "elapsed_seconds": time.monotonic() - started,
                    }
                )
                result.validate_answers(request)
                logger.info(
                    "Decision completed provider=%s elapsed_seconds=%.3f",
                    result.provider,
                    result.elapsed_seconds,
                )
                return result
            except (ValidationError, ValueError) as error:
                raise DecisionError("Decision response failed validation") from error
            except DecisionError as error:
                if not error.retryable or attempt == self.settings.max_retries:
                    raise
                delay = min(2**attempt, 8)
                logger.warning(
                    "Retrying decision provider=%s attempt=%d delay=%d",
                    self.settings.provider,
                    attempt + 1,
                    delay,
                )
                time.sleep(delay)
        raise AssertionError("Decision retry loop exhausted without a result")
