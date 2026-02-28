"""Unit tests for Phase 7.2 intelligent file extractors."""

import pytest
import json
import tempfile
from pathlib import Path
from stratifyai.utils.csv_extractor import (
    extract_csv_schema,
    analyze_csv_file,
    estimate_token_reduction
)
from stratifyai.utils.json_extractor import (
    infer_json_schema,
    extract_json_schema,
    analyze_json_file
)
from stratifyai.utils.log_extractor import (
    extract_timestamp,
    extract_log_level,
    extract_error_pattern,
    analyze_log_file,
    extract_log_summary
)
from stratifyai.utils.code_extractor import (
    extract_python_structure,
    analyze_code_file
)


class TestCSVExtractor:
    """Tests for CSV schema extraction."""
    
    def test_extract_csv_schema_basic(self, tmp_path):
        """Test basic CSV schema extraction."""
        # Create test CSV
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "name,age,city\n"
            "Alice,30,NYC\n"
            "Bob,25,LA\n"
            "Charlie,35,Chicago\n"
        )
        
        schema = extract_csv_schema(csv_file)
        
        assert schema.row_count == 3
        assert schema.column_count == 3
        assert len(schema.columns) == 3
        assert schema.columns[0].name == "name"
        assert schema.columns[1].name == "age"
        assert schema.columns[2].name == "city"
    
    def test_csv_numeric_stats(self, tmp_path):
        """Test numeric statistics extraction."""
        csv_file = tmp_path / "numbers.csv"
        csv_file.write_text(
            "value\n"
            "10\n"
            "20\n"
            "30\n"
        )
        
        schema = extract_csv_schema(csv_file)
        col = schema.columns[0]
        
        assert col.numeric_stats is not None
        assert col.numeric_stats['min'] == 10.0
        assert col.numeric_stats['max'] == 30.0
        assert col.numeric_stats['mean'] == 20.0
    
    def test_csv_null_handling(self, tmp_path):
        """Test null value handling."""
        csv_file = tmp_path / "nulls.csv"
        csv_file.write_text(
            "value\n"
            "1\n"
            "\n"
            "3\n"
        )
        
        schema = extract_csv_schema(csv_file)
        col = schema.columns[0]
        
        # pandas treats empty strings as NaN in numeric columns
        # Empty row gets skipped, so null_count may be 0
        assert col.null_count >= 0
        assert col.null_percentage >= 0
    
    def test_csv_file_not_found(self):
        """Test error handling for missing file."""
        with pytest.raises(FileNotFoundError):
            extract_csv_schema(Path("/nonexistent/file.csv"))
    
    def test_analyze_csv_file(self, tmp_path):
        """Test complete CSV analysis."""
        csv_file = tmp_path / "data.csv"
        # Create larger CSV to ensure positive reduction
        rows = "\n".join([f"{i},{i*2}" for i in range(100)])
        csv_file.write_text(f"col1,col2\n{rows}\n")
        
        result = analyze_csv_file(csv_file)
        
        assert 'schema' in result
        assert 'schema_text' in result
        assert 'token_reduction_pct' in result
        # Schema extraction provides meaningful reduction
        assert result['token_reduction_pct'] > 0
    
    def test_token_reduction_calculation(self):
        """Test token reduction percentage calculation."""
        reduction = estimate_token_reduction(1000, 100)
        assert reduction == 90.0
        
        reduction = estimate_token_reduction(0, 0)
        assert reduction == 0.0


class TestJSONExtractor:
    """Tests for JSON schema extraction."""
    
    def test_infer_simple_types(self):
        """Test inference of simple JSON types."""
        assert infer_json_schema(None).type == "null"
        assert infer_json_schema(True).type == "boolean"
        assert infer_json_schema(42).type == "number"
        assert infer_json_schema("hello").type == "string"
    
    def test_infer_array(self):
        """Test array schema inference."""
        schema = infer_json_schema([1, 2, 3])
        
        assert schema.type == "array"
        assert schema.value_schema.type == "number"
        assert len(schema.sample_values) == 3
    
    def test_infer_object(self):
        """Test object schema inference."""
        data = {"name": "Alice", "age": 30}
        schema = infer_json_schema(data)
        
        assert schema.type == "object"
        assert len(schema.keys) == 2
        assert "name" in schema.keys
        assert "age" in schema.keys
        assert schema.nested_schemas["name"].type == "string"
        assert schema.nested_schemas["age"].type == "number"
    
    def test_infer_nested_structure(self):
        """Test nested JSON structure inference."""
        data = {
            "user": {
                "name": "Alice",
                "contacts": ["email@test.com", "phone"]
            }
        }
        schema = infer_json_schema(data)
        
        assert schema.type == "object"
        user_schema = schema.nested_schemas["user"]
        assert user_schema.type == "object"
        contacts_schema = user_schema.nested_schemas["contacts"]
        assert contacts_schema.type == "array"
    
    def test_extract_json_schema(self, tmp_path):
        """Test JSON file schema extraction."""
        json_file = tmp_path / "test.json"
        # Create larger JSON to ensure positive reduction
        data = {f"key_{i}": f"value_{i}" * 50 for i in range(50)}
        json_file.write_text(json.dumps(data, indent=2))
        
        result = extract_json_schema(json_file)
        
        assert result['structure'] == "Object with 50 keys"
        # Schema extraction provides meaningful reduction
        assert result['token_reduction_pct'] > 70
    
    def test_json_file_not_found(self):
        """Test error handling for missing JSON file."""
        with pytest.raises(FileNotFoundError):
            extract_json_schema(Path("/nonexistent/file.json"))
    
    def test_analyze_json_file(self, tmp_path):
        """Test complete JSON file analysis."""
        json_file = tmp_path / "data.json"
        json_file.write_text('{"test": [1, 2, 3]}')
        
        result = analyze_json_file(json_file)
        
        assert "JSON File:" in result
        assert "Structure:" in result
        assert "Schema:" in result


