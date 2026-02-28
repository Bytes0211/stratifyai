"""Code structure extraction for intelligent file analysis.

This module extracts structural information from code files using AST to reduce
token usage by 80%+ while preserving essential code structure.
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any


@dataclass
class FunctionInfo:
    """Information about a function."""
    name: str
    line_number: int
    params: List[str]
    returns: Optional[str] = None
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_async: bool = False


@dataclass
class ClassInfo:
    """Information about a class."""
    name: str
    line_number: int
    bases: List[str]
    methods: List[FunctionInfo]
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)


@dataclass
class CodeStructure:
    """Complete code structure information."""
    file_path: str
    language: str
    imports: List[str]
    functions: List[FunctionInfo]
    classes: List[ClassInfo]
    total_lines: int
    docstring: Optional[str] = None
    
    def to_text(self) -> str:
        """Convert structure to human-readable text.
        
        Returns:
            Formatted code structure
        """
        lines = [
            f"Code File: {self.file_path}",
            f"Language: {self.language}",
            f"Total Lines: {self.total_lines:,}",
        ]
        
        if self.docstring:
            lines.append(f"\nModule Docstring:\n  {self.docstring[:200]}")
        
        # Imports
        if self.imports:
            lines.append(f"\nImports ({len(self.imports)}):")
            for imp in self.imports[:20]:  # Show first 20
                lines.append(f"  - {imp}")
            if len(self.imports) > 20:
                lines.append(f"  ... and {len(self.imports) - 20} more")
        
        # Functions
        if self.functions:
            lines.append(f"\nFunctions ({len(self.functions)}):")
            for func in self.functions:
                decorators = f"@{', @'.join(func.decorators)} " if func.decorators else ""
                async_prefix = "async " if func.is_async else ""
                params = ", ".join(func.params)
                returns = f" -> {func.returns}" if func.returns else ""
                lines.append(f"  [Line {func.line_number}] {decorators}{async_prefix}def {func.name}({params}){returns}")
                if func.docstring:
                    lines.append(f"      \"{func.docstring[:100]}\"")
        
        # Classes
        if self.classes:
            lines.append(f"\nClasses ({len(self.classes)}):")
            for cls in self.classes:
                decorators = f"@{', @'.join(cls.decorators)} " if cls.decorators else ""
                bases = f"({', '.join(cls.bases)})" if cls.bases else ""
                lines.append(f"  [Line {cls.line_number}] {decorators}class {cls.name}{bases}:")
                if cls.docstring:
                    lines.append(f"      \"{cls.docstring[:100]}\"")
                if cls.methods:
                    lines.append(f"      Methods ({len(cls.methods)}):")
                    for method in cls.methods[:10]:  # Show first 10 methods
                        params = ", ".join(method.params)
                        lines.append(f"        - {method.name}({params})")
                    if len(cls.methods) > 10:
                        lines.append(f"        ... and {len(cls.methods) - 10} more")
        
        return "\n".join(lines)


class PythonASTVisitor(ast.NodeVisitor):
    """AST visitor to extract code structure from Python files."""
    
    def __init__(self):
        self.imports: List[str] = []
        self.functions: List[FunctionInfo] = []
        self.classes: List[ClassInfo] = []
        self.current_class: Optional[str] = None
    
    def visit_Import(self, node: ast.Import):
        """Visit import statement."""
        for alias in node.names:
            import_str = alias.name
            if alias.asname:
                import_str += f" as {alias.asname}"
            self.imports.append(f"import {import_str}")
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Visit from...import statement."""
        module = node.module or ""
        for alias in node.names:
            import_str = alias.name
            if alias.asname:
                import_str += f" as {alias.asname}"
            self.imports.append(f"from {module} import {import_str}")
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Visit function definition."""
        self._process_function(node, is_async=False)
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef):
        """Visit async function definition."""
        self._process_function(node, is_async=True)
        self.generic_visit(node)
    
    def _process_function(self, node, is_async: bool):
        """Process function/method node."""
        # Extract parameters
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                try:
                    param_name += f": {ast.unparse(arg.annotation)}"
                except:
                    pass
            params.append(param_name)
        
        # Extract return type
        returns = None
        if node.returns:
            try:
                returns = ast.unparse(node.returns)
            except:
                pass
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        if docstring:
            docstring = docstring.split('\n')[0]  # First line only
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except:
                decorators.append("@decorator")
        
        func_info = FunctionInfo(
            name=node.name,
            line_number=node.lineno,
            params=params,
            returns=returns,
            docstring=docstring,
            decorators=decorators,
            is_async=is_async
        )
        
        # Add to appropriate list
        if self.current_class:
            # Find the class and add method
            for cls in self.classes:
                if cls.name == self.current_class:
                    cls.methods.append(func_info)
                    break
        else:
            self.functions.append(func_info)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Visit class definition."""
        # Extract base classes
        bases = []
        for base in node.bases:
            try:
                bases.append(ast.unparse(base))
            except:
                bases.append("BaseClass")
        
        # Extract docstring
        docstring = ast.get_docstring(node)
        if docstring:
            docstring = docstring.split('\n')[0]  # First line only
        
        # Extract decorators
        decorators = []
        for decorator in node.decorator_list:
            try:
                decorators.append(ast.unparse(decorator))
            except:
                decorators.append("@decorator")
        
        class_info = ClassInfo(
            name=node.name,
            line_number=node.lineno,
            bases=bases,
            methods=[],
            docstring=docstring,
            decorators=decorators
        )
        
        self.classes.append(class_info)
        
        # Visit methods
        old_class = self.current_class
        self.current_class = node.name
        self.generic_visit(node)
        self.current_class = old_class


