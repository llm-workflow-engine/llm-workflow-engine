"""Exercise media resolution and provider-defined budgets without external I/O."""

from __future__ import annotations

import base64
from pathlib import Path
from collections.abc import Iterator

import httpx
import pytest

from lwe.decisions import (
    CombinedMediaLimit,
    DecisionRequest,
    MediaLimits,
    MediaLoader,
    MediaPolicy,
    Noul,
)

PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
)


def test_media_sources_resolve_consistently_and_check_mode_does_no_io(tmp_path: Path) -> None:
    """Files, redirected downloads, data URLs, and raw base64 share one wire format."""
    data = base64.b64decode(PNG_BASE64)
    path = tmp_path / "image with spaces.png"
    path.write_bytes(data)
    calls: list[str] = []

    def respond(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        assert "authorization" not in request.headers
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "/image"})
        return httpx.Response(200, content=data)

    loader = MediaLoader(transport=httpx.MockTransport(respond))
    policy = MediaPolicy(
        {"images": MediaLimits(frozenset({"image/png"}), 5, len(data), 5 * len(data))}
    )
    data_url = f"data:image/png;base64,{PNG_BASE64}"
    request = DecisionRequest(
        state="Inspect",
        questions={"q": Noul(instructions="Q?")},
        images=[
            "https://media.example/redirect",
            path.as_uri(),
            PNG_BASE64,
            data_url,
            path.as_uri(),
        ],
    )
    assert request.validate_media(policy, loader=loader).images[:2] == request.images[:2]
    assert calls == []
    missing = request.model_copy(update={"images": [(tmp_path / "missing.png").as_uri()]})
    missing.validate_media(policy, loader=loader)
    with pytest.raises(ValueError, match="file does not exist"):
        missing.validate_media(policy, loader=loader, resolve=True)
    resolved = request.validate_media(policy, loader=loader, resolve=True)
    assert resolved.images == [data_url] * 5
    assert calls == ["/redirect", "/image"]
    assert request.images[0].startswith("https://")
    with pytest.raises(ValueError, match="Invalid base64"):
        loader.load("not-base64!")
    with pytest.raises(ValueError, match="absolute local file URI"):
        loader.load("file://remote-host/image.png")


def test_media_limits_apply_to_decoded_bytes_and_shared_budgets() -> None:
    """Core honors plugin policies without imposing Cloudflare counts or sizes."""
    loader = MediaLoader()
    policy = MediaPolicy(
        {
            "audio": MediaLimits(frozenset({"audio/wav"}), 2, 4),
            "videos": MediaLimits(frozenset({"video/mp4"}), 2, 4),
        },
        (CombinedMediaLimit(("audio", "videos"), 5),),
    )
    audio = "data:audio/wav;base64,eHl6"
    video = "data:video/mp4;base64,eHl6"
    assert loader.validate_media({"audio": [audio]}, policy)["audio"] == [audio]
    for media, message in [
        ({"audio": [audio] * 3}, "Too many"),
        ({"audio": ["data:audio/wav;base64,eHl6MDE="]}, "decoded byte limit"),
        ({"audio": [audio], "videos": [video]}, "decoded byte limit"),
        ({"audio": [video]}, "Unsupported MIME"),
        ({"images": [video]}, "does not support images"),
    ]:
        with pytest.raises(ValueError, match=message):
            loader.validate_media(media, policy)


def test_download_failures_and_oversized_streams_stop_loading() -> None:
    """Enforce limits during download even without a trustworthy Content-Length."""
    consumed: list[int] = []

    class Chunks(httpx.SyncByteStream):
        """An unknown-length stream whose third chunk must never be consumed."""

        def __iter__(self) -> Iterator[bytes]:
            for i in range(3):
                consumed.append(i)
                yield b"xxxx"

    loader = MediaLoader(
        transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Chunks()))
    )
    with pytest.raises(ValueError, match="decoded byte limit"):
        loader.load("https://media.example/large", max_bytes=4)
    assert consumed == [0, 1]
    loader = MediaLoader(transport=httpx.MockTransport(lambda request: httpx.Response(404)))
    with pytest.raises(ValueError, match="HTTP 404"):
        loader.load("https://media.example/missing")