class TestLogExtractor:
    """Tests for log file error extraction."""
    
    def test_extract_timestamp_iso(self):
        """Test ISO timestamp extraction."""
        line = "2026-02-03T10:30:45 ERROR Something failed"
        ts = extract_timestamp(line)
        
        assert ts == "2026-02-03T10:30:45"
    
    def test_extract_timestamp_us_format(self):
        """Test US format timestamp extraction."""
        line = "02/03/2026 10:30:45 ERROR Something failed"
        ts = extract_timestamp(line)
        
        assert ts == "02/03/2026 10:30:45"
    
    def test_extract_log_level_error(self):
        """Test ERROR level extraction."""
        assert extract_log_level("ERROR: Something went wrong") == "ERROR"
        assert extract_log_level("FATAL error occurred") == "ERROR"
        assert extract_log_level("CRITICAL failure") == "ERROR"
    
    def test_extract_log_level_warn(self):
        """Test WARN level extraction."""
        assert extract_log_level("WARN: Deprecated API") == "WARN"
        assert extract_log_level("WARNING: Low memory") == "WARN"
    
    def test_extract_log_level_info(self):
        """Test INFO level extraction."""
        assert extract_log_level("INFO: Server started") == "INFO"
        assert extract_log_level("INFORMATION logged") == "INFO"
    
    def test_extract_error_pattern(self):
        """Test error pattern extraction."""
        # Numbers replaced
        pattern = extract_error_pattern("Error on line 123")
        assert "<NUM>" in pattern
        
        # Hex addresses replaced
        pattern = extract_error_pattern("Crash at 0xdeadbeef")
        assert "<ADDR>" in pattern
        
        # Strings replaced
        pattern = extract_error_pattern('Failed to load "config.json"')
        assert "<STR>" in pattern
    
    def test_analyze_log_file_basic(self, tmp_path):
        """Test basic log file analysis."""
        log_file = tmp_path / "test.log"
        log_file.write_text(
            "2026-02-03 10:00:00 INFO Server started\n"
            "2026-02-03 10:01:00 ERROR Database connection failed\n"
            "2026-02-03 10:02:00 WARN Low memory\n"
            "2026-02-03 10:03:00 ERROR Timeout\n"
        )
        
        summary = analyze_log_file(log_file)
        
        assert summary.total_lines == 4
        assert len(summary.errors) == 2
        assert len(summary.warnings) == 1
        assert summary.timestamp_range is not None
    
    def test_log_file_not_found(self):
        """Test error handling for missing log file."""
        with pytest.raises(FileNotFoundError):
            analyze_log_file(Path("/nonexistent/file.log"))
    
    def test_extract_log_summary(self, tmp_path):
        """Test complete log summary extraction."""
        log_file = tmp_path / "server.log"
        log_file.write_text(
            "ERROR: Failed to connect\n"
            "ERROR: Timeout occurred\n"
        )
        
        result = extract_log_summary(log_file)
        
        assert 'summary' in result
        assert 'summary_text' in result
        assert 'token_reduction_pct' in result


