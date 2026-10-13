"""Load media sources and enforce limits supplied by decision providers."""

from __future__ import annotations

import base64
import binascii
import mimetypes
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import unquote, urlsplit

import filetype
import httpx

READ_CHUNK_BYTES = 64 * 1024
MIME_ALIASES = {"audio/x-wav": "audio/wav", "audio/mp3": "audio/mpeg"}


@dataclass(frozen=True)
class MediaLimits:
    """Provider limits for one modality; omitted limits are unrestricted."""

    mime_types: frozenset[str] = frozenset()
    max_items: int | None = None
    max_item_bytes: int | None = None
    max_total_bytes: int | None = None


@dataclass(frozen=True)
class CombinedMediaLimit:
    """A provider's shared decoded byte budget across multiple modalities."""

    modalities: tuple[str, ...]
    max_bytes: int


@dataclass(frozen=True)
class MediaPolicy:
    """Allowed modalities and optional shared budgets, defined by a provider."""

    modalities: Mapping[str, MediaLimits] = field(default_factory=dict)
    combined_limits: tuple[CombinedMediaLimit, ...] = ()


@dataclass(frozen=True)
class LoadedMedia:
    """Normalized wire representation and decoded size of a media item."""

    data_url: str
    size: int


class MediaLoader:
    """Resolve HTTP(S), local file URIs, data URLs, and raw base64.

    :param timeout: Per-operation timeout for media downloads.
    :param transport: Optional isolated HTTP transport, without provider credentials.
    """

    def __init__(self, timeout: float = 30.0, transport: httpx.BaseTransport | None = None) -> None:
        self.timeout = timeout
        self.transport = transport

    def validate_media(
        self,
        media: Mapping[str, list[str]],
        policy: MediaPolicy,
        *,
        resolve: bool = False,
    ) -> dict[str, list[str]]:
        """Validate a provider policy and optionally resolve external sources.

        :param resolve: Download/read sources when true; otherwise inspect only embedded data.
        :raises ValueError: On unsupported sources, failed loading, or exceeded limits.
        :return: New media lists, with resolved sources normalized to data URLs.
        """
        result: dict[str, list[str]] = {}
        sizes: dict[str, int] = {}
        for modality, items in media.items():
            result[modality] = []
            if not items:
                continue
            if modality not in policy.modalities:
                raise ValueError(f"The selected model does not support {modality}")
            limits = policy.modalities[modality]
            if limits.max_items is not None and len(items) > limits.max_items:
                raise ValueError(f"Too many {modality} items; maximum is {limits.max_items}")
            for index, source in enumerate(items):
                budget = self._remaining_bytes(modality, limits, policy, sizes)
                try:
                    loaded = self.load(source, max_bytes=budget, resolve=resolve)
                    if loaded is None:
                        result[modality].append(source)
                        continue
                    mime = loaded.data_url.partition(";")[0].removeprefix("data:")
                    if limits.mime_types and mime not in limits.mime_types:
                        raise ValueError(f"Unsupported MIME type {mime!r}")
                    sizes[modality] = sizes.get(modality, 0) + loaded.size
                    result[modality].append(loaded.data_url)
                except ValueError as error:
                    raise ValueError(f"{modality}[{index}]: {error}") from error
        return result

    @staticmethod
    def _remaining_bytes(
        modality: str, limits: MediaLimits, policy: MediaPolicy, sizes: dict[str, int]
    ) -> int | None:
        """Bound each read by the remaining per-item, modality, and shared budgets."""
        budgets = [] if limits.max_item_bytes is None else [limits.max_item_bytes]
        if limits.max_total_bytes is not None:
            budgets.append(limits.max_total_bytes - sizes.get(modality, 0))
        for group in policy.combined_limits:
            if modality in group.modalities:
                budgets.append(group.max_bytes - sum(sizes.get(key, 0) for key in group.modalities))
        return min(budgets) if budgets else None

    def load(
        self, source: str, *, max_bytes: int | None = None, resolve: bool = True
    ) -> LoadedMedia | None:
        """Load one source; unresolved external sources return None in validation mode."""
        scheme = urlsplit(source).scheme.lower() if not source.startswith("data:") else "data"
        if scheme in {"http", "https"}:
            if not urlsplit(source).hostname:
                raise ValueError("Media URL requires a host")
            return self._load_http(source, max_bytes) if resolve else None
        if scheme == "file":
            path = self._file_path(source)
            return self._load_file(path, max_bytes) if resolve else None
        if scheme and scheme != "data":
            raise ValueError("Unsupported media URI scheme; use HTTP(S), file://, or base64")
        return self._load_base64(source, max_bytes)

    @staticmethod
    def _file_path(source: str) -> Path:
        """Require explicit absolute local file URIs with no remote authority."""
        uri = urlsplit(source)
        path = Path(unquote(uri.path))
        if (
            uri.netloc not in {"", "localhost"}
            or uri.query
            or uri.fragment
            or not path.is_absolute()
        ):
            raise ValueError("Use an absolute local file URI such as file:///path/to/media.wav")
        return path

    def _load_file(self, path: Path, max_bytes: int | None) -> LoadedMedia:
        """Read a regular file with a bounded buffer and explicit file errors."""
        try:
            if not path.is_file():
                raise ValueError("Media file does not exist or is not a regular file")
            self._check_size(path.stat().st_size, max_bytes)
            with path.open("rb") as stream:
                data = self._read_chunks(
                    iter(lambda: stream.read(READ_CHUNK_BYTES), b""), max_bytes
                )
        except OSError as error:
            raise ValueError("Could not read media file") from error
        return self._encode(data, mimetypes.guess_type(path.name)[0])

    def _load_http(self, source: str, max_bytes: int | None) -> LoadedMedia:
        """Stream downloads, enforcing size even when Content-Length is absent or wrong."""
        try:
            with httpx.Client(
                timeout=self.timeout, transport=self.transport, follow_redirects=True
            ) as client:
                with client.stream("GET", source) as response:
                    if not response.is_success:
                        raise ValueError(f"Media download failed (HTTP {response.status_code})")
                    data = self._read_chunks(response.iter_bytes(), max_bytes)
                    mime = response.headers.get("content-type", "").partition(";")[0]
                    return self._encode(
                        data, mime or mimetypes.guess_type(urlsplit(str(response.url)).path)[0]
                    )
        except httpx.HTTPError as error:
            raise ValueError("Media download failed or timed out") from error

    @classmethod
    def _read_chunks(cls, chunks: Iterable[bytes], max_bytes: int | None) -> bytes:
        """Stop a file or HTTP stream as soon as its decoded byte budget is exceeded."""
        buffer = bytearray()
        for chunk in chunks:
            if not chunk:
                continue
            cls._check_size(len(buffer) + len(chunk), max_bytes)
            buffer.extend(chunk)
        cls._check_size(len(buffer), max_bytes)
        return bytes(buffer)

    @staticmethod
    def _check_size(size: int, max_bytes: int | None) -> None:
        """Require nonempty media within any supplied decoded byte budget."""
        if size == 0:
            raise ValueError("Media is empty")
        if max_bytes is not None and size > max_bytes:
            raise ValueError(f"Media exceeds the remaining decoded byte limit ({max_bytes} bytes)")

    @classmethod
    def _load_base64(cls, source: str, max_bytes: int | None) -> LoadedMedia:
        """Preserve supplied base64 while validating its bytes and determining its MIME type."""
        mime: str | None = None
        encoded = source
        if source.startswith("data:"):
            header, separator, encoded = source.partition(",")
            if not separator or not header.endswith(";base64"):
                raise ValueError("Media data URLs must use base64 encoding")
            mime = header[5:-7]
        encoded = "".join(encoded.split())
        if max_bytes is not None and len(encoded) > 4 * ((max_bytes + 2) // 3):
            raise ValueError(f"Media exceeds the remaining decoded byte limit ({max_bytes} bytes)")
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("Invalid base64 media; use file:// for a local file") from error
        cls._check_size(len(data), max_bytes)
        resolved_mime = cls._mime_type(data, mime)
        return LoadedMedia(f"data:{resolved_mime};base64,{encoded}", len(data))

    @classmethod
    def _encode(cls, data: bytes, mime: str | None) -> LoadedMedia:
        """Infer a MIME type and encode downloaded or file contents exactly once."""
        resolved_mime = cls._mime_type(data, mime)
        return LoadedMedia(
            f"data:{resolved_mime};base64,{base64.b64encode(data).decode('ascii')}", len(data)
        )

    @staticmethod
    def _mime_type(data: bytes, hint: str | None) -> str:
        """Prefer binary signatures; accept an explicit MIME hint for unknown formats."""
        mime = filetype.guess_mime(data) or hint
        if not mime or mime == "application/octet-stream" or "/" not in mime:
            raise ValueError("Cannot determine media MIME type; supply a data:<MIME>;base64 URL")
        return MIME_ALIASES.get(mime.lower(), mime.lower())
