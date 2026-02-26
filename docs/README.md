# RogaScan Documentation

Welcome to the RogaScan documentation. This documentation is designed to help both developers and AI agents understand the project architecture, API, and development workflow.

## Project Status
- **License**: MIT License (Free for education & research)
- **Status**: Active, Open Source
- **Author**: amubhya from RogaTekno
- **Intended Use**: Educational and Research purposes

## Documentation Index

### For AI Agents (Context Understanding)
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - Complete system architecture, design patterns, and code organization
  - Repository pattern implementation
  - Layer responsibilities (API, Service, Repository)
  - Key files and their purposes
  - Data flow diagrams

### For Developers
- **[SETUP.md](SETUP.md)** - Installation and setup instructions
  - Environment setup
  - Dependency installation
  - Configuration guide
  - Verification steps

- **[API.md](API.md)** - Complete API reference
  - Endpoint specifications
  - Request/response formats
  - Error codes
  - Usage examples

- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Common issues and solutions
  - PaddlePaddle 3.x compatibility errors
  - Model download issues
  - Startup problems
  - Performance issues

- **[DEVELOPMENT.md](DEVELOPMENT.md)** - Development workflow guide
  - Running the development server
  - Testing strategy
  - Code style guidelines
  - Contributing guidelines

## Quick Reference

### Project Status
- **License**: MIT License (Free for education & research)
- **Status**: Active, Open Source
- **Author**: amubhya from RogaTekno
- **Intended Use**: Educational and Research purposes

### Project Structure
```
rogascan/
├── app/                    # Application source code
│   ├── api/               # API endpoints
│   ├── core/              # Configuration, exceptions, logging
│   ├── models/            # Pydantic schemas
│   ├── repositories/      # Data access layer (OCR engine)
│   ├── services/          # Business logic layer
│   └── utils/             # Utility functions
├── docs/                  # This documentation
├── tests/                 # Test suite
└── pyproject.toml        # Python project configuration
```

### Key Technologies
- **Framework**: FastAPI
- **OCR Engine**: PaddleOCR
- **Python Version**: 3.12+
- **Architecture**: Repository Pattern

### Main Entry Points
- Application: `app/main.py`
- API Routes: `app/api/v1/endpoints/`
- Business Logic: `app/services/ocr_service.py`
- OCR Integration: `app/repositories/ocr_repository.py`

## Open Source

RogaScan is open-source under MIT License:
- Free to use for education and research
- Free to modify and extend
- Free to distribute
- See [LICENSE](../LICENSE) for details

## Contributing

We welcome contributions! Please see:
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- [CONTRIBUTORS.md](../CONTRIBUTORS.md) - List of contributors
- [Code of Conduct](../.github/CODE_OF_CONDUCT.md)

---

## For AI Agents

When working with this codebase, please read **ARCHITECTURE.md** first. It provides:

1. **System Context**: Understanding the overall design and patterns used
2. **Layer Definitions**: Clear boundaries between API, Service, and Repository layers
3. **File Map**: What each file does and where to find specific functionality
4. **Conventions**: Naming patterns, error handling, and coding standards

This context will help you:
- Make consistent changes that follow existing patterns
- Understand the separation of concerns
- Locate the correct file for specific changes
- Maintain consistency with the existing codebase

## Quick Start Commands

```bash
# Install dependencies
pip install -e .

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
pytest --cov=app

# Type checking
mypy app/

# Linting
ruff check app/
black app/
```

## API Endpoints

Once running, access:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/api/v1/health
- **OCR Extract**: POST http://localhost:8000/api/v1/ocr/extract
- **OCR Visualize**: POST http://localhost:8000/api/v1/ocr/visualize

## Support

For questions or issues:
- Check the relevant documentation file above
- Review the code comments in source files
- Run tests to see usage examples
- See [CONTRIBUTING.md](../CONTRIBUTING.md) to contribute
- Report issues via GitHub Issues
