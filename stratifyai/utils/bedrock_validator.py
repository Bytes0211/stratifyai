"""Bedrock model validation utility.

Validates AWS Bedrock model availability using boto3.
"""

import time
from typing import Dict, List, Any, Optional

try:
    import boto3
    from botocore.exceptions import ClientError, NoCredentialsError, BotoCoreError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False


def validate_bedrock_models(
    model_ids: List[str],
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validate which Bedrock models are available in the user's AWS account/region.
    
    Args:
        model_ids: List of model IDs to validate
        region_name: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
        
    Returns:
        Dict containing:
            - valid_models: List of model IDs that are available
            - invalid_models: List of model IDs that are NOT available
            - validation_time_ms: Time taken to validate in milliseconds
            - error: Error message if validation failed (None if successful)
    """
    import os
    
    result = {
        "valid_models": [],
        "invalid_models": [],
        "validation_time_ms": 0,
        "error": None,
    }
    
    if not BOTO3_AVAILABLE:
        result["error"] = "boto3 not installed"
        result["valid_models"] = model_ids  # Assume all valid if can't check
        return result
    
    start_time = time.time()
    
    try:
        # Get region from env or default
        region = region_name or os.getenv("AWS_DEFAULT_REGION", "us-east-1")
        
        # Create bedrock client (not bedrock-runtime - we need list_foundation_models)
        bedrock_client = boto3.client(
            service_name="bedrock",
            region_name=region
        )
        
        # Get available foundation models
        response = bedrock_client.list_foundation_models()
        available_model_ids = {model["modelId"] for model in response.get("modelSummaries", [])}
        
        # Check each requested model
        for model_id in model_ids:
            if model_id in available_model_ids:
                result["valid_models"].append(model_id)
            else:
                result["invalid_models"].append(model_id)
        
    except NoCredentialsError:
        result["error"] = "AWS credentials not configured"
        result["valid_models"] = model_ids  # Show all, let runtime handle auth
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "Unknown")
        error_msg = e.response.get("Error", {}).get("Message", str(e))
        result["error"] = f"AWS API error ({error_code}): {error_msg}"
        result["valid_models"] = model_ids  # Show all on error
        
    except BotoCoreError as e:
        result["error"] = f"AWS connection error: {str(e)}"
        result["valid_models"] = model_ids  # Show all on error
        
    except Exception as e:
        result["error"] = f"Validation failed: {str(e)}"
        result["valid_models"] = model_ids  # Show all on error
    
    finally:
        result["validation_time_ms"] = int((time.time() - start_time) * 1000)
    
    return result


def get_validated_interactive_models(
    region_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get validated interactive Bedrock models with metadata.
    
    This is a convenience function that validates the curated interactive models
    and returns them with their display metadata.
    
    Args:
        region_name: AWS region (defaults to AWS_DEFAULT_REGION or us-east-1)
        
    Returns:
        Dict containing:
            - models: Dict mapping model_id to metadata (display_name, description, category)
            - validation_result: Full validation result dict
    """
    from ..config import INTERACTIVE_BEDROCK_MODELS, BEDROCK_MODELS
    
    # Get list of interactive model IDs
    model_ids = list(INTERACTIVE_BEDROCK_MODELS.keys())
    
    # Validate
    validation_result = validate_bedrock_models(model_ids, region_name)
    
    # Build validated models dict with full metadata
    models = {}
    for model_id in validation_result["valid_models"]:
        # Merge interactive metadata with full model config
        interactive_meta = INTERACTIVE_BEDROCK_MODELS.get(model_id, {})
        full_config = BEDROCK_MODELS.get(model_id, {})
        
        models[model_id] = {
            **full_config,
            **interactive_meta,
        }
    
    return {
        "models": models,
        "validation_result": validation_result,
    }
