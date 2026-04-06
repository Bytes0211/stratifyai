"""Extended tests for MCP connection lifecycle, Bedrock validator, MCP server entrypoints, and RAG pipeline."""

import asyncio
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class _AsyncContext:
    """Simple async context manager for tests."""

    def __init__(self, value):
        self.value = value

    async def __aenter__(self):
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        return False


# ---------------------------------------------------------------------------
# mcp_client/connection.py
# ---------------------------------------------------------------------------
class TestMCPConnectionExtra:
    def _config(self):
        from stratifyai.mcp_client.config import ConfiguredServer

        return ConfiguredServer(server_id="demo", command="echo", args=["hi"], env={})

    def test_session_property_raises_when_uninitialized(self):
        from stratifyai.mcp_client.connection import MCPServerConnection

        conn = MCPServerConnection(self._config())
        with pytest.raises(RuntimeError, match="Session not initialized"):
            _ = conn.session

    @pytest.mark.asyncio
    async def test_connect_returns_existing_session(self):
        from stratifyai.mcp_client.connection import MCPServerConnection

        conn = MCPServerConnection(self._config())
        existing = MagicMock()
        conn._session = existing
        result = await conn.connect()
        assert result is existing

    @pytest.mark.asyncio
    async def test_connect_run_probe_and_close_success(self):
        from stratifyai.mcp_client.connection import MCPServerConnection

        session = MagicMock()
        session.initialize = AsyncMock()
        session.list_tools = AsyncMock(return_value=[])

        conn = MCPServerConnection(self._config())

        with (
            patch(
                "stratifyai.mcp_client.connection.stdio_client",
                return_value=_AsyncContext(("read", "write")),
            ),
            patch(
                "stratifyai.mcp_client.connection.ClientSession",
                return_value=_AsyncContext(session),
            ),
        ):
            result = await conn.connect()
            assert result is session
            latency = await conn.probe()
            assert latency >= 0
            await conn.close()
            assert conn._session is None

    @pytest.mark.asyncio
    async def test_connect_raises_when_run_fails(self):
        from stratifyai.mcp_client.connection import MCPServerConnection

        conn = MCPServerConnection(self._config())

        async def broken_run():
            conn._connect_error = RuntimeError("boom")
            conn._ready.set()

        conn._run = broken_run  # type: ignore[method-assign]

        with pytest.raises(RuntimeError, match="boom"):
            await conn.connect()

    @pytest.mark.asyncio
    async def test_close_cancels_task_on_timeout(self):
        from stratifyai.mcp_client.connection import MCPServerConnection

        conn = MCPServerConnection(self._config())
        conn._close_event = asyncio.Event()

        async def sleeper():
            await asyncio.sleep(10)

        conn._task = asyncio.create_task(sleeper())

        with patch("asyncio.wait_for", side_effect=asyncio.TimeoutError):
            await conn.close()

        assert conn._task is None
        assert conn._close_event is None


