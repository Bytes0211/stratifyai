"""Unit tests for CLI file loading functionality."""

import pytest
from unittest.mock import MagicMock, patch, mock_open, PropertyMock
from pathlib import Path
from datetime import datetime
from typer.testing import CliRunner

from cli.stratifyai_cli import app
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
def mock_console():
    """Mock Rich console."""
    with patch('cli.stratifyai_cli.console') as mock:
        yield mock


@pytest.fixture
def mock_prompt():
    """Mock Rich Prompt.ask."""
    with patch('cli.stratifyai_cli.Prompt.ask') as mock:
        yield mock


@pytest.fixture
def mock_confirm():
    """Mock Rich Confirm.ask."""
    with patch('cli.stratifyai_cli.Confirm.ask') as mock:
        yield mock


class TestLoadFileContentSuccess:
    """Tests for load_file_content successfully loading valid text files."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_load_valid_small_text_file(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content successfully loads a valid small text file."""
        # Create a temporary test file
        test_file = tmp_path / "test.txt"
        test_content = "This is a test file content."
        test_file.write_text(test_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Response",
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
        
        # Mock interactive mode to exit after file load
        mock_prompt.side_effect = ['exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command with file flag
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--file', str(test_file)
            ])
        
        # Verify success message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        success_messages = [call for call in print_calls if '✓ Loaded' in call]
        assert len(success_messages) > 0, "Success message not found"
        
        # Verify file content was loaded
        assert any('test.txt' in str(call) for call in print_calls)
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_load_valid_medium_text_file(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content successfully loads a valid medium-sized text file (< 500KB)."""
        # Create a file with ~100KB of content (below warning threshold)
        test_file = tmp_path / "medium.txt"
        test_content = "Line of text.\n" * 7000  # ~100KB
        test_file.write_text(test_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Response",
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
        
        # Mock interactive mode to exit after file load
        mock_prompt.side_effect = ['exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command with file flag
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--file', str(test_file)
            ])
        
        # Verify success message was printed (no warning for medium files)
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        success_messages = [call for call in print_calls if '✓ Loaded' in call]
        assert len(success_messages) > 0, "Success message not found"
        
        # Verify NO warning was shown
        warning_messages = [call for call in print_calls if '⚠ Large file detected' in call]
        assert len(warning_messages) == 0, "Warning should not appear for medium files"


class TestLoadFileContentNotFound:
    """Tests for load_file_content handling file not found errors."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_file_not_found_error(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content handles file not found error gracefully."""
        # Use a non-existent file path
        nonexistent_file = tmp_path / "nonexistent.txt"
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Mock interactive mode: provide file path interactively, then exit
        mock_prompt.side_effect = [str(nonexistent_file), 'exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command without file flag (will prompt for file)
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini'
            ])
        
        # Verify error message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        error_messages = [call for call in print_calls if '✗ File not found' in call]
        assert len(error_messages) > 0, "File not found error message not displayed"
        
        # Verify the file path is mentioned in error
        assert any(str(nonexistent_file) in call or 'nonexistent.txt' in call for call in print_calls)


class TestLoadFileContentSizeLimit:
    """Tests for load_file_content rejecting files exceeding maximum size limit."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_file_exceeds_max_size_limit(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content rejects files exceeding 5MB size limit."""
        # Create a file larger than 5MB
        test_file = tmp_path / "large.txt"
        # Create 6MB file (exceeds 5MB limit)
        large_content = "X" * (6 * 1024 * 1024)
        test_file.write_text(large_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Mock interactive mode: provide file path, then exit
        mock_prompt.side_effect = [str(test_file), 'exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini'
            ])
        
        # Verify error message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        error_messages = [call for call in print_calls if '✗ File too large' in call]
        assert len(error_messages) > 0, "File too large error message not displayed"
        
        # Verify warning about token consumption
        warning_messages = [call for call in print_calls if 'consume significant tokens' in call]
        assert len(warning_messages) > 0, "Token consumption warning not displayed"
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.Confirm.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_large_file_warning_with_user_confirmation(
        self, mock_client_class, mock_confirm, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content warns about large files (>500KB) and asks for confirmation."""
        # Create a file larger than 500KB but smaller than 5MB
        test_file = tmp_path / "large_but_valid.txt"
        # Create 1MB file (triggers warning but is under 5MB limit)
        large_content = "X" * (1024 * 1024)
        test_file.write_text(large_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Response",
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
        
        # User confirms to load large file, then exits
        mock_confirm.return_value = True
        mock_prompt.side_effect = ['exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command with file flag
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--file', str(test_file)
            ])
        
        # Verify warning was displayed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        warning_messages = [call for call in print_calls if '⚠ Large file detected' in call]
        assert len(warning_messages) > 0, "Large file warning not displayed"
        
        # Verify confirmation was asked
        assert mock_confirm.called, "User confirmation not requested"
        
        # Verify file was loaded after confirmation
        success_messages = [call for call in print_calls if '✓ Loaded' in call]
        assert len(success_messages) > 0, "File should be loaded after confirmation"
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.Confirm.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_large_file_warning_with_user_rejection(
        self, mock_client_class, mock_confirm, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content cancels loading when user rejects large file warning."""
        # Create a file larger than 500KB but smaller than 5MB
        test_file = tmp_path / "large_but_valid.txt"
        # Create 1MB file
        large_content = "X" * (1024 * 1024)
        test_file.write_text(large_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # User rejects loading large file, then exits
        mock_confirm.return_value = False
        mock_prompt.side_effect = ['exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command with file flag
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--file', str(test_file)
            ])
        
        # Verify warning was displayed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        warning_messages = [call for call in print_calls if '⚠ Large file detected' in call]
        assert len(warning_messages) > 0, "Large file warning not displayed"
        
        # Verify confirmation was asked
        assert mock_confirm.called, "User confirmation not requested"
        
        # Verify file was NOT loaded (cancellation message shown)
        cancel_messages = [call for call in print_calls if 'File load cancelled' in call]
        assert len(cancel_messages) > 0, "File load cancellation message not displayed"


class TestLoadFileContentNonTextFile:
    """Tests for load_file_content handling non-text files (UnicodeDecodeError)."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_binary_file_raises_unicode_decode_error(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that load_file_content raises error for non-text files (binary files)."""
        # Create a binary file (not a text file)
        test_file = tmp_path / "binary.bin"
        # Write binary data that will cause UnicodeDecodeError
        binary_data = bytes([0xFF, 0xFE, 0xFD, 0xFC] * 100)
        test_file.write_bytes(binary_data)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Mock interactive mode: provide file path, then exit
        mock_prompt.side_effect = [str(test_file), 'exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini'
            ])
        
        # Verify error message was printed
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        error_messages = [call for call in print_calls if 'not a text file' in call]
        assert len(error_messages) > 0, "Non-text file error message not displayed"


