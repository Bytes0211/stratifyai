#!/usr/bin/env python3
"""Unit test for temperature validation (no API keys required)."""

import os
from stratifyai.providers.anthropic import AnthropicProvider
from stratifyai.providers.openai import OpenAIProvider
from stratifyai.exceptions import ValidationError
from stratifyai.models import Message, ChatRequest

def test_anthropic_temperature_validation():
    """Test that Anthropic validates temperature 0.0 to 1.0."""
    print("Testing Anthropic temperature validation...")
    
    # Create provider with dummy API key
    provider = AnthropicProvider(api_key="test-key-12345")
    
    # Test valid temperature (0.7)
    try:
        provider.validate_temperature(0.7, 0.0, 1.0)
        print("✅ PASS: Temperature 0.7 is valid for Anthropic")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 0.7 should be valid: {e}")
    
    # Test valid temperature (1.0 - max boundary)
    try:
        provider.validate_temperature(1.0, 0.0, 1.0)
        print("✅ PASS: Temperature 1.0 is valid for Anthropic")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 1.0 should be valid: {e}")
    
    # Test valid temperature (0.0 - min boundary)
    try:
        provider.validate_temperature(0.0, 0.0, 1.0)
        print("✅ PASS: Temperature 0.0 is valid for Anthropic")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 0.0 should be valid: {e}")
    
    # Test invalid temperature (1.3 - exceeds max)
    try:
        provider.validate_temperature(1.3, 0.0, 1.0)
        print("❌ FAIL: Temperature 1.3 should be invalid for Anthropic")
    except ValidationError as e:
        print(f"✅ PASS: Caught ValidationError for temperature 1.3: {e}")
    
    # Test invalid temperature (2.0 - exceeds max)
    try:
        provider.validate_temperature(2.0, 0.0, 1.0)
        print("❌ FAIL: Temperature 2.0 should be invalid for Anthropic")
    except ValidationError as e:
        print(f"✅ PASS: Caught ValidationError for temperature 2.0: {e}")
    
    # Test invalid temperature (-0.1 - below min)
    try:
        provider.validate_temperature(-0.1, 0.0, 1.0)
        print("❌ FAIL: Temperature -0.1 should be invalid for Anthropic")
    except ValidationError as e:
        print(f"✅ PASS: Caught ValidationError for temperature -0.1: {e}")

def test_openai_temperature_validation():
    """Test that OpenAI validates temperature 0.0 to 2.0."""
    print("\nTesting OpenAI temperature validation...")
    
    # Create provider with dummy API key
    provider = OpenAIProvider(api_key="test-key-12345")
    
    # Test valid temperature (0.7)
    try:
        provider.validate_temperature(0.7, 0.0, 2.0)
        print("✅ PASS: Temperature 0.7 is valid for OpenAI")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 0.7 should be valid: {e}")
    
    # Test valid temperature (2.0 - max boundary)
    try:
        provider.validate_temperature(2.0, 0.0, 2.0)
        print("✅ PASS: Temperature 2.0 is valid for OpenAI")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 2.0 should be valid: {e}")
    
    # Test valid temperature (1.5)
    try:
        provider.validate_temperature(1.5, 0.0, 2.0)
        print("✅ PASS: Temperature 1.5 is valid for OpenAI")
    except ValidationError as e:
        print(f"❌ FAIL: Temperature 1.5 should be valid: {e}")
    
    # Test invalid temperature (2.5 - exceeds max)
    try:
        provider.validate_temperature(2.5, 0.0, 2.0)
        print("❌ FAIL: Temperature 2.5 should be invalid for OpenAI")
    except ValidationError as e:
        print(f"✅ PASS: Caught ValidationError for temperature 2.5: {e}")
    
    # Test invalid temperature (-0.1 - below min)
    try:
        provider.validate_temperature(-0.1, 0.0, 2.0)
        print("❌ FAIL: Temperature -0.1 should be invalid for OpenAI")
    except ValidationError as e:
        print(f"✅ PASS: Caught ValidationError for temperature -0.1: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("Temperature Validation Unit Tests (No API Keys Required)")
    print("=" * 60)
    test_anthropic_temperature_validation()
    test_openai_temperature_validation()
    print("\n" + "=" * 60)
    print("All tests complete!")
    print("=" * 60)
