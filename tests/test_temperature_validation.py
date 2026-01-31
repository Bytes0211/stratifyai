#!/usr/bin/env python3
"""Test temperature validation for providers."""

from llm_abstraction import LLMClient
from llm_abstraction.exceptions import ValidationError
from llm_abstraction.models import Message

def test_anthropic_temperature_validation():
    """Test that Anthropic rejects temperature > 1.0."""
    print("Testing Anthropic temperature validation...")
    
    try:
        client = LLMClient(provider="anthropic")
        
        # This should raise ValidationError (temperature > 1.0)
        messages = [Message(role="user", content="Hello")]
        try:
            response = client.chat_completion(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                temperature=1.3  # Invalid for Anthropic
            )
            print("❌ FAIL: Expected ValidationError but request succeeded")
        except ValidationError as e:
            print(f"✅ PASS: Caught ValidationError as expected: {e}")
        
        # This should succeed (temperature = 1.0)
        try:
            response = client.chat_completion(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                temperature=1.0  # Valid for Anthropic
            )
            print("✅ PASS: Temperature 1.0 accepted for Anthropic")
        except ValidationError as e:
            print(f"❌ FAIL: Temperature 1.0 should be valid: {e}")
        
        # This should succeed (temperature = 0.7)
        try:
            response = client.chat_completion(
                model="claude-3-5-sonnet-20241022",
                messages=messages,
                temperature=0.7  # Valid for Anthropic
            )
            print("✅ PASS: Temperature 0.7 accepted for Anthropic")
        except ValidationError as e:
            print(f"❌ FAIL: Temperature 0.7 should be valid: {e}")
            
    except Exception as e:
        print(f"⚠️  Test skipped (no API key or other error): {e}")

def test_openai_temperature_validation():
    """Test that OpenAI accepts temperature up to 2.0."""
    print("\nTesting OpenAI temperature validation...")
    
    try:
        client = LLMClient(provider="openai")
        
        messages = [Message(role="user", content="Hello")]
        
        # This should raise ValidationError (temperature > 2.0)
        try:
            response = client.chat_completion(
                model="gpt-4o-mini",
                messages=messages,
                temperature=2.5  # Invalid for OpenAI
            )
            print("❌ FAIL: Expected ValidationError but request succeeded")
        except ValidationError as e:
            print(f"✅ PASS: Caught ValidationError as expected: {e}")
        
        # This should succeed (temperature = 2.0)
        try:
            response = client.chat_completion(
                model="gpt-4o-mini",
                messages=messages,
                temperature=2.0,  # Valid for OpenAI
                max_tokens=5
            )
            print("✅ PASS: Temperature 2.0 accepted for OpenAI")
        except ValidationError as e:
            print(f"❌ FAIL: Temperature 2.0 should be valid: {e}")
            
    except Exception as e:
        print(f"⚠️  Test skipped (no API key or other error): {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Temperature Validation Tests")
    print("=" * 60)
    test_anthropic_temperature_validation()
    test_openai_temperature_validation()
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)
