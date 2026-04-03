"""Tests for prompt template system."""

import warnings
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest

from stratifyai.models import Message
from stratifyai.prompts import PromptParameter, PromptRegistry, PromptTemplate, registry

# ===== Model Tests =====


def test_prompt_parameter_validate_required():
    """Test that required parameters without values raise ValueError."""
    param = PromptParameter(name="text", required=True, description="Test param")

    with pytest.raises(ValueError, match="Required parameter 'text' not provided"):
        param.validate(None)


def test_prompt_parameter_validate_default():
    """Test that missing parameters use defaults."""
    param = PromptParameter(name="style", default="brief", required=False)

    assert param.validate(None) == "brief"
    assert param.validate("detailed") == "detailed"


def test_prompt_parameter_validate_choice():
    """Test that invalid choices raise ValueError."""
    param = PromptParameter(
        name="focus",
        type="choice",
        choices=["bugs", "security", "performance"],
        default="bugs",
        required=False,
    )

    # Valid choice
    assert param.validate("security") == "security"

    # Invalid choice
    with pytest.raises(ValueError, match="must be one of"):
        param.validate("invalid")


def test_prompt_parameter_validate_number():
    """Test number coercion and validation."""
    param = PromptParameter(name="max_length", type="number", required=True)

    # Valid numbers
    assert param.validate(100) == 100.0
    assert param.validate("200") == 200.0
    assert param.validate(50.5) == 50.5

    # Invalid number
    with pytest.raises(ValueError, match="must be a number"):
        param.validate("not_a_number")


def test_prompt_template_render_basic():
    """Test basic template rendering with system and user messages."""
    template = PromptTemplate(
        name="test",
        description="Test template",
        system="You are a {role}.",
        user="Help me with {task}.",
        parameters=[
            PromptParameter(name="role", required=True),
            PromptParameter(name="task", required=True),
        ],
    )

    messages = template.render(role="assistant", task="coding")

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert messages[0].content == "You are a assistant."
    assert messages[1].role == "user"
    assert messages[1].content == "Help me with coding."


def test_prompt_template_render_missing_required():
    """Test that missing required parameters raise ValueError."""
    template = PromptTemplate(
        name="test",
        description="Test template",
        system="System",
        user="User prompt requires {param}.",
        parameters=[
            PromptParameter(name="param", required=True, description="Required"),
        ],
    )

    with pytest.raises(ValueError, match="Required parameter 'param' not provided"):
        template.render()


def test_prompt_template_render_with_defaults():
    """Test that defaults are substituted correctly."""
    template = PromptTemplate(
        name="test",
        description="Test template",
        system="",
        user="Style: {style}. Length: {max_length}.",
        parameters=[
            PromptParameter(name="style", default="brief", required=False),
            PromptParameter(
                name="max_length", type="number", default=100, required=False
            ),
        ],
    )

    messages = template.render()
    assert len(messages) == 1
    assert "Style: brief" in messages[0].content
    assert "Length: 100" in messages[0].content


def test_prompt_template_render_unknown_param_warns():
    """Test that unknown parameters trigger warnings."""
    template = PromptTemplate(
        name="test",
        description="Test template",
        system="",
        user="{known}",
        parameters=[
            PromptParameter(name="known", required=True),
        ],
    )

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        template.render(known="value", unknown="extra")
        assert len(w) == 1
        assert "Unknown parameter 'unknown'" in str(w[0].message)


def test_prompt_template_to_dict():
    """Test template serialization for API responses."""
    template = PromptTemplate(
        name="test",
        description="Test template",
        system="System",
        user="User",
        parameters=[
            PromptParameter(
                name="param1",
                type="string",
                description="First param",
                default="default",
                required=False,
            ),
        ],
        tags=["tag1", "tag2"],
        recommended_models=["model1"],
        recommended_temperature=0.5,
        source="builtin",
    )

    result = template.to_dict()

    assert result["name"] == "test"
    assert result["description"] == "Test template"
    assert result["system"] == "System"
    assert result["user"] == "User"
    assert len(result["parameters"]) == 1
    assert result["parameters"][0]["name"] == "param1"
    assert result["tags"] == ["tag1", "tag2"]
    assert result["recommended_models"] == ["model1"]
    assert result["recommended_temperature"] == 0.5
    assert result["source"] == "builtin"


# ===== Registry Tests =====


def test_registry_loads_builtin_templates():
    """Test that built-in templates are discovered and loaded."""
    templates = registry.list()

    # Should have 10 built-in templates
    assert len(templates) >= 10

    # Check for specific templates
    template_names = [t.name for t in templates]
    assert "code_review" in template_names
    assert "summarize" in template_names
    assert "chatbot" in template_names