class TestInteractiveModeInitialFileLoad:
    """Tests for interactive mode loading initial file content when --file flag is used."""
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_interactive_mode_loads_initial_file_with_flag(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that interactive mode loads initial file content when --file flag is used."""
        # Create a test file
        test_file = tmp_path / "context.txt"
        test_content = "This is the initial context from file."
        test_file.write_text(test_content)
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        mock_response = ChatResponse(
            id="test-id",
            model="gpt-4.1-mini",
            content="Response with context",
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
        client_instance.chat_completion_sync.return_value = mock_response
        
        # Mock interactive mode: send a message, then exit
        mock_prompt.side_effect = ['Hello with context', 'exit']
        
        # Capture the messages sent to the LLM
        captured_requests = []
        
        def capture_request(request):
            # Deep copy messages
            captured_requests.append([Message(role=m.role, content=m.content) for m in request.messages])
            return mock_response
        
        client_instance.chat_completion_sync.side_effect = capture_request
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command with file flag
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini',
                '--file', str(test_file)
            ])
        
        # Verify success message for file load
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        success_messages = [call for call in print_calls if '✓ Loaded' in call]
        assert len(success_messages) > 0, "File load success message not displayed"
        
        # Verify "Loading initial context..." message
        loading_messages = [call for call in print_calls if 'Loading initial context' in call]
        assert len(loading_messages) > 0, "Loading context message not displayed"
        
        # Verify "File loaded as initial context" message
        loaded_messages = [call for call in print_calls if 'File loaded as initial context' in call]
        assert len(loaded_messages) > 0, "File loaded confirmation not displayed"
        
        # Verify the file content was included in the message history
        assert len(captured_requests) > 0, "No requests captured"
        first_request_messages = captured_requests[0]
        
        # First message should be the file context
        assert len(first_request_messages) >= 1, "No initial context message found"
        assert test_content in first_request_messages[0].content, "File content not in initial message"
        assert "[Context from context.txt]" in first_request_messages[0].content, "Context label not found"
    
    @patch('cli.stratifyai_cli.console')
    @patch('cli.stratifyai_cli.Prompt.ask')
    @patch('cli.stratifyai_cli.LLMClient')
    def test_interactive_mode_continues_without_file_if_load_fails(
        self, mock_client_class, mock_prompt, mock_console, tmp_path
    ):
        """Test that interactive mode continues without initial file if load fails."""
        # Note: When using --file flag, Typer validates file existence before CLI code runs.
        # This test verifies error handling when file is provided interactively instead.
        
        # Use a non-existent file path
        nonexistent_file = tmp_path / "nonexistent.txt"
        
        # Setup mocks
        client_instance = MagicMock()
        mock_client_class.return_value = client_instance
        
        # Mock interactive mode: provide invalid file path when prompted, then exit
        mock_prompt.side_effect = [str(nonexistent_file), 'exit']
        
        # Mock MODEL_CATALOG
        with patch('cli.stratifyai_cli.MODEL_CATALOG', {
            'openai': {'gpt-4.1-mini': {'context': 128000}}
        }):
            # Run interactive command without file flag (will prompt for file)
            runner = CliRunner()
            result = runner.invoke(app, [
                'interactive',
                '--provider', 'openai',
                '--model', 'gpt-4.1-mini'
            ])
        
        # Verify error message was shown
        print_calls = [str(call) for call in mock_console.print.call_args_list]
        error_messages = [call for call in print_calls if '✗ File not found' in call]
        assert len(error_messages) > 0, "File not found error not displayed"
        
        # Verify interactive mode still started (welcome message shown)
        welcome_messages = [call for call in print_calls if 'StratifyAI Interactive Mode' in call]
        assert len(welcome_messages) > 0, "Interactive mode did not start"