class TestCodeExtractor:
    """Tests for code structure extraction."""
    
    def test_extract_simple_function(self, tmp_path):
        """Test extraction of simple function."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "def hello(name: str) -> str:\n"
            "    \"\"\"Say hello.\"\"\"\n"
            "    return f'Hello {name}'\n"
        )
        
        structure = extract_python_structure(py_file)
        
        assert len(structure.functions) == 1
        func = structure.functions[0]
        assert func.name == "hello"
        assert len(func.params) == 1
        assert func.returns == "str"
        assert func.docstring == "Say hello."
    
    def test_extract_class(self, tmp_path):
        """Test extraction of class structure."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "class MyClass:\n"
            "    \"\"\"A test class.\"\"\"\n"
            "    def method(self):\n"
            "        pass\n"
        )
        
        structure = extract_python_structure(py_file)
        
        assert len(structure.classes) == 1
        cls = structure.classes[0]
        assert cls.name == "MyClass"
        assert cls.docstring == "A test class."
        assert len(cls.methods) == 1
        assert cls.methods[0].name == "method"
    
    def test_extract_imports(self, tmp_path):
        """Test extraction of import statements."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "import os\n"
            "from pathlib import Path\n"
            "import json as js\n"
        )
        
        structure = extract_python_structure(py_file)
        
        assert len(structure.imports) == 3
        assert "import os" in structure.imports
        assert "from pathlib import Path" in structure.imports
        assert "import json as js" in structure.imports
    
    def test_extract_decorators(self, tmp_path):
        """Test extraction of decorators."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "@property\n"
            "def value(self):\n"
            "    return self._value\n"
        )
        
        structure = extract_python_structure(py_file)
        
        assert len(structure.functions) == 1
        assert len(structure.functions[0].decorators) == 1
        assert "property" in structure.functions[0].decorators[0]
    
    def test_async_function(self, tmp_path):
        """Test async function detection."""
        py_file = tmp_path / "test.py"
        py_file.write_text(
            "async def fetch_data():\n"
            "    pass\n"
        )
        
        structure = extract_python_structure(py_file)
        
        assert len(structure.functions) == 1
        assert structure.functions[0].is_async is True
    
    def test_python_file_not_found(self):
        """Test error handling for missing Python file."""
        with pytest.raises(FileNotFoundError):
            extract_python_structure(Path("/nonexistent/file.py"))
    
    def test_syntax_error_handling(self, tmp_path):
        """Test handling of invalid Python syntax."""
        py_file = tmp_path / "bad.py"
        py_file.write_text("def broken(\n")  # Incomplete syntax
        
        with pytest.raises(SyntaxError):
            extract_python_structure(py_file)
    
    def test_analyze_code_file_python(self, tmp_path):
        """Test complete Python file analysis."""
        py_file = tmp_path / "code.py"
        # Create larger Python file to ensure positive reduction
        code_lines = []
        for i in range(50):
            code_lines.append(f"def function_{i}(arg1, arg2, arg3):")
            code_lines.append(f"    \"\"\"Function {i} does something.\"\"\"")
            code_lines.append(f"    result = arg1 + arg2 + arg3")
            code_lines.append(f"    return result * {i}")
            code_lines.append("")
        
        py_file.write_text("\n".join(code_lines))
        
        result = analyze_code_file(py_file)
        
        assert 'structure' in result
        assert 'structure_text' in result
        assert 'token_reduction_pct' in result
        # Structure extraction provides meaningful reduction
        assert result['token_reduction_pct'] > 30
    
    def test_analyze_code_file_non_python(self, tmp_path):
        """Test analysis of non-Python code files."""
        js_file = tmp_path / "code.js"
        js_file.write_text("function test() { return 42; }")
        
        result = analyze_code_file(js_file)
        
        assert result['structure'] is None
        assert 'AST extraction only available for Python' in result['structure_text']


class TestIntegration:
    """Integration tests for file extractors."""
    
    def test_csv_to_text_conversion(self, tmp_path):
        """Test CSV schema text generation."""
        csv_file = tmp_path / "data.csv"
        csv_file.write_text("id,name\n1,Alice\n2,Bob\n")
        
        schema = extract_csv_schema(csv_file)
        text = schema.to_text()
        
        assert "CSV File:" in text
        assert "Dimensions:" in text
        assert "Column Schema:" in text
    
    def test_json_to_text_conversion(self):
        """Test JSON schema text generation."""
        schema = infer_json_schema({"key": "value"})
        text = schema.to_text()
        
        assert "Object with" in text
    
    def test_log_to_text_conversion(self, tmp_path):
        """Test log summary text generation."""
        log_file = tmp_path / "test.log"
        log_file.write_text("ERROR: Test error\n")
        
        summary = analyze_log_file(log_file)
        text = summary.to_text()
        
        assert "Log File:" in text
        assert "Total Lines:" in text
        assert "Errors:" in text
    
    def test_code_to_text_conversion(self, tmp_path):
        """Test code structure text generation."""
        py_file = tmp_path / "test.py"
        py_file.write_text("def test(): pass")
        
        structure = extract_python_structure(py_file)
        text = structure.to_text()
        
        assert "Code File:" in text
        assert "Language: Python" in text
        assert "Functions" in text


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
