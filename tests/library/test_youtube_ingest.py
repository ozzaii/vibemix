# SPDX-License-Identifier: Apache-2.0
"""Unit tests for library.youtube_ingest — pure URL helpers + mocked ingest.

No network: the Gemini call goes through an injected FakeClient. Pass
``model="fake-model"`` to ingest_youtube so the model_router is never touched.
"""

from __future__ import annotations

import pytest

from vibemix.library import youtube_ingest as yt


# --------------------------------------------------------------------------- #
# fakes
# --------------------------------------------------------------------------- #


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class _FakeModels:
    def __init__(self, response: _FakeResponse | None = None, raises: bool = False):
        self._response = response
        self._raises = raises
        self.calls: list[dict] = []

    def generate_content(self, **kw):
        self.calls.append(kw)
        if self._raises:
            raise RuntimeError("boom from the API")
        return self._response


class _FakeClient:
    def __init__(self, response: _FakeResponse | None = None, raises: bool = False):
        self.models = _FakeModels(response=response, raises=raises)


# --------------------------------------------------------------------------- #
# is_youtube_url
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "http://youtube.com/watch?v=dQw4w9WgXcQ",
        "youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/shorts/dQw4w9WgXcQ",
        "https://www.youtube.com/watch?list=PL123&v=dQw4w9WgXcQ",
        "https://m.youtube.com/watch?v=dQw4w9WgXcQ",
    ],
)
def test_is_youtube_url_true(url: str) -> None:
    assert yt.is_youtube_url(url) is True


@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://vimeo.com/123456",
        "not a url at all",
        "https://youtube.com/feed/subscriptions",
        None,
    ],
)
def test_is_youtube_url_false(url) -> None:
    assert yt.is_youtube_url(url) is False


# --------------------------------------------------------------------------- #
# youtube_deep_link
# --------------------------------------------------------------------------- #


def test_deep_link_normalizes_watch_url() -> None:
    assert (
        yt.youtube_deep_link("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        == "https://youtu.be/dQw4w9WgXcQ"
    )


def test_deep_link_normalizes_shorts_and_youtu_be() -> None:
    assert (
        yt.youtube_deep_link("https://www.youtube.com/shorts/dQw4w9WgXcQ")
        == "https://youtu.be/dQw4w9WgXcQ"
    )
    assert yt.youtube_deep_link("youtu.be/dQw4w9WgXcQ") == "https://youtu.be/dQw4w9WgXcQ"


def test_deep_link_with_t_seconds() -> None:
    assert (
        yt.youtube_deep_link("https://youtu.be/dQw4w9WgXcQ", t_seconds=90)
        == "https://youtu.be/dQw4w9WgXcQ?t=90"
    )


def test_deep_link_ignores_nonpositive_or_bad_t() -> None:
    assert (
        yt.youtube_deep_link("https://youtu.be/dQw4w9WgXcQ", t_seconds=0)
        == "https://youtu.be/dQw4w9WgXcQ"
    )
    assert (
        yt.youtube_deep_link("https://youtu.be/dQw4w9WgXcQ", t_seconds=-5)
        == "https://youtu.be/dQw4w9WgXcQ"
    )


def test_deep_link_passthrough_on_unparseable() -> None:
    bad = "https://example.com/whatever"
    assert yt.youtube_deep_link(bad) == bad


# --------------------------------------------------------------------------- #
# build_youtube_part
# --------------------------------------------------------------------------- #


def test_build_youtube_part_returns_part_with_file_uri() -> None:
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    part = yt.build_youtube_part(url)
    assert part.file_data.file_uri == url
    # VideoMetadata fps default is the low audio-ish sampling rate.
    assert part.video_metadata.fps == pytest.approx(0.2)


def test_build_youtube_part_custom_fps() -> None:
    part = yt.build_youtube_part("https://youtu.be/dQw4w9WgXcQ", fps=1.0)
    assert part.video_metadata.fps == pytest.approx(1.0)


def test_build_youtube_part_raises_on_non_youtube() -> None:
    with pytest.raises(ValueError):
        yt.build_youtube_part("https://example.com/video")


# --------------------------------------------------------------------------- #
# ingest_youtube
# --------------------------------------------------------------------------- #


def test_ingest_success_path() -> None:
    client = _FakeClient(response=_FakeResponse("genre: techno, peak-time energy"))
    out = yt.ingest_youtube(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        client=client,
        model="fake-model",
    )
    assert out["available"] is True
    assert out["summary"] == "genre: techno, peak-time energy"
    assert out["url"] == "https://youtu.be/dQw4w9WgXcQ"
    assert "hint" in out["note"].lower()
    # The injected client was actually called with the resolved model.
    assert client.models.calls[0]["model"] == "fake-model"
    # contents = [youtube_part, text_part]
    contents = client.models.calls[0]["contents"]
    assert contents[0].file_data.file_uri == (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    )


def test_ingest_uses_custom_prompt() -> None:
    client = _FakeClient(response=_FakeResponse("ok"))
    yt.ingest_youtube(
        "https://youtu.be/dQw4w9WgXcQ",
        prompt="just the BPM please",
        client=client,
        model="fake-model",
    )
    text_part = client.models.calls[0]["contents"][1]
    assert text_part.text == "just the BPM please"


def test_ingest_non_youtube_url() -> None:
    client = _FakeClient(response=_FakeResponse("should not be called"))
    out = yt.ingest_youtube(
        "https://example.com/video", client=client, model="fake-model"
    )
    assert out["available"] is False
    assert out["error"] == "not a YouTube URL"
    assert client.models.calls == []


def test_ingest_no_client() -> None:
    out = yt.ingest_youtube(
        "https://youtu.be/dQw4w9WgXcQ", client=None, model="fake-model"
    )
    assert out["available"] is False
    assert "needs a Gemini client" in out["error"]


def test_ingest_client_raises_is_caught() -> None:
    client = _FakeClient(raises=True)
    out = yt.ingest_youtube(
        "https://youtu.be/dQw4w9WgXcQ", client=client, model="fake-model"
    )
    assert out["available"] is False
    assert "ingest failed" in out["error"]


def test_ingest_empty_text_is_unavailable() -> None:
    client = _FakeClient(response=_FakeResponse(""))
    out = yt.ingest_youtube(
        "https://youtu.be/dQw4w9WgXcQ", client=client, model="fake-model"
    )
    assert out["available"] is False
    assert "no text" in out["error"]