# ---------------------------------------------------------------------------
# utils/bedrock_validator.py
# ---------------------------------------------------------------------------
class TestBedrockValidatorExtra:
    def test_validate_bedrock_models_boto3_missing(self):
        from stratifyai.utils import bedrock_validator as mod

        with patch.object(mod, "BOTO3_AVAILABLE", False):
            result = mod.validate_bedrock_models(["a", "b"])

        assert result["error"] == "boto3 not installed"
        assert result["valid_models"] == ["a", "b"]

    def test_validate_bedrock_models_success(self):
        from stratifyai.utils import bedrock_validator as mod

        mock_client = MagicMock()
        mock_client.list_foundation_models.return_value = {
            "modelSummaries": [{"modelId": "model-1"}, {"modelId": "model-2"}]
        }

        with (
            patch.object(mod, "BOTO3_AVAILABLE", True),
            patch.object(mod, "boto3") as mock_boto3,
        ):
            mock_boto3.client.return_value = mock_client
            result = mod.validate_bedrock_models(
                ["model-1", "missing"], region_name="us-east-1"
            )

        assert result["error"] is None
        assert "model-1" in result["valid_models"]
        assert "missing" in result["invalid_models"]

    def test_validate_bedrock_models_generic_error(self):
        from stratifyai.utils import bedrock_validator as mod

        with (
            patch.object(mod, "BOTO3_AVAILABLE", True),
            patch.object(mod, "boto3") as mock_boto3,
        ):
            mock_boto3.client.side_effect = Exception("kaput")
            result = mod.validate_bedrock_models(["model-1"])

        assert "Validation failed" in result["error"]
        assert result["valid_models"] == ["model-1"]

    def test_get_validated_interactive_models(self):
        from stratifyai.utils import bedrock_validator as mod

        fake_validation = {
            "valid_models": ["amazon.nova-pro-v1:0"],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }
        with patch.object(mod, "validate_bedrock_models", return_value=fake_validation):
            result = mod.get_validated_interactive_models()

        assert "models" in result
        assert "validation_result" in result
        assert result["validation_result"] == fake_validation


# ---------------------------------------------------------------------------
# mcp_server entrypoints
# ---------------------------------------------------------------------------
class TestMCPServerEntrypoints:
    def test_create_server_returns_mcp(self):
        from stratifyai.mcp_server import create_server

        fake_mcp = MagicMock()
        fake_module = SimpleNamespace(mcp=fake_mcp)

        with patch.dict(sys.modules, {"stratifyai.mcp_server.server": fake_module}):
            result = create_server()

        assert result is fake_mcp

    def test_main_uses_default_stdio_transport(self):
        from stratifyai.mcp_server.__main__ import main

        fake_mcp = MagicMock()
        fake_module = SimpleNamespace(mcp=fake_mcp)

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(transport="stdio"),
            ),
            patch.dict(sys.modules, {"stratifyai.mcp_server.server": fake_module}),
        ):
            main()

        fake_mcp.run.assert_called_once_with(transport="stdio")

    def test_main_uses_streamable_http_transport(self):
        from stratifyai.mcp_server.__main__ import main

        fake_mcp = MagicMock()
        fake_module = SimpleNamespace(mcp=fake_mcp)

        with (
            patch(
                "argparse.ArgumentParser.parse_args",
                return_value=SimpleNamespace(transport="streamable-http"),
            ),
            patch.dict(sys.modules, {"stratifyai.mcp_server.server": fake_module}),
        ):
            main()

        fake_mcp.run.assert_called_once_with(transport="streamable-http")


