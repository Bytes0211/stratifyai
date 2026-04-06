"""Unit tests for AWS Bedrock model validation helpers."""

from unittest.mock import MagicMock, patch

from botocore.exceptions import NoCredentialsError

from stratifyai.utils.bedrock_validator import (
    get_validated_interactive_models,
    validate_bedrock_models,
)


class TestBedrockValidator:
    @patch("stratifyai.utils.bedrock_validator.BOTO3_AVAILABLE", False)
    def test_validate_bedrock_models_when_boto3_missing(self):
        result = validate_bedrock_models(["model-a"])

        assert result["error"] == "boto3 not installed"
        assert result["valid_models"] == ["model-a"]

    @patch("stratifyai.utils.bedrock_validator.boto3.client")
    @patch("stratifyai.utils.bedrock_validator.BOTO3_AVAILABLE", True)
    def test_validate_bedrock_models_splits_valid_and_invalid(self, mock_client):
        bedrock = MagicMock()
        bedrock.list_foundation_models.return_value = {
            "modelSummaries": [{"modelId": "valid-model"}, {"modelId": "other-model"}]
        }
        mock_client.return_value = bedrock

        result = validate_bedrock_models(["valid-model", "missing-model"], "us-west-2")

        assert result["valid_models"] == ["valid-model"]
        assert result["invalid_models"] == ["missing-model"]
        assert result["error"] is None
        mock_client.assert_called_once_with(
            service_name="bedrock", region_name="us-west-2"
        )

    @patch("stratifyai.utils.bedrock_validator.boto3.client")
    @patch("stratifyai.utils.bedrock_validator.BOTO3_AVAILABLE", True)
    def test_validate_bedrock_models_handles_missing_credentials(self, mock_client):
        mock_client.side_effect = NoCredentialsError()

        result = validate_bedrock_models(["model-a"])

        assert result["error"] == "AWS credentials not configured"
        assert result["valid_models"] == ["model-a"]

    @patch("stratifyai.utils.bedrock_validator.validate_bedrock_models")
    def test_get_validated_interactive_models_merges_metadata(self, mock_validate):
        model_id = "anthropic.claude-3-5-haiku-20241022-v1:0"
        mock_validate.return_value = {
            "valid_models": [model_id],
            "invalid_models": [],
            "validation_time_ms": 1,
            "error": None,
        }

        result = get_validated_interactive_models()

        assert model_id in result["models"]
        assert result["models"][model_id]["display_name"]
        assert result["validation_result"]["valid_models"] == [model_id]
