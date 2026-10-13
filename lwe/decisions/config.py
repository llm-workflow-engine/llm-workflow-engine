"""Connection settings and profile presets for decision providers."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import Field, JsonValue, SecretStr

from lwe.core.config import Config
from lwe.decisions.models import DecisionModel


class DecisionSettings(DecisionModel):
    """Configure a provider without constructing a chat backend or API client."""

    provider: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    model: str = Field(min_length=1, pattern=r"\S")
    options: dict[str, JsonValue] = Field(default_factory=dict)
    api_key: SecretStr | None = Field(default=None, exclude=True, repr=False)
    api_key_env_var: str | None = Field(default=None, min_length=1)
    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=2, ge=0, le=5)

    def credentials(self, default_env_var: str) -> str:
        """Resolve a secret at invocation time, never during preset loading."""
        variable = self.api_key_env_var or default_env_var
        value = self.api_key.get_secret_value() if self.api_key else os.getenv(variable, "")
        if not value.strip():
            raise ValueError(f"Decision provider credentials are missing; set {variable}")
        return value

    @classmethod
    def from_preset(
        cls,
        preset: str,
        *,
        profile: str = "default",
        config_dir: str | Path | None = None,
        data_dir: str | Path | None = None,
    ) -> DecisionSettings:
        """Read ``decisions.presets`` from an ordinary LWE profile.

        :param preset: Name of a decision preset in the profile configuration.
        :param profile: Optional LWE profile containing the preset; defaults to ``default``.
        :raises ValueError: If the preset is missing or malformed.
        """
        config = Config(
            config_dir=str(config_dir) if config_dir else os.getenv("LWE_CONFIG_DIR"),
            data_dir=str(data_dir) if data_dir else os.getenv("LWE_DATA_DIR"),
            profile=profile,
        )
        config.load_from_file()
        presets = config.get("decisions.presets") or {}
        if not isinstance(presets, dict) or preset not in presets:
            raise ValueError(f"Decision preset {preset!r} not found in profile {profile!r}")
        return cls.model_validate(presets[preset])
