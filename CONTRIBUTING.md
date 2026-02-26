# Contributing to SnapText

Thank you for your interest in contributing to SnapText! This project is designed for **education and research**, and we welcome contributions from the community to improve its quality and functionality.

## Table of Contents

- [How to Contribute](#how-to-contribute)
- [Development Guidelines](#development-guidelines)
- [Code of Conduct](#code-of-conduct)
- [Getting Help](#getting-help)

---

## How to Contribute

### 1. Report Issues

If you find a bug or have a suggestion:

1. Check if the issue already exists in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear and specific title
   - Detailed description of the problem
   - Steps to reproduce (if bug)
   - Environment information (OS, Python version, etc.)
   - Screenshots/error logs (if relevant)

### 2. Submit Pull Requests

#### Fork and Clone

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/snaptext.git
cd snaptext

# Add upstream
git remote add upstream https://github.com/RogaTekno/snaptext.git
```

#### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install dev tools
pip install pytest pytest-asyncio pytest-cov black ruff mypy

# Run tests to verify setup
pytest
```

#### Create a New Branch

```bash
# Sync with upstream
git fetch upstream
git checkout main
git merge upstream/main

# Create a branch for your feature/fix
git checkout -b feature/your-feature-name
# or
git checkout -b fix/bug-description
```

#### Make Your Changes

1. Follow the existing architecture - See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. Add tests for new features
3. Update documentation if needed
4. Format code with Black
5. Lint code with Ruff

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/ --fix

# Type check
mypy app/

# Run tests
pytest --cov=app
```

#### Commit with Clear Messages

Use [Conventional Commits](https://www.conventionalcommits.org/) format:

```
feat: add Arabic language support
fix: handle error on large image files
docs: update API documentation
test: add tests for visualization endpoint
refactor: simplify image validation
```

Example:

```bash
git add .
git commit -m "feat: add watermark on OCR visualization"
```

#### Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create a Pull Request on GitHub
```

In your PR description, explain:
- What you changed and why
- Related issues (if any)
- Screenshots for UI changes
- How to test your changes

### 3. Opportunities for Contribution

SnapText has solid generic OCR capabilities. Here are exciting opportunities to expand the project:

#### Document-Specific Processors

Build intelligent extractors for specific document types:

**Indonesian Documents** (High Priority):
- **KTP (Kartu Tanda Penduduk)** - ID Card field extractor
  - Extract: NIK, name, birth date/place, gender, address, religion, marital status
  - Validate: 16-digit NIK checksum
  - Output: Structured JSON with all fields

- **KK (Kartu Keluarga)** - Family Card parser
  - Extract: Card number, head of family, family member details
  - Validate: KK number format
  - Output: Structured family data

- **BPJS Cards** - Insurance card extractors
  - BPJS Kesehatan (13-digit number)
  - BPJS Ketenagakerjaan (11-digit number)
  - Extract participant and coverage information

- **Bank Documents** - Statement and passbook parser
  - Multiple bank formats
  - Account numbers, balances, transactions
  - Date and amount extraction

**Implementation Approach**:
1. Create mapper class in `app/services/mappers/`
2. Add validation rules for each document type
3. Create dedicated API endpoints
4. Add comprehensive tests
5. Document with examples

#### Infrastructure Enhancements

**Deployment & Operations**:
- Docker containerization for easy deployment
- Docker Compose for full stack setup
- Health check improvements
- Monitoring and metrics

**Performance & Scalability**:
- Redis caching layer for repeated documents
- Batch processing endpoint for multiple images
- Celery/Redis queue for async processing
- Database integration for result storage
- CDN support for visualized images

**User Experience**:
- WebSocket support for real-time updates
- Progress indicators for long operations
- Mobile-optimized API responses
- Client SDKs (Python, JavaScript)

#### Quality Improvements

**Testing**:
- Increase test coverage to 80%+
- Add integration tests for all endpoints
- Performance benchmarking tests
- Load testing configurations

**Documentation**:
- More usage examples
- Tutorial for building custom extractors
- Video tutorials for common tasks
- API cookbook with recipes

**Core Features**:
- Additional language models
- Image preprocessing options
- Custom watermark configuration
- Export formats (PDF, DOCX, etc.)

#### How to Get Started

**Example: Adding KTP Extractor**

1. **Create the mapper**:
```python
# app/services/mappers/ktp_mapper.py
class KTPMapper:
    def extract(self, ocr_result: dict) -> dict:
        # Parse OCR text
        # Extract fields using regex/patterns
        # Validate NIK checksum
        # Return structured data
        pass
```

2. **Add endpoint**:
```python
# app/api/v1/endpoints/documents.py
@router.post("/extract/ktp")
async def extract_ktp(file: UploadFile):
    # Run OCR
    # Apply KTP mapper
    # Return structured data
    pass
```

3. **Add tests**:
```python
# tests/test_mappers/test_ktp_mapper.py
def test_extract_nik():
    # Test NIK extraction
    pass
```

4. **Document and contribute!**

**Ready to contribute?** We're here to help! Open an issue to discuss your proposed feature, and we'll guide you through the process.

---

## Development Guidelines

### Code Style

- Python 3.12+ type hints
- Google-style docstrings
- Follow PEP 8
- Max line length: 100 characters
- Use `|` for union types

### Architecture

Follow the layer architecture:

- **API Layer**: `app/api/` - HTTP handlers
- **Service Layer**: `app/services/` - Business logic
- **Repository Layer**: `app/repositories/` - Data access
- **Core**: `app/core/` - Config, exceptions, logging

### Testing

- Minimum 70% test coverage
- Unit tests for services and repositories
- Integration tests for endpoints
- Use fixtures for test data

### Documentation

- Update README for new features
- Add/update docs/ if needed
- Docstrings for public functions
- Comments for complex logic

### Contribution Terms

By contributing, you agree that:

1. **License**: Your contributions will be licensed under MIT License
2. **Originality**: You have the rights to contribute the code
3. **Non-Competitive**: Not for directly competing with the original project
4. **Educational Focus**: Aligned with learning and research goals
5. **Respect**: Respectful to other contributors and users

### Review Process

- PRs will be reviewed by the maintainer
- Feedback will be provided within 1-7 days
- Changes may be requested
- Approval required before merge
- Squash merge to maintain clean history

### Recognition

Contributors will be acknowledged in:

- `CONTRIBUTORS.md` file
- Release notes
- About section in documentation

---

## Code of Conduct

### Our Standards

Examples of behavior that contributes to a positive environment:

- Demonstrating empathy and kindness toward other people
- Being respectful of differing opinions, viewpoints, and experiences
- Giving and gracefully accepting constructive feedback
- Accepting responsibility and apologizing to those affected by our mistakes
- Focusing on what is best not just for us as individuals, but for the overall community

Examples of unacceptable behavior:

- The use of sexualized language or imagery, and sexual attention or advances of any kind
- Trolling, insulting or derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information, such as a physical or email address, without their explicit permission
- Other conduct which could reasonably be considered inappropriate in a professional setting

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the community leaders responsible for enforcement.

All complaints will be reviewed and investigated promptly and fairly.

---

## For Researchers & Students

We strongly support academic and educational use:

### For Researchers

- Explain your research topic
- Share papers/publications that use SnapText
- Consider contributing improvements back

### For Students

- Suitable for thesis, dissertation, or coursework
- Learn FastAPI, OCR, and clean architecture
- Build portfolio with open-source contributions
- Mention on your CV/portfolio

### For Lecturers

- Use for teaching materials
- Contribute course improvements
- Student projects can be merged

---

## Getting Help

If you need assistance:

- Read [docs/](docs/) for complete documentation
- Open a discussion for questions
- Create an issue for bug reports
- Contact maintainer for important matters

### Resources

- [ARCHITECTURE.md](docs/ARCHITECTURE.md) - System design and patterns
- [SETUP.md](docs/SETUP.md) - Installation and configuration
- [API.md](docs/API.md) - Complete API reference
- [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) - Common issues and solutions
- [DEVELOPMENT.md](docs/DEVELOPMENT.md) - Development workflow

---

## Contact

- **Maintainer**: amubhya
- **Organization**: RogaTekno

---

## License

All contributions are licensed under [MIT License](LICENSE) - see LICENSE file for details.

---

**Thank you for contributing to SnapText!**

Together we make OCR technology accessible for everyone.
