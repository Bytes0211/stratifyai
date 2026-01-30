# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Project Overview

StratumAI is [describe what the project does]. The project demonstrates [key capabilities and technologies].

## Development Environment Setup

### Initial Setup
```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Using uv (Alternative)
```bash
# Create virtual environment with uv
uv venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies with uv
uv pip install -r requirements.txt
```

## Project Structure

```txt
stratumai/
├── README.md              # Project overview
├── project-status.md      # Project timeline and status
├── WARP.md                # This file (development guidance)
├── requirements.txt       # Python dependencies
├── .venv/                 # Virtual environment
└── [other directories]
```

## Testing

### Running Tests
```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_example.py

# Run specific test
pytest tests/test_example.py::test_function_name
```

## Common Workflows

### Starting Development
```bash
# Activate virtual environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# [Additional setup steps]
```

### Adding Dependencies
```bash
# Install new package
pip install package-name

# Update requirements.txt
pip freeze > requirements.txt
```

## Architecture Principles

[Describe key architectural decisions and patterns]

### Key Design Decisions
1. [Decision 1]
2. [Decision 2]
3. [Decision 3]

## Project Status

**Current Phase:** Initial Setup  
**Progress:** 20% Phase 0  
**Latest Updates:** Project initialized with virtual environment and documentation (Jan 30, 2026)

### Completed Phases
- ✅ Phase 0: Initial project setup (20%)
  - Project structure created
  - Virtual environment configured
  - Documentation templates established

### Next Steps
- 📝 Define project requirements
- 📝 Design system architecture
- 📝 Select technology stack
- 📝 Begin implementation

## Documentation

### Core Documentation
- **README.md** - Project overview and setup instructions
- **project-status.md** - Detailed project timeline and progress
- **WARP.md** - This file (development environment guidance)

## Troubleshooting

### Common Issues

**Virtual Environment Not Found:**
```bash
# Recreate if .venv is missing
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Dependency Issues:**
```bash
# Update pip
pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

## Development Best Practices

### Code Style
- Follow PEP 8 for Python code
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and single-purpose

### Git Practices
- Never commit `.env` files or credentials
- Use `.gitignore` for environment files
- Write descriptive commit messages
- Include co-author line: `Co-Authored-By: Warp <agent@warp.dev>`

## Git Commit Convention

Use conventional commit format: `type(scope): brief description`

### Commit Types
- **feat**: New feature or functionality
- **fix**: Bug fix
- **docs**: Documentation changes
- **refactor**: Code refactoring without functionality change
- **test**: Adding or updating tests
- **chore**: Maintenance tasks (dependencies, config, infrastructure)
- **perf**: Performance improvements
- **style**: Code style/formatting changes

### Project Scopes
- **core**: Core functionality
- **api**: API endpoints
- **ui**: User interface
- **data**: Data processing
- **docs**: Documentation
- **tests**: Testing
- **config**: Configuration

### Guidelines
- Keep first line under 72 characters
- Use imperative mood ("add" not "added")
- Always include: `Co-Authored-By: Warp <agent@warp.dev>`
- Scope is optional but recommended
- Reference issues when applicable: `fix(api): resolve connection issue (#123)`

## Technical Constraints

### Must Maintain
- [Constraint 1]
- [Constraint 2]
- [Constraint 3]

### Security Requirements
- Never commit secrets or credentials
- Use environment variables for sensitive data
- [Additional security requirements]

### Performance Targets
- [Target 1]
- [Target 2]
- [Target 3]