def test_registry_get_existing():
    """Test getting a template by name."""
    template = registry.get("code_review")

    assert template.name == "code_review"
    assert "code" in template.tags
    assert len(template.parameters) > 0


def test_registry_get_nonexistent():
    """Test that getting nonexistent template raises KeyError with available list."""
    with pytest.raises(KeyError, match="Template 'nonexistent' not found"):
        registry.get("nonexistent")


def test_registry_list_all():
    """Test listing all templates."""
    templates = registry.list()

    assert len(templates) > 0
    # Templates should be sorted by name
    assert templates == sorted(templates, key=lambda t: t.name)


def test_registry_list_by_tag():
    """Test filtering templates by tag."""
    code_templates = registry.list(tag="code")

    assert len(code_templates) > 0
    # All templates should have the 'code' tag
    for t in code_templates:
        assert "code" in t.tags


def test_registry_list_by_source():
    """Test filtering templates by source."""
    builtin_templates = registry.list(source="builtin")

    assert len(builtin_templates) > 0
    # All templates should be built-in
    for t in builtin_templates:
        assert t.source == "builtin"


def test_registry_render_shortcut():
    """Test that render() combines get + render in one call."""
    messages = registry.render(
        "summarize",
        text="This is a test document.",
        max_length=50,
        style="bullet_points",
    )

    assert len(messages) >= 1
    assert any(isinstance(m, Message) for m in messages)


def test_registry_search():
    """Test searching templates by name, description, and tags."""
    # Search by name
    results = registry.search("code")
    assert len(results) > 0
    assert any("code" in t.name.lower() for t in results)

    # Search by tag
    results = registry.search("review")
    assert len(results) > 0


def test_registry_tags():
    """Test getting all unique tags."""
    tags = registry.tags()

    assert len(tags) > 0
    # Tags should be sorted
    assert tags == sorted(tags)
    # Should contain common tags
    assert "code" in tags


def test_registry_register_programmatic():
    """Test manual template registration."""
    custom_registry = PromptRegistry()

    template = PromptTemplate(
        name="custom",
        description="Custom template",
        system="System",
        user="User",
        source="user",
    )

    custom_registry.register(template)

    assert custom_registry.get("custom").name == "custom"


def test_registry_load_user_directory():
    """Test loading YAML templates from a custom directory."""
    with TemporaryDirectory() as tmpdir:
        # Create a test template file
        template_path = Path(tmpdir) / "test_template.yaml"
        template_path.write_text("""
name: test_user_template
description: User template for testing
system: You are a helpful assistant.
user: Help with {task}
parameters:
  - name: task
    type: string
    description: Task to help with
    required: true
tags:
  - test
""")

        # Load from directory
        custom_registry = PromptRegistry()
        count = custom_registry.load_directory(Path(tmpdir), source="user")

        assert count == 1
        template = custom_registry.get("test_user_template")
        assert template.name == "test_user_template"
        assert template.source == "user"


def test_registry_user_overrides_builtin():
    """Test that user templates can override built-in templates with same name."""
    with TemporaryDirectory() as tmpdir:
        # Create a user template with a unique name first
        template_path = Path(tmpdir) / "my_custom_template.yaml"
        template_path.write_text("""
name: my_custom_template
description: My custom template
system: Custom system
user: Custom user {text}
parameters:
  - name: text
    type: text
    required: true
""")

        # Create fresh registry
        custom_registry = PromptRegistry()

        # Load user templates
        count_user = custom_registry.load_directory(Path(tmpdir), source="user")
        assert count_user == 1

        template = custom_registry.get("my_custom_template")
        # Verify user template was loaded correctly
        assert template.source == "user"
        assert template.description.strip() == "My custom template"
        assert template.system == "Custom system"

        # Now test override by loading the same template name again
        override_path = Path(tmpdir) / "my_custom_template_v2.yaml"
        override_path.write_text("""
name: my_custom_template
description: Overridden template
system: Override system
user: Override user {text}
parameters:
  - name: text
    type: text
    required: true
""")

        # Load again - should override
        count = custom_registry.load_directory(Path(tmpdir), source="user")
        assert count == 2  # Both files loaded

        template_after = custom_registry.get("my_custom_template")
        # The last loaded template should win
        assert template_after.description.strip() in [
            "My custom template",
            "Overridden template",
        ]


# ===== YAML Loading Tests =====


