"""Builder pattern for configuring chat clients.

Provides a fluent interface for configuring chat parameters before execution.

Example:
    from stratifyai.chat import anthropic

    # Model is always required
    response = await anthropic.chat("Hello", model="claude-sonnet-4-5")

    # Builder pattern with chaining (model required)
    client = (
        anthropic
        .with_model("claude-opus-4-5")
        .with_system("I am a helpful assistant")
        .with_developer("Use markdown formatting")
        .with_temperature(0.5)
        .with_max_tokens(1000)
    )
    response = await client.chat("Hello")
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from stratifyai.utils.sync_helpers import run_sync

if TYPE_CHECKING:
    from stratifyai import LLMClient
    from stratifyai.models import ChatResponse


@dataclass
class ChatBuilder:
    """Builder for configuring chat requests with fluent interface.

    Each with_* method returns a new ChatBuilder instance with the
    updated configuration, allowing for method chaining.

    Model is required - either via with_model() or as a parameter to chat().

    Attributes:
        provider: The provider name (e.g., "openai", "anthropic")
        default_temperature: Default temperature setting
        default_max_tokens: Default max tokens setting
        _model: Configured model (required before chat)
        _system: System prompt
        _developer: Developer/instruction prompt
        _temperature: Configured temperature (None = use default)
        _max_tokens: Configured max tokens (None = use default)
        _client_factory: Factory function to create LLMClient
    """

    provider: str
    default_temperature: float = 0.7
    default_max_tokens: int | None = None
    _model: str | None = None
    _system: str | None = None
    _developer: str | None = None
    _temperature: float | None = None
    _max_tokens: int | None = None
    _template_user: str | None = None
    _client_factory: Callable[[], LLMClient] | None = None
    _extra_kwargs: dict = field(default_factory=dict)

    def _clone(self, **updates) -> ChatBuilder:
        """Create a copy of this builder with updates applied."""
        return ChatBuilder(
            provider=self.provider,
            default_temperature=self.default_temperature,
            default_max_tokens=self.default_max_tokens,
            _model=updates.get("_model", self._model),
            _system=updates.get("_system", self._system),
            _developer=updates.get("_developer", self._developer),
            _temperature=updates.get("_temperature", self._temperature),
            _max_tokens=updates.get("_max_tokens", self._max_tokens),
            _template_user=updates.get("_template_user", self._template_user),
            _client_factory=self._client_factory,
            _extra_kwargs={**self._extra_kwargs, **updates.get("_extra_kwargs", {})},
        )

    def with_model(self, model: str) -> ChatBuilder:
        """Set the model to use (required).

        Args:
            model: Model name (e.g., "claude-opus-4-5", "gpt-4.1")

        Returns:
            New ChatBuilder with model configured.

        Example:
            client = anthropic.with_model("claude-opus-4-5")
        """
        return self._clone(_model=model)

    def with_system(self, prompt: str) -> ChatBuilder:
        """Set the system prompt.

        The system prompt sets the AI's behavior and context.

        Args:
            prompt: System prompt text

        Returns:
            New ChatBuilder with system prompt configured.

        Example:
            client = anthropic.with_system("You are a helpful coding assistant")
        """
        return self._clone(_system=prompt)

    def with_developer(self, instructions: str) -> ChatBuilder:
        """Set developer/instruction prompt.

        Developer instructions provide formatting or behavioral guidance.
        These are prepended to the system prompt if both are set.

        Args:
            instructions: Developer instructions text

        Returns:
            New ChatBuilder with developer instructions configured.

        Example:
            client = anthropic.with_developer("Always use markdown formatting")
        """
        return self._clone(_developer=instructions)

    def with_temperature(self, temperature: float) -> ChatBuilder:
        """Set the sampling temperature.

        Args:
            temperature: Temperature value (0.0 = deterministic, 2.0 = creative)

        Returns:
            New ChatBuilder with temperature configured.

        Example:
            client = anthropic.with_temperature(0.3)
        """
        return self._clone(_temperature=temperature)

    def with_max_tokens(self, max_tokens: int) -> ChatBuilder:
        """Set the maximum tokens to generate.

        Args:
            max_tokens: Maximum number of tokens in the response

        Returns:
            New ChatBuilder with max_tokens configured.

        Example:
            client = anthropic.with_max_tokens(500)
        """
        return self._clone(_max_tokens=max_tokens)

    def with_options(self, **kwargs) -> ChatBuilder:
        """Set additional provider-specific options.

        Args:
            **kwargs: Additional options passed to the API

        Returns:
            New ChatBuilder with extra options configured.

        Example:
            client = anthropic.with_options(top_p=0.9)
        """
        return self._clone(_extra_kwargs=kwargs)

    def with_template(self, name: str, **params) -> ChatBuilder:
        """Configure the builder using a named prompt template.

        Loads the template from the registry, renders it with the given
        parameters, and applies the resulting system/user prompts to
        the builder.

        If the template specifies a ``recommended_temperature`` and no
        temperature has been set on this builder, the recommended value
        is applied automatically.

        Args:
            name: Template name (e.g., ``"code_review"``).
            **params: Template parameter values.

        Returns:
            A new ``ChatBuilder`` with the template applied.

        Raises:
            KeyError: If the template is not found.
            ValueError: If required template parameters are missing.

        Example::

            response = await (
                anthropic
                .with_model("claude-sonnet-4-20250514")
                .with_template("code_review", code=src, language="python")
                .chat("Review this code")
            )
        """
        from stratifyai.prompts import registry

        template = registry.get(name)
        messages = template.render(**params)

        # Extract system and user content from rendered messages
        system_content = None
        user_content = None
        for msg in messages:
            if msg.role == "system":
                system_content = msg.content
            elif msg.role == "user":
                user_content = msg.content

        updates: dict[str, Any] = {}
        if system_content:
            updates["_system"] = system_content
        if user_content:
            updates["_template_user"] = user_content

        # Apply recommended temperature if none is set
        if template.recommended_temperature is not None and self._temperature is None:
            updates["_temperature"] = template.recommended_temperature

        return self._clone(**updates)

    @property
    def model(self) -> str | None:
        """Get the configured model (None if not set)."""
        return self._model

    @property
    def temperature(self) -> float:
        """Get the effective temperature (configured or default)."""
        return (
            self._temperature
            if self._temperature is not None
            else self.default_temperature
        )

    @property
    def max_tokens(self) -> int | None:
        """Get the effective max_tokens (configured or default)."""
        return (
            self._max_tokens
            if self._max_tokens is not None
            else self.default_max_tokens
        )

    def _get_client(self) -> LLMClient:
        """Get or create the LLM client."""
        if self._client_factory is None:
            from stratifyai import LLMClient

            return LLMClient(provider=self.provider)
        return self._client_factory()

    def _build_system_prompt(self) -> str | None:
        """Combine developer and system prompts."""
        if self._developer and self._system:
            return f"{self._developer}\n\n{self._system}"
        return self._developer or self._system

    def _build_messages(self, prompt: str | list) -> list:
        """Build the messages list from prompt and configured prompts.

        If a template was applied via ``with_template()``, the template's
        rendered user message is used, and the explicit prompt is appended
        if provided.
        """
        from stratifyai.models import Message

        if isinstance(prompt, str):
            messages = []
            system_prompt = self._build_system_prompt()
            if system_prompt:
                messages.append(Message(role="system", content=system_prompt))

            # If template user content exists, use it first
            if self._template_user:
                messages.append(Message(role="user", content=self._template_user))
                # Append explicit prompt if provided and non-empty
                if prompt and prompt.strip():
                    messages.append(Message(role="user", content=prompt))
            else:
                messages.append(Message(role="user", content=prompt))
            return messages
        else:
            # If prompt is already a list of messages, prepend system if not present
            messages = list(prompt)
            system_prompt = self._build_system_prompt()
            if system_prompt and (not messages or messages[0].role != "system"):
                from stratifyai.models import Message

                messages.insert(0, Message(role="system", content=system_prompt))
            return messages

    async def chat(
        self,
        prompt: str | list,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
        **kwargs,
    ) -> ChatResponse | AsyncIterator[ChatResponse]:
        """Send an async chat completion request.

        Args:
            prompt: User message string or list of Message objects.
            model: Model to use (required if not set via with_model()).
            system: Override the configured system prompt.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max_tokens.
            stream: Whether to stream the response.
            **kwargs: Additional parameters passed to the API.

        Returns:
            ChatResponse object, or AsyncIterator[ChatResponse] if streaming.

        Raises:
            ValueError: If no model is specified.
        """
        client = self._get_client()

        # Use overrides if provided, otherwise use configured values
        effective_model = model or self._model
        if not effective_model:
            raise ValueError(
                f"Model is required. Either call with_model() first or pass model parameter.\n"
                f"Example: {self.provider}.with_model('model-name').chat(...) or "
                f"{self.provider}.chat(..., model='model-name')"
            )
        effective_temp = temperature if temperature is not None else self.temperature
        effective_max = max_tokens if max_tokens is not None else self.max_tokens

        # Handle system prompt override
        if system:
            builder = self.with_system(system)
            messages = builder._build_messages(prompt)
        else:
            messages = self._build_messages(prompt)

        # Merge extra kwargs
        merged_kwargs = {**self._extra_kwargs, **kwargs}

        return await client.chat(
            model=effective_model,
            messages=messages,
            temperature=effective_temp,
            max_tokens=effective_max,
            stream=stream,
            **merged_kwargs,
        )

    async def chat_stream(
        self,
        prompt: str | list,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> AsyncIterator[ChatResponse]:
        """Send an async streaming chat completion request.

        Args:
            prompt: User message string or list of Message objects.
            model: Override the configured model.
            system: Override the configured system prompt.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max_tokens.
            **kwargs: Additional parameters passed to the API.

        Yields:
            ChatResponse chunks.
        """
        return cast(
            AsyncIterator[ChatResponse],
            await self.chat(
                prompt,
                model=model,
                system=system,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            ),
        )

    def chat_sync(
        self,
        prompt: str | list,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        **kwargs,
    ) -> ChatResponse:
        """Synchronous wrapper for chat().

        Args:
            prompt: User message string or list of Message objects.
            model: Override the configured model.
            system: Override the configured system prompt.
            temperature: Override the configured temperature.
            max_tokens: Override the configured max_tokens.
            **kwargs: Additional parameters passed to the API.

        Returns:
            ChatResponse object.
        """
        return cast(
            ChatResponse,
            run_sync(
                self.chat(
                    prompt,
                    model=model,
                    system=system,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                    **kwargs,
                )
            ),
        )


def create_module_builder(
    provider: str,
    default_temperature: float = 0.7,
    default_max_tokens: int | None = None,
    client_factory: Callable[[], LLMClient] | None = None,
) -> ChatBuilder:
    """Create a ChatBuilder for a provider module.

    Args:
        provider: Provider name
        default_temperature: Default temperature
        default_max_tokens: Default max tokens
        client_factory: Optional factory to create shared client

    Returns:
        Configured ChatBuilder instance
    """
    return ChatBuilder(
        provider=provider,
        default_temperature=default_temperature,
        default_max_tokens=default_max_tokens,
        _client_factory=client_factory,
    )