def extract_python_structure(file_path: Path) -> CodeStructure:
    """Extract structure from Python file using AST.
    
    Args:
        file_path: Path to Python file
        
    Returns:
        CodeStructure object
        
    Raises:
        FileNotFoundError: If file doesn't exist
        SyntaxError: If Python code is malformed
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Python file not found: {file_path}")
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        source_code = f.read()
    
    # Parse AST
    try:
        tree = ast.parse(source_code, filename=str(file_path))
    except SyntaxError as e:
        raise SyntaxError(f"Failed to parse {file_path}: {e}")
    
    # Extract module docstring
    docstring = ast.get_docstring(tree)
    if docstring:
        docstring = docstring.split('\n')[0]  # First line only
    
    # Visit AST
    visitor = PythonASTVisitor()
    visitor.visit(tree)
    
    # Count lines
    total_lines = source_code.count('\n') + 1
    
    return CodeStructure(
        file_path=str(file_path),
        language="Python",
        imports=visitor.imports,
        functions=visitor.functions,
        classes=visitor.classes,
        total_lines=total_lines,
        docstring=docstring
    )


def analyze_code_file(file_path: Path) -> Dict[str, Any]:
    """Analyze a code file and return structure information.
    
    Args:
        file_path: Path to code file
        
    Returns:
        Dictionary with structure and metadata
    """
    # Detect language from extension
    extension = file_path.suffix.lower()
    
    if extension == '.py':
        structure = extract_python_structure(file_path)
        structure_text = structure.to_text()
        
        # Calculate sizes
        original_size = file_path.stat().st_size
        structure_size = len(structure_text)
        
        return {
            'structure': structure,
            'structure_text': structure_text,
            'original_size_bytes': original_size,
            'structure_size_bytes': structure_size,
            'token_reduction_pct': ((original_size - structure_size) / original_size * 100) if original_size > 0 else 0.0,
            'recommended_action': 'Use structure for LLM analysis instead of full code'
        }
    else:
        # For non-Python files, return basic info
        original_size = file_path.stat().st_size
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        structure_text = f"Code File: {file_path}\nLanguage: {extension[1:] if extension else 'unknown'}\nTotal Lines: {len(lines)}\n\nNote: AST extraction only available for Python files."
        
        return {
            'structure': None,
            'structure_text': structure_text,
            'original_size_bytes': original_size,
            'structure_size_bytes': len(structure_text),
            'token_reduction_pct': 0.0,
            'recommended_action': 'Full file analysis required (non-Python)'
        }