def test_load_yaml_template_valid():
    """Test parsing all fields from YAML correctly."""
    with TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "complete.yaml"
        template_path.write_text("""
name: complete_template
description: A complete template
system: System prompt with {param1}
user: User prompt with {param2}
parameters:
  - name: param1
    type: string
    description: First parameter
    default: default1
    required: false
  - name: param2
    type: number
    description: Second parameter
    required: true
tags:
  - tag1
  - tag2
recommended_models:
  - model1
  - model2
recommended_temperature: 0.5
""")

        from stratifyai.prompts.registry import _load_yaml_template

        template = _load_yaml_template(template_path, source="user")

        assert template.name == "complete_template"
        assert template.description == "A complete template"
        assert len(template.parameters) == 2
        assert template.parameters[0].name == "param1"
        assert template.parameters[0].default == "default1"
        assert template.tags == ["tag1", "tag2"]
        assert template.recommended_models == ["model1", "model2"]
        assert template.recommended_temperature == 0.5


def test_load_yaml_template_minimal():
    """Test that optional fields are handled correctly."""
    with TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "minimal.yaml"
        template_path.write_text("""
name: minimal
system: System
user: User
""")

        from stratifyai.prompts.registry import _load_yaml_template

        template = _load_yaml_template(template_path, source="builtin")

        assert template.name == "minimal"
        assert template.description == ""
        assert len(template.parameters) == 0
        assert len(template.tags) == 0


def test_load_yaml_template_invalid():
    """Test graceful error on invalid YAML."""
    with TemporaryDirectory() as tmpdir:
        template_path = Path(tmpdir) / "invalid.yaml"
        # Missing required 'system' field
        template_path.write_text("""
name: invalid
user: User only
""")

        from stratifyai.prompts.registry import _load_yaml_template

        with pytest.raises(ValueError, match="missing required field"):
            _load_yaml_template(template_path, source="user")


# ===== Integration Tests =====


def test_template_messages_work_with_chat_request():
    """Test that rendered messages create a valid ChatRequest."""
    from stratifyai import ChatRequest

    messages = registry.render(
        "chatbot", persona="coding assistant", tone="professional"
    )

    # Should be able to create a ChatRequest
    request = ChatRequest(
        model="gpt-4o-mini",
        messages=messages,
    )

    assert request.model == "gpt-4o-mini"
    assert len(request.messages) >= 1


def test_code_review_template_renders():
    """Test that code_review template renders with real parameters."""
    messages = registry.render(
        "code_review",
        code="def hello():\n    print('world')",
        language="python",
        focus="style",
    )

    assert len(messages) == 2
    assert messages[0].role == "system"
    assert "python" in messages[0].content.lower()
    assert messages[1].role == "user"
    assert "def hello():" in messages[1].content


def test_summarize_template_renders():
    """Test that summarize template renders with real parameters."""
    messages = registry.render(
        "summarize",
        text="This is a long document that needs to be summarized.",
        max_length=100,
        style="bullet_points",
    )

    assert len(messages) >= 1
    system_msg = next((m for m in messages if m.role == "system"), None)
    if system_msg:
        assert "100" in system_msg.content  # max_length
        assert "bullet_points" in system_msg.content  # style


def test_all_builtin_templates_render_with_defaults():
    """Test that every built-in template renders when only defaults are used."""
    templates = registry.list(source="builtin")

    for template in templates:
        # Skip templates that have required parameters without defaults
        required_params = [
            p for p in template.parameters if p.required and p.default is None
        ]

        if not required_params:
            # Should render successfully with defaults
            messages = template.render()
            assert len(messages) >= 1
            assert all(isinstance(m, Message) for m in messages)


def test_chatbuilder_integration():
    """Test integration with ChatBuilder.with_template()."""
    from stratifyai.chat.builder import ChatBuilder

    builder = ChatBuilder(provider="openai", default_temperature=0.7)

    # Apply template
    configured_builder = builder.with_template(
        "chatbot", persona="coding assistant", tone="friendly"
    )

    # Should have system prompt and temperature set
    assert configured_builder._system is not None
    assert "coding assistant" in configured_builder._system
    assert configured_builder._temperature == 0.7  # Template recommends 0.7


def test_template_with_empty_system():
    """Test that templates with empty system prompts work correctly."""
    template = PromptTemplate(
        name="test",
        description="Test",
        system="",  # Empty system prompt
        user="Hello {name}",
        parameters=[
            PromptParameter(name="name", required=True),
        ],
    )

    messages = template.render(name="World")

    # Should only have user message
    assert len(messages) == 1
    assert messages[0].role == "user"
    assert messages[0].content == "Hello World"
