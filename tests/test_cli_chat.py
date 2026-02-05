"""Unit tests for CLI chat command and _chat_impl function."""

import pytest
from unittest.mock import MagicMock, patch, mock_open, call
from pathlib import Path
from datetime import datetime
from typer.testing import CliRunner

from cli.stratifyai_cli import app, _chat_impl
from stratifyai.models import Message, ChatRequest, ChatResponse, Usage


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_client():
    """Create a mock LLMClient."""
    with patch('cli.stratifyai_cli.LLMClient') as mock:
        client_instance = MagicMock()
        mock.return_value = client_instance
        
        # Setup default response
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Test response",
            finish_reason="stop",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        yield mock, client_instance


@pytest.fixture
def mock_prompt():
    """Mock Rich Prompt.ask."""
    with patch('cli.stratifyai_cli.Prompt.ask') as mock:
        yield mock


@pytest.fixture
def mock_console():
    """Mock Rich console."""
    with patch('cli.stratifyai_cli.console') as mock:
        yield mock


class TestChatCommand:
    """Tests for the chat command."""
    
    def test_chat_invokes_chat_impl_with_initial_parameters(
        self, runner, mock_client, mock_prompt, mock_console
    ):
        """Test that chat command correctly invokes _chat_impl with initial parameters."""
        # Setup mocks
        mock_prompt.side_effect = ["4"]  # Exit immediately
        
        # Capture the request when chat_completion_stream is called
        captured_request = []
        
        def mock_stream(request):
            # Capture a copy of the request before messages are modified
            captured_request.append(ChatRequest(
                model=request.model,
                messages=request.messages.copy(),  # Copy the messages list
                temperature=request.temperature,
                max_tokens=request.max_tokens
            ))
            chunk = MagicMock()
            chunk.content = "Test response"
            yield chunk
        
        mock_client[1].chat_completion_stream.side_effect = mock_stream
        
        # Run command with all parameters (with stream)
        result = runner.invoke(app, [
            'chat',
            'Hello, world!',
            '--provider', 'openai',
            '--model', 'gpt-4.1-mini',
            '--temperature', '0.7',
            '--max-tokens', '100',
            '--stream'
        ])
        
        # Verify the command executed successfully
        assert result.exit_code == 0
        
        # Verify LLMClient was created with correct provider
        mock_client[0].assert_called_once_with(provider='openai')
        
        # Verify the captured request
        assert len(captured_request) == 1
        request = captured_request[0]
        assert isinstance(request, ChatRequest)
        assert request.model == 'gpt-4.1-mini'
        assert request.temperature == 0.7
        assert request.max_tokens == 100
        assert len(request.messages) == 1
        assert request.messages[0].content == 'Hello, world!'
    
    def test_chat_with_system_message(
        self, runner, mock_client, mock_prompt, mock_console
    ):
        """Test chat command with system message parameter."""
        mock_prompt.side_effect = ["4"]  # Exit immediately
        
        # Capture the request when chat_completion is called
        captured_request = []
        
        def capture_request(request):
            # Capture a copy of the messages before they're modified
            captured_request.append(ChatRequest(
                model=request.model,
                messages=request.messages.copy(),
                temperature=request.temperature
            ))
            return mock_client[1].chat_completion_sync.return_value
        
        mock_client[1].chat_completion_sync.side_effect = capture_request
        
        # Patch MODEL_CATALOG to avoid interactive temperature prompt
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {'openai': {'gpt-4.1-mini': {'context': 128000}}}):
            result = runner.invoke(app, [
                'chat',
                'Hello',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--temperature', '0.7',  # Explicitly provide temperature
                '--system', 'You are a helpful assistant.'
            ])
        
        assert result.exit_code == 0
        
        # Verify the captured request
        assert len(captured_request) == 1
        request = captured_request[0]
        assert len(request.messages) == 2
        assert request.messages[0].role == 'system'
        assert request.messages[0].content == 'You are a helpful assistant.'
        assert request.messages[1].role == 'user'
        assert request.messages[1].content == 'Hello'


