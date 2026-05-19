import asyncio
import uuid
from types import SimpleNamespace

from api.v1.ppt.endpoints import outlines as outlines_module
from api.v1.ppt.endpoints import presentation as presentation_module


class _FakeAsyncSession:
    def __init__(self, item):
        self._item = item

    async def get(self, *_args, **_kwargs):
        return self._item

    def add(self, *_args, **_kwargs):
        return None

    def add_all(self, *_args, **_kwargs):
        return None

    async def commit(self):
        return None

    async def execute(self, *_args, **_kwargs):
        return None


def _collect_stream_body(response) -> list[str]:
    async def _collect():
        chunks: list[str] = []
        async for chunk in response.body_iterator:
            if isinstance(chunk, bytes):
                chunks.append(chunk.decode("utf-8"))
            else:
                chunks.append(chunk)
        return chunks

    return asyncio.run(_collect())


def test_outlines_stream_returns_sse_error_for_unexpected_generator_failure(monkeypatch):
    presentation = SimpleNamespace(
        id=uuid.uuid4(),
        file_paths=None,
        n_slides=1,
        include_table_of_contents=False,
        include_title_slide=True,
        content="topic",
        language="English",
        tone="default",
        verbosity="standard",
        instructions=None,
        web_search=False,
        outlines=None,
        title=None,
        model_dump=lambda mode="json": {"id": "x"},
    )
    sql_session = _FakeAsyncSession(presentation)

    async def failing_outline_generator(*_args, **_kwargs):
        yield "partial"
        raise RuntimeError("stream exploded")

    monkeypatch.setattr(
        outlines_module,
        "get_outline_messages",
        lambda *_args, **_kwargs: [
            SimpleNamespace(content="sys"),
            SimpleNamespace(content="user"),
        ],
    )
    monkeypatch.setattr(
        outlines_module.MEM0_PRESENTATION_MEMORY_SERVICE,
        "store_generation_context",
        lambda *_args, **_kwargs: asyncio.sleep(0),
    )
    monkeypatch.setattr(
        outlines_module, "generate_ppt_outline", failing_outline_generator
    )

    response = asyncio.run(
        outlines_module.stream_outlines(presentation.id, sql_session=sql_session)
    )
    chunks = _collect_stream_body(response)
    joined = "".join(chunks)

    assert '"type": "chunk"' in joined
    assert '"type": "error"' in joined


def test_presentation_stream_returns_sse_error_for_unexpected_slide_failure(monkeypatch):
    presentation = SimpleNamespace(
        id=uuid.uuid4(),
        language="English",
        tone="default",
        verbosity="standard",
        instructions=None,
        structure={"slides": [0]},
        outlines={"slides": [{"content": "x"}]},
        get_structure=lambda: SimpleNamespace(slides=[0]),
        get_layout=lambda: SimpleNamespace(
            name="demo",
            slides=[SimpleNamespace(id="layout-1")],
        ),
        get_presentation_outline=lambda: SimpleNamespace(
            slides=[SimpleNamespace(content="## Intro")]
        ),
        model_dump=lambda mode="json": {"id": "x"},
    )
    sql_session = _FakeAsyncSession(presentation)

    async def raise_runtime(*_args, **_kwargs):
        raise RuntimeError("slide generation failed")

    monkeypatch.setattr(
        presentation_module,
        "get_slide_content_from_type_and_outline",
        raise_runtime,
    )
    monkeypatch.setenv("APP_DATA_DIRECTORY", "/tmp")

    response = asyncio.run(
        presentation_module.stream_presentation(presentation.id, sql_session=sql_session)
    )
    chunks = _collect_stream_body(response)
    joined = "".join(chunks)

    assert '"type": "chunk"' in joined
    assert '"type": "error"' in joined