# ---------------------------------------------------------------------------
# rag.py
# ---------------------------------------------------------------------------
class TestRAGExtra:
    def _make_client(self):
        from stratifyai.rag import RAGClient

        embedding_provider = MagicMock()
        llm_client = MagicMock()
        vectordb = MagicMock()

        with patch("stratifyai.rag.VectorDBClient", return_value=vectordb):
            client = RAGClient(
                embedding_provider=embedding_provider,
                llm_client=llm_client,
                persist_directory="/tmp/test-chroma",
            )

        client.vectordb = vectordb
        return client, vectordb

    @pytest.mark.asyncio
    async def test_index_file_not_found(self):
        client, _ = self._make_client()

        with pytest.raises(FileNotFoundError):
            await client.index_file("/definitely/missing/file.txt", "demo")

    @pytest.mark.asyncio
    async def test_index_file_success(self, tmp_path):
        client, vectordb = self._make_client()
        vectordb.add_documents = AsyncMock()

        file_path = tmp_path / "sample.txt"
        file_path.write_text("Hello world\n" * 100, encoding="utf-8")

        result = await client.index_file(str(file_path), "demo")
        assert result.collection_name == "demo"
        assert result.num_files == 1
        assert result.num_chunks >= 1

    @pytest.mark.asyncio
    async def test_index_directory_invalid_dir(self):
        client, _ = self._make_client()

        with pytest.raises(ValueError, match="Invalid directory"):
            await client.index_directory("/definitely/missing/dir", "demo")

    @pytest.mark.asyncio
    async def test_index_directory_no_matching_files(self, tmp_path):
        from stratifyai.exceptions import LLMAbstractionError

        client, _ = self._make_client()

        with pytest.raises(LLMAbstractionError, match="No files found"):
            await client.index_directory(str(tmp_path), "demo", file_patterns=["*.xyz"])

    @pytest.mark.asyncio
    async def test_index_directory_continues_on_file_error(self, tmp_path):
        client, _ = self._make_client()

        (tmp_path / "a.txt").write_text("A", encoding="utf-8")
        (tmp_path / "b.txt").write_text("B", encoding="utf-8")

        async def fake_index_file(
            file_path, collection_name, chunk_size=1000, overlap=200
        ):
            if file_path.endswith("a.txt"):
                raise RuntimeError("boom")
            from stratifyai.rag import IndexingResult

            return IndexingResult(collection_name, 2, 1, 10, 0.0)

        client.index_file = fake_index_file  # type: ignore[method-assign]

        result = await client.index_directory(
            str(tmp_path), "demo", file_patterns=["*.txt"]
        )
        assert result.num_files == 2
        assert result.num_chunks == 2

    @pytest.mark.asyncio
    async def test_query_no_results_raises(self):
        from stratifyai.exceptions import LLMAbstractionError

        client, vectordb = self._make_client()
        vectordb.query = AsyncMock(return_value=[])

        with pytest.raises(LLMAbstractionError, match="No results found"):
            await client.query("demo", "what is this?")

    @pytest.mark.asyncio
    async def test_query_success_with_sources(self):
        from stratifyai.vectordb import SearchResult

        client, vectordb = self._make_client()
        vectordb.query = AsyncMock(
            return_value=[
                SearchResult(
                    document="Important fact",
                    metadata={"filename": "notes.txt", "chunk_idx": 1},
                    distance=0.2,
                    doc_id="doc1",
                )
            ]
        )

        fake_response = MagicMock()
        fake_response.content = "Answer from sources"
        fake_response.model = "gpt-4o-mini"
        fake_response.usage = SimpleNamespace(cost_usd=0.12)

        fake_llm_client = MagicMock()
        fake_llm_client.chat_completion = AsyncMock(return_value=fake_response)

        with patch("stratifyai.rag.LLMClient", return_value=fake_llm_client):
            result = await client.query("demo", "question?")

        assert result.content == "Answer from sources"
        assert result.num_chunks_retrieved == 1
        assert result.sources[0]["file"] == "notes.txt"

    def test_list_delete_and_stats(self):
        client, vectordb = self._make_client()
        vectordb.list_collections.return_value = ["demo"]
        vectordb.get_collection_count.return_value = 3
        vectordb.get_documents.return_value = [
            {"metadata": {"filename": "a.txt"}},
            {"metadata": {"filename": "b.txt"}},
            {"metadata": {"filename": "a.txt"}},
        ]

        assert client.list_collections() == ["demo"]
        client.delete_collection("demo")
        vectordb.delete_collection.assert_called_once_with("demo")

        stats = client.get_collection_stats("demo")
        assert stats["num_chunks"] == 3
        assert stats["num_files"] == 2

    @pytest.mark.asyncio
    async def test_retrieve_only(self):
        from stratifyai.vectordb import SearchResult

        client, vectordb = self._make_client()
        vectordb.query = AsyncMock(
            return_value=[
                SearchResult(
                    document="doc",
                    metadata={},
                    distance=0.1,
                    doc_id="1",
                )
            ]
        )

        result = await client.retrieve_only("demo", "hello")
        assert len(result) == 1
        assert result[0].doc_id == "1"