class TestChatImplSingleTurn:
    """Tests for _chat_impl single-turn conversation."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_single_turn_conversation_with_exit(
        self, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl handles a single-turn conversation and exits correctly."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Hello! How can I help?",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        # User chooses to exit immediately (option 4)
        mock_prompt.return_value = "4"
        
        # Execute
        _chat_impl(
            message="Hello",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify chat_completion was called once
        assert client_instance.chat_completion_sync.call_count == 1
        
        # Verify exit message was printed
        mock_console.print.assert_any_call("[dim]Goodbye![/dim]")
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_exit_without_save(
        self, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl exits gracefully without saving when 'Exit' is chosen."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Test response",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        # User chooses option 4 (Exit)
        mock_prompt.return_value = "4"
        
        # Execute with mock file operations
        with patch('builtins.open', mock_open()) as mock_file:
            _chat_impl(
                message="Test message",
                provider="openai",
                model="gpt-4.1-mini",
                temperature=0.7,
                max_tokens=None,
                stream=False,
                system=None,
                file=None,
                cache_control=False
            )
            
            # Verify file was NOT opened (no save)
            mock_file.assert_not_called()
        
        # Verify goodbye message
        mock_console.print.assert_any_call("[dim]Goodbye![/dim]")


class TestChatImplMultiTurn:
    """Tests for _chat_impl multi-turn conversation."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_maintains_conversation_history_across_turns(
        self, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl correctly maintains conversation history across multiple turns."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Create two different responses
        mock_response_1 = ChatResponse(
            id="test-id-1",
            model="gpt-4.1-mini",
            content="First response",
            finish_reason="stop",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        
        mock_response_2 = ChatResponse(
            id="test-id-2",
            model="gpt-4.1-mini",
            content="Second response",
            finish_reason="stop",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            usage=Usage(
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30,
                cost_usd=0.0002,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        
        # Capture requests to verify conversation history
        captured_requests = []
        
        def capture_and_respond(request):
            # Deep copy messages to capture state at call time
            captured_requests.append([Message(role=m.role, content=m.content) for m in request.messages])
            if len(captured_requests) == 1:
                return mock_response_1
            else:
                return mock_response_2
        
        client_instance.chat_completion_sync.side_effect = capture_and_respond
        
        # Mock prompts: first "1" (continue), then user input, then "4" (exit)
        mock_prompt.side_effect = ["1", "Second message", "4"]
        
        # Execute
        _chat_impl(
            message="First message",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify chat_completion was called twice
        assert client_instance.chat_completion_sync.call_count == 2
        
        # Verify first call had only the first user message
        assert len(captured_requests) == 2
        assert len(captured_requests[0]) == 1
        assert captured_requests[0][0].content == "First message"
        
        # Verify second call had full conversation history
        # After first turn: [user: "First message", assistant: "First response"]
        # Second turn adds: [user: "Second message"]
        # So total should be 3 messages
        assert len(captured_requests[1]) == 3
        assert captured_requests[1][0].role == "user"
        assert captured_requests[1][0].content == "First message"
        assert captured_requests[1][1].role == "assistant"
        assert captured_requests[1][1].content == "First response"
        assert captured_requests[1][2].role == "user"
        assert captured_requests[1][2].content == "Second message"


class TestChatImplSave:
    """Tests for _chat_impl save functionality."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open)
    @patch('cli.stratifyai_cli.datetime')
    def test_saves_conversation_on_save_and_exit(
        self, mock_datetime, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl saves full conversation history when 'Save & exit' is chosen."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Test response",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y%m%d_%H%M%S": "20260201_120000",
            "%Y-%m-%d %H:%M:%S": "2026-02-01 12:00:00"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # User chooses option 3 (Save & exit), then provides filename
        mock_prompt.side_effect = ["3", "test_conversation.md"]
        
        # Execute
        _chat_impl(
            message="Hello, world!",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify file was opened for writing
        mock_file.assert_called_once_with("test_conversation.md", "w")
        
        # Get the file handle
        handle = mock_file()
        
        # Verify content was written
        write_calls = handle.write.call_args_list
        written_content = ''.join([call[0][0] for call in write_calls])
        
        # Verify structure
        assert "# LLM Response" in written_content
        assert "**Provider:** openai" in written_content
        assert "**Model:** gpt-4.1-mini" in written_content
        assert "**Timestamp:** 2026-02-01 12:00:00" in written_content
        assert "## Conversation" in written_content
        assert "**You:** Hello, world!" in written_content
        assert "**Assistant:** Test response" in written_content
        
        # Verify success message
        mock_console.print.assert_any_call("[green]✓ Saved to test_conversation.md[/green]")
        
        # Verify goodbye message
        mock_console.print.assert_any_call("[dim]Goodbye![/dim]")
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open)
    @patch('cli.stratifyai_cli.datetime')
    def test_saves_and_continues_conversation(
        self, mock_datetime, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl saves conversation and continues when 'Save & continue' is chosen."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response_1 = ChatResponse(
            id="test-id-1",
            model="gpt-4.1-mini",
            content="First response",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=10,
                completion_tokens=5,
                total_tokens=15,
                cost_usd=0.0001,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        
        mock_response_2 = ChatResponse(
            id="test-id-2",
            model="gpt-4.1-mini",
            content="Second response",
            provider="openai",
            created_at=datetime.now(),
            raw_response={},
            finish_reason="stop",
            usage=Usage(
                prompt_tokens=20,
                completion_tokens=10,
                total_tokens=30,
                cost_usd=0.0002,
                cached_tokens=0,
                cache_creation_tokens=0,
                cache_read_tokens=0
            )
        )
        
        # Capture requests
        captured_requests = []
        
        def capture_and_respond(request):
            captured_requests.append([Message(role=m.role, content=m.content) for m in request.messages])
            if len(captured_requests) == 1:
                return mock_response_1
            else:
                return mock_response_2
        
        client_instance.chat_completion_sync.side_effect = capture_and_respond
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y%m%d_%H%M%S": "20260201_120000",
            "%Y-%m-%d %H:%M:%S": "2026-02-01 12:00:00"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # User: Save & continue (2), filename, next message, then exit (4)
        mock_prompt.side_effect = ["2", "saved.md", "Follow-up", "4"]
        
        # Execute
        _chat_impl(
            message="First message",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify file was saved
        mock_file.assert_called_once_with("saved.md", "w")
        
        # Verify chat_completion was called twice (once for initial, once for follow-up)
        assert client_instance.chat_completion_sync.call_count == 2
        
        # Verify second call includes full conversation history
        # After first turn and save: [user: "First message", assistant: "First response"]
        # Second turn adds: [user: "Follow-up"]
        # Total: 3 messages
        assert len(captured_requests) == 2
        assert len(captured_requests[1]) == 3
        assert captured_requests[1][0].role == "user"
        assert captured_requests[1][0].content == "First message"
        assert captured_requests[1][1].role == "assistant"
        assert captured_requests[1][1].content == "First response"
        assert captured_requests[1][2].role == "user"
        assert captured_requests[1][2].content == "Follow-up"
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open)
    @patch('cli.stratifyai_cli.datetime')
    def test_saves_multi_turn_conversation_history(
        self, mock_datetime, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl saves the full conversation history across multiple turns."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Three responses for three turns
        mock_response_1 = ChatResponse(
            id="test-id-1", model="gpt-4.1-mini", content="Response 1",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.0001,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        mock_response_2 = ChatResponse(
            id="test-id-2", model="gpt-4.1-mini", content="Response 2",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=20, completion_tokens=10, total_tokens=30, cost_usd=0.0002,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        mock_response_3 = ChatResponse(
            id="test-id-3", model="gpt-4.1-mini", content="Response 3",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=30, completion_tokens=15, total_tokens=45, cost_usd=0.0003,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        
        client_instance.chat_completion_sync.side_effect = [mock_response_1, mock_response_2, mock_response_3]
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y%m%d_%H%M%S": "20260201_120000",
            "%Y-%m-%d %H:%M:%S": "2026-02-01 12:00:00"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # User: Continue (1), Message 2, Continue (1), Message 3, Save & exit (3), filename
        mock_prompt.side_effect = ["1", "Message 2", "1", "Message 3", "3", "multi_turn.md"]
        
        # Execute
        _chat_impl(
            message="Message 1",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify file was saved
        mock_file.assert_called_once_with("multi_turn.md", "w")
        
        # Get written content
        handle = mock_file()
        write_calls = handle.write.call_args_list
        written_content = ''.join([call[0][0] for call in write_calls])
        
        # Verify all messages are in the saved file
        assert "**You:** Message 1" in written_content
        assert "**Assistant:** Response 1" in written_content
        assert "**You:** Message 2" in written_content
        assert "**Assistant:** Response 2" in written_content
        assert "**You:** Message 3" in written_content
        assert "**Assistant:** Response 3" in written_content
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open)
    @patch('cli.stratifyai_cli.datetime')
    def test_adds_md_extension_if_missing(
        self, mock_datetime, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl adds .md extension if not provided."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id", model="gpt-4.1-mini", content="Test response",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.0001,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        # Mock datetime
        mock_now = MagicMock()
        mock_now.strftime.side_effect = lambda fmt: {
            "%Y%m%d_%H%M%S": "20260201_120000",
            "%Y-%m-%d %H:%M:%S": "2026-02-01 12:00:00"
        }[fmt]
        mock_datetime.now.return_value = mock_now
        
        # User provides filename without .md extension
        mock_prompt.side_effect = ["3", "myfile"]
        
        # Execute
        _chat_impl(
            message="Test",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=None,
            cache_control=False
        )
        
        # Verify file was opened with .md extension added
        mock_file.assert_called_once_with("myfile.md", "w")
        mock_console.print.assert_any_call("[green]✓ Saved to myfile.md[/green]")


class TestChatImplFileInput:
    """Tests for _chat_impl file input functionality."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open, read_data="File content here")
    def test_loads_content_from_file(
        self, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl correctly loads content from file."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id", model="gpt-4.1-mini", content="Response",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.0001,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        mock_prompt.return_value = "4"  # Exit
        
        # Execute with file
        test_file_path = Path("/tmp/test.txt")
        _chat_impl(
            message=None,
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=test_file_path,
            cache_control=False
        )
        
        # Verify file was read
        mock_file.assert_any_call(test_file_path, 'r', encoding='utf-8')
        
        # Verify message content includes file content
        call_args = client_instance.chat_completion_sync.call_args
        request = call_args[0][0]
        assert "File content here" in request.messages[0].content
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    @patch('builtins.open', new_callable=mock_open, read_data="File content")
    def test_combines_message_and_file_content(
        self, mock_file, mock_client_class, mock_prompt, mock_console
    ):
        """Test that _chat_impl combines message and file content."""
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id", model="gpt-4.1-mini", content="Response",
            finish_reason="stop", provider="openai",
            created_at=datetime.now(), raw_response={},
            usage=Usage(
                prompt_tokens=10, completion_tokens=5, total_tokens=15, cost_usd=0.0001,
                cached_tokens=0, cache_creation_tokens=0, cache_read_tokens=0
            )
        )
        client_instance.chat_completion_sync.return_value = mock_response
        
        mock_prompt.return_value = "4"  # Exit
        
        # Execute with both message and file
        test_file_path = Path("/tmp/test.txt")
        _chat_impl(
            message="Process this:",
            provider="openai",
            model="gpt-4.1-mini",
            temperature=0.7,
            max_tokens=None,
            stream=False,
            system=None,
            file=test_file_path,
            cache_control=False
        )
        
        # Verify message content includes both
        call_args = client_instance.chat_completion_sync.call_args
        request = call_args[0][0]
        content = request.messages[0].content
        assert "Process this:" in content
        assert "File content" in content
