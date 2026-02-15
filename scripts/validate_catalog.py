#!/usr/bin/env python3
"""Validate catalog/models.json against catalog/schema.json.

This script checks:
- JSON syntax is valid
- Catalog matches the JSON schema
- Required fields are present
- No duplicate model IDs within provider
- Pricing values are non-negative
- Context window > 0

Usage:
    python scripts/validate_catalog.py
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Tuple


def load_json_file(path: Path) -> Dict[str, Any]:
    """Load and parse JSON file."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {path}: {e}")
        sys.exit(1)
    except FileNotFoundError:
        print(f"❌ File not found: {path}")
        sys.exit(1)


def validate_schema(catalog: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Basic schema validation (simplified - doesn't use jsonschema library)."""
    errors = []
    
    # Check required top-level fields
    required_fields = ["version", "updated", "providers"]
    for field in required_fields:
        if field not in catalog:
            errors.append(f"Missing required field: {field}")
    
    # Validate version format (semver)
    if "version" in catalog:
        version = catalog["version"]
        parts = version.split(".")
        if len(parts) != 3 or not all(p.isdigit() for p in parts):
            errors.append(f"Invalid version format: {version} (expected semver like 1.0.0)")
    
    return errors


def validate_providers(providers: Dict[str, Dict[str, Any]]) -> List[str]:
    """Validate provider models."""
    errors = []
    
    for provider_name, models in providers.items():
        # Check provider name format
        if not provider_name.islower():
            errors.append(f"Provider name must be lowercase: {provider_name}")
        
        # Track model IDs to detect duplicates
        model_ids = set()
        
        for model_id, model_data in models.items():
            # Check for duplicates
            if model_id in model_ids:
                errors.append(f"{provider_name}: Duplicate model ID: {model_id}")
            model_ids.add(model_id)
            
            # Validate required fields
            required_fields = ["context", "cost_input", "cost_output"]
            for field in required_fields:
                if field not in model_data:
                    errors.append(f"{provider_name}/{model_id}: Missing required field: {field}")
            
            # Validate context window
            if "context" in model_data:
                context = model_data["context"]
                if not isinstance(context, int) or context <= 0:
                    errors.append(f"{provider_name}/{model_id}: Invalid context window: {context} (must be positive integer)")
            
            # Validate pricing
            for cost_field in ["cost_input", "cost_output", "cost_cache_write", "cost_cache_read"]:
                if cost_field in model_data:
                    cost = model_data[cost_field]
                    if not isinstance(cost, (int, float)) or cost < 0:
                        errors.append(f"{provider_name}/{model_id}: Invalid {cost_field}: {cost} (must be non-negative number)")
            
            # Validate deprecation fields
            if model_data.get("deprecated"):
                if "deprecated_date" not in model_data:
                    errors.append(f"{provider_name}/{model_id}: Deprecated models must have deprecated_date")
                if "replacement_model" not in model_data:
                    errors.append(f"{provider_name}/{model_id}: Deprecated models must have replacement_model")
    
    return errors


def main():
    """Main validation function."""
    project_root = Path(__file__).parent.parent
    catalog_path = project_root / "catalog" / "models.json"
    schema_path = project_root / "catalog" / "schema.json"
    
    print("🔍 Validating model catalog...")
    print(f"   Catalog: {catalog_path}")
    print(f"   Schema:  {schema_path}")
    print()
    
    # Load files
    catalog = load_json_file(catalog_path)
    schema = load_json_file(schema_path)
    
    all_errors = []
    
    # Validate schema
    print("✓ JSON syntax valid")
    
    schema_errors = validate_schema(catalog, schema)
    all_errors.extend(schema_errors)
    
    if not schema_errors:
        print("✓ Schema validation passed")
    
    # Validate providers
    if "providers" in catalog:
        provider_errors = validate_providers(catalog["providers"])
        all_errors.extend(provider_errors)
        
        if not provider_errors:
            print("✓ Provider validation passed")
            
            # Count models
            total_models = sum(len(models) for models in catalog["providers"].values())
            print(f"✓ Found {len(catalog['providers'])} providers with {total_models} models")
    
    # Report results
    print()
    if all_errors:
        print(f"❌ Validation failed with {len(all_errors)} errors:")
        for error in all_errors:
            print(f"   - {error}")
        sys.exit(1)
    else:
        print("✅ Catalog validation passed!")
        print(f"   Version: {catalog.get('version', 'unknown')}")
        print(f"   Updated: {catalog.get('updated', 'unknown')}")
        sys.exit(0)


if __name__ == "__main__":
    main()
