# Contributing to uwacomm

Thank you for your interest in contributing to uwacomm! This document provides guidelines and instructions for contributing.

## Getting Started

### Development Setup

1. **Fork and clone the repository**

```bash
git clone https://github.com/YOUR_USERNAME/uwacomm.git
cd uwacomm
```

2. **Create a virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install development dependencies**

```bash
pip install -e ".[dev]"
```

## Development Workflow

### Before Making Changes

1. **Create a feature branch**

```bash
git checkout -b feature/your-feature-name
```

2. **Ensure tests pass**

```bash
pytest
```

### Making Changes

1. **Follow the coding standards** (see below)
2. **Write tests** for new functionality
3. **Update documentation** as needed
4. **Add changelog entry** in CHANGELOG.md

### Submitting Changes

1. **Run the full test suite**

```bash
pytest --cov=uwacomm
```

2. **Run linters and formatters**

```bash
black src tests examples
ruff check src tests examples
mypy src
```

3. **Commit your changes**

```bash
git add .
git commit -m "feat: add new feature description"
```

4. **Push to your fork**

```bash
git push origin feature/your-feature-name
```

5. **Open a Pull Request** on GitHub

## Coding Standards

### Style Guidelines

- **PEP 8**: Follow Python style guide
- **Type hints**: All functions must have type hints
- **Docstrings**: Use Google-style docstrings for all public APIs
- **Line length**: 100 characters (enforced by black)

### Example

```python
from __future__ import annotations

from typing import Optional


def example_function(value: int, optional: Optional[str] = None) -> bool:
    """Short description of what this function does.

    Longer description if needed, explaining the purpose, behavior,
    and any important details.

    Args:
        value: Description of the value parameter
        optional: Description of the optional parameter

    Returns:
        Description of what is returned

    Raises:
        ValueError: When and why this exception is raised

    Example:
        >>> result = example_function(42, "test")
        >>> print(result)
        True
    """
    if optional is None:
        return value > 0
    return len(optional) > value
```

### Testing Requirements

- **Unit tests**: Required for all new functions
- **Integration tests**: Required for new features
- **Property tests**: Encouraged for codecs and utilities
- **Coverage**: Aim for >90% test coverage

### Test Example

```python
import pytest
from uwacomm import encode, decode, BaseMessage


class TestNewFeature:
    """Test suite for new feature."""

    def test_basic_functionality(self) -> None:
        """Test basic use case."""
        # Arrange
        msg = MyMessage(field=42)

        # Act
        result = encode(msg)

        # Assert
        assert len(result) > 0
        decoded = decode(MyMessage, result)
        assert decoded.field == 42

    def test_edge_case(self) -> None:
        """Test edge case handling."""
        with pytest.raises(ValueError, match="expected pattern"):
            problematic_function(invalid_input)
```

## Pull Request Guidelines

### PR Checklist

- [ ] Tests pass locally
- [ ] Code follows style guidelines (black, ruff, mypy)
- [ ] New tests added for new functionality
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Commit messages follow convention (see below)

### Commit Message Convention

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Test changes
- `chore`: Build process or tooling changes

**Examples:**

```
feat(codec): add varint encoding support

Implements variable-length integer encoding for more efficient
representation of small integers.

Closes #42
```

```
fix(framing): correct CRC-16 calculation

The CRC-16 polynomial was incorrect for CCITT standard.
Updated to use 0x1021 polynomial.

Fixes #123
```

## Release Process

### Automated Releases

This project uses [python-semantic-release](https://python-semantic-release.readthedocs.io/)
for automated versioning and releases.

**How it works:**
1. Push commits to `main` following Conventional Commits
2. CI runs tests
3. semantic-release analyzes commits and bumps version
4. CHANGELOG.md updated automatically
5. Git tag created
6. GitHub Release published
7. Package published to PyPI

**Version bump rules:**
- `feat:` → Minor (0.1.0 → 0.2.0)
- `fix:` → Patch (0.1.0 → 0.1.1)
- `BREAKING CHANGE:` in footer → Major (0.1.0 → 1.0.0)

**Breaking change example:**
```bash
git commit -m "feat(codec): change encoding format

BREAKING CHANGE: Encoding format changed from big-endian to little-endian."
```

### Manual Release (Emergency Only)

If automation fails:
1. Update version in `pyproject.toml` and `src/uwacomm/__init__.py`
2. Update `CHANGELOG.md`
3. `git commit -m "chore(release): v0.x.y"`
4. `git tag -a v0.x.y -m "Release v0.x.y"`
5. `git push origin main --tags`

## Areas for Contribution

### High Priority

- [ ] Float/double encoding with precision and scale
- [ ] Nested message support
- [ ] Variable-length arrays and strings
- [ ] Zigzag encoding for signed integers
- [ ] Comprehensive user guide documentation

### Medium Priority

- [ ] Little-endian encoding option
- [ ] Delta encoding
- [ ] Schema versioning utilities
- [ ] Protobuf object conversion (not just schema)
- [ ] More examples and tutorials

### Low Priority

- [ ] Advanced framing (preamble/ASM)
- [ ] Fragmentation and reassembly
- [ ] ROS2 integration examples
- [ ] Performance optimizations

## Questions or Issues?

- **Bug reports**: [Open an issue](https://github.com/patel999jay/uwacomm/issues/new?template=bug_report.md)
- **Feature requests**: [Open an issue](https://github.com/patel999jay/uwacomm/issues/new?template=feature_request.md)
- **Questions**: [Start a discussion](https://github.com/patel999jay/uwacomm/discussions)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
