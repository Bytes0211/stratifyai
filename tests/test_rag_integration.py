"""Integration-style tests for the local RAG pipeline."""

from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stratifyai.embeddings import EmbeddingProvider, EmbeddingResult
from stratifyai.exceptions import LLMAbstractionError
from stratifyai.models import ChatResponse, Usage
from stratifyai.rag import RAGClient
from stratifyai.vectordb import SearchResult


class FakeEmbeddingProvider(EmbeddingProvider):
    """Small deterministic embedding provider for local RAG tests."""

    async def generate_embeddings(
        self, texts: list[str], model: str | None = None
    ) -> EmbeddingResult:
        keywords = ("housing", "mortgage", "zoning")
        embeddings = [
            [float(text.lower().count(keyword)) for keyword in keywords]
            for text in texts
        ]
        total_tokens = sum(len(text.split()) for text in texts)
        return EmbeddingResult(
            embeddings=embeddings,
            model=model or "fake-embed",
            total_tokens=total_tokens,
            cost=0.0,
        )

    def get_embedding_dimension(self, model: str) -> int:
        return 3


class FakeVectorDBClient:
    """In-memory vector DB used to exercise RAGClient without ChromaDB."""

    def __init__(self, embedding_provider, persist_directory=None):
        self.embedding_provider = embedding_provider
        self.persist_directory = persist_directory
        self.collections: dict[str, list[dict[str, object]]] = {}

    async def add_documents(
        self,
        collection_name: str,
        documents: list[str],
        metadatas: list[dict] | None = None,
        ids: list[str] | None = None,
    ) -> list[str]:
        if ids is None:
            ids = [f"doc-{idx}" for idx in range(len(documents))]
        if metadatas is None:
            metadatas = [{} for _ in documents]

        embeddings = (
            await self.embedding_provider.generate_embeddings(documents)
        ).embeddings
        collection = self.collections.setdefault(collection_name, [])
        for idx, document in enumerate(documents):
            collection.append(
                {
                    "id": ids[idx],
                    "document": document,
                    "metadata": metadatas[idx],
                    "embedding": embeddings[idx],
                }
            )
        return ids

    async def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: dict | None = None,
    ) -> list[SearchResult]:
        query_embedding = (
            await self.embedding_provider.generate_embeddings([query_text])
        ).embeddings[0]
        matches = []
        for item in self.collections.get(collection_name, []):
            embedding = item["embedding"]
            distance = sum(
                abs(a - b) for a, b in zip(query_embedding, embedding, strict=False)
            )
            matches.append(
                SearchResult(
                    document=item["document"],
                    metadata=item["metadata"],
                    distance=distance,
                    doc_id=item["id"],
                )
            )
        return sorted(matches, key=lambda item: item.distance)[:n_results]

    def list_collections(self) -> list[str]:
        return list(self.collections.keys())

    def delete_collection(self, collection_name: str) -> None:
        self.collections.pop(collection_name, None)

    def get_collection_count(self, collection_name: str) -> int:
        return len(self.collections.get(collection_name, []))

    def get_documents(self, collection_name: str, ids=None, where=None, limit=None):
        docs = [
            {
                "id": item["id"],
                "document": item["document"],
                "metadata": item["metadata"],
            }
            for item in self.collections.get(collection_name, [])
        ]
        return docs[:limit] if limit is not None else docs

    def get_or_create_collection(self, name: str):
        return self.collections.setdefault(name, [])


def _make_chat_response(content: str, cost: float = 0.123) -> ChatResponse:
    return ChatResponse(
        id="rag-1",
        model="gpt-4o-mini",
        content=content,
        finish_reason="stop",
        usage=Usage(
            prompt_tokens=30,
            completion_tokens=12,
            total_tokens=42,
            cost_usd=cost,
        ),
        provider="openai",
        created_at=datetime.now(),
        raw_response={},
    )


@pytest.mark.asyncio
async def test_rag_index_file_and_retrieve_only_round_trip(tmp_path: Path):
    file_path = tmp_path / "housing.md"
    file_path.write_text(
        "Housing supply is constrained by zoning.\n"
        "Mortgage rates influence housing demand.",
        encoding="utf-8",
    )

    with patch("stratifyai.rag.VectorDBClient", FakeVectorDBClient):
        rag = RAGClient(
            embedding_provider=FakeEmbeddingProvider(),
            llm_client=MagicMock(),
            persist_directory=str(tmp_path / "chroma"),
        )

        result = await rag.index_file(
            str(file_path),
            collection_name="housing_docs",
            chunk_size=40,
            overlap=0,
        )

        retrieved = await rag.retrieve_only(
            "housing_docs", "mortgage demand", n_results=2
        )
        stats = rag.get_collection_stats("housing_docs")

    assert result.collection_name == "housing_docs"
    assert result.num_chunks >= 2
    assert retrieved
    assert any("mortgage" in item.document.lower() for item in retrieved)
    assert stats["name"] == "housing_docs"
    assert "housing.md" in stats["sample_files"]


@pytest.mark.asyncio
async def test_rag_query_returns_sources_and_total_cost(tmp_path: Path):
    file_path = tmp_path / "market.txt"
    file_path.write_text(
        "Housing affordability improved as mortgage rates stabilized.",
        encoding="utf-8",
    )

    with patch("stratifyai.rag.VectorDBClient", FakeVectorDBClient):
        rag = RAGClient(
            embedding_provider=FakeEmbeddingProvider(),
            llm_client=MagicMock(),
            persist_directory=str(tmp_path / "chroma_query"),
        )
        await rag.index_file(str(file_path), collection_name="market_docs", overlap=0)

    with (
        patch("stratifyai.rag.VectorDBClient", FakeVectorDBClient),
        patch("stratifyai.rag.LLMClient") as mock_llm_class,
    ):
        mock_llm = MagicMock()
        mock_llm.chat_completion = AsyncMock(
            return_value=_make_chat_response("Rates stabilized the market.", cost=0.321)
        )
        mock_llm_class.return_value = mock_llm

        response = await rag.query(
            collection_name="market_docs",
            query="What happened to mortgage rates?",
            provider="openai",
            model="gpt-4o-mini",
            n_results=1,
        )

    assert response.content == "Rates stabilized the market."
    assert response.total_cost == pytest.approx(0.321)
    assert response.num_chunks_retrieved == 1
    assert response.sources[0]["file"] == "market.txt"
    request = mock_llm.chat_completion.await_args.kwargs["request"]
    assert "Sources:" in request.messages[0].content
    assert "What happened to mortgage rates?" in request.messages[0].content


@pytest.mark.asyncio
async def test_rag_query_raises_when_collection_has_no_results(tmp_path: Path):
    with patch("stratifyai.rag.VectorDBClient", FakeVectorDBClient):
        rag = RAGClient(
            embedding_provider=FakeEmbeddingProvider(),
            llm_client=MagicMock(),
            persist_directory=str(tmp_path / "empty_chroma"),
        )
        rag.vectordb.get_or_create_collection("empty_docs")

        with pytest.raises(LLMAbstractionError, match="No results found"):
            await rag.query("empty_docs", "unknown topic")
