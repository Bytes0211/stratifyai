"""
Validates available Amazon Bedrock models and compares with StratifyAI config.
"""
import logging
import json
import boto3
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def list_foundation_models(bedrock_client):
    """
    Gets a list of available Amazon Bedrock foundation models.

    :return: The list of available bedrock foundation models.
    """
    try:
        response = bedrock_client.list_foundation_models()
        models = response["modelSummaries"]
        logger.info("Got %s foundation models.", len(models))
        return models
    except ClientError:
        logger.error("Couldn't list foundation models.")
        raise


def main():
    """Entry point for the example."""
    
    # Import StratifyAI config
    from stratifyai.config import BEDROCK_MODELS
    
    aws_region = "us-east-1"
    
    print(f"\n{'='*80}")
    print(f"Validating Bedrock Models in Region: {aws_region}")
    print(f"{'='*80}\n")
    
    # Get models from AWS
    bedrock_client = boto3.client(service_name="bedrock", region_name=aws_region)
    fm_models = list_foundation_models(bedrock_client)
    
    # Create lookup of available models
    available_model_ids = {model["modelId"] for model in fm_models}
    available_models_by_provider = {}
    for model in fm_models:
        provider = model["providerName"]
        if provider not in available_models_by_provider:
            available_models_by_provider[provider] = []
        available_models_by_provider[provider].append(model)
    
    # Check which models in our config are available
    print(f"\n{'='*80}")
    print("StratifyAI Config Validation")
    print(f"{'='*80}\n")
    
    valid_models = []
    invalid_models = []
    
    for model_id in BEDROCK_MODELS.keys():
        if model_id in available_model_ids:
            status = "✓ VALID"
            valid_models.append(model_id)
        else:
            status = "✗ INVALID"
            invalid_models.append(model_id)
        print(f"{status:12} | {model_id}")
    
    # Summary
    print(f"\n{'='*80}")
    print("Summary")
    print(f"{'='*80}")
    print(f"Total in config:  {len(BEDROCK_MODELS)}")
    print(f"Valid models:     {len(valid_models)} ✓")
    print(f"Invalid models:   {len(invalid_models)} ✗")
    
    # Show invalid models with suggestions
    if invalid_models:
        print(f"\n{'='*80}")
        print("Invalid Models - Need to be updated in config.py")
        print(f"{'='*80}\n")
        for model_id in invalid_models:
            print(f"✗ {model_id}")
            # Try to find similar model
            provider_prefix = model_id.split('.')[0]
            print(f"  Available {provider_prefix} models:")
            for avail_model in fm_models:
                if avail_model["modelId"].startswith(provider_prefix):
                    print(f"    - {avail_model['modelId']}")
            print()
    
    # Show available models NOT in config
    print(f"\n{'='*80}")
    print("Available Models NOT in StratifyAI Config")
    print(f"{'='*80}\n")
    
    config_model_ids = set(BEDROCK_MODELS.keys())
    new_models = available_model_ids - config_model_ids
    
    if new_models:
        # Group by provider
        new_by_provider = {}
        for model in fm_models:
            if model["modelId"] in new_models:
                provider = model["providerName"]
                if provider not in new_by_provider:
                    new_by_provider[provider] = []
                new_by_provider[provider].append(model)
        
        for provider in sorted(new_by_provider.keys()):
            print(f"\n{provider}:")
            for model in new_by_provider[provider]:
                print(f"  - {model['modelId']}")
                if "inputModalities" in model:
                    print(f"    Input: {', '.join(model['inputModalities'])}")
                if "outputModalities" in model:
                    print(f"    Output: {', '.join(model['outputModalities'])}")
    else:
        print("None - all available models are in config!")
    
    # Full model details (optional - commented out by default)
    print(f"\n{'='*80}")
    print("Detailed Model Information")
    print(f"{'='*80}\n")
    print("Showing models by provider:\n")
    
    for provider in sorted(available_models_by_provider.keys()):
        print(f"\n{provider} ({len(available_models_by_provider[provider])} models):")
        for model in available_models_by_provider[provider]:
            in_config = "✓" if model["modelId"] in config_model_ids else " "
            print(f"  [{in_config}] {model['modelId']}")
    
    logger.info("\nValidation complete!")


if __name__ == "__main__":
    main()
