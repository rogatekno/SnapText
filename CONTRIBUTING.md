# Contributing to RogaScan

Thank you for your interest in contributing to RogaScan! This project is designed for **education and research**, and we welcome contributions from the community to improve its quality and functionality.

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
git clone https://github.com/YOUR_USERNAME/rogascan.git
cd rogascan

# Add upstream
git remote add upstream https://github.com/RogaTekno/rogascan.git
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

1. **Follow the existing architecture** - See [ARCHITECTURE.md](docs/ARCHITECTURE.md)
2. **Add tests** for new features
3. **Update documentation** if needed
4. **Format code** with Black
5. **Lint code** with Ruff

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

### 3. Areas That Need Contributions

We are looking for contributions in:

- [ ] **Language Support**: Add OCR support for more languages
- [ ] **Document Mapping**: Implement field extraction for KTP, KK, BPJS, etc.
- [ ] **Batch Processing**: Endpoint for multiple files
- [ ] **Caching**: Redis cache for OCR results
- [ ] **Queue System**: Celery/Redis for async processing
- [ ] **Docker**: Dockerfile and docker-compose for deployment
- [ ] **Tests**: Additional test coverage
- [ ] **Documentation**: Improvements and completions
- [ ] **Performance**: Processing speed optimizations
- [ ] **Mobile API**: Endpoints optimized for mobile apps

### 4. Development Guidelines

#### Code Style

- Python 3.12+ type hints
- Google-style docstrings
- Follow PEP 8
- Max line length: 100 characters
- Use `|` for union types

#### Architecture

Follow the layer architecture:
- **API Layer**: `app/api/` - HTTP handlers
- **Service Layer**: `app/services/` - Business logic
- **Repository Layer**: `app/repositories/` - Data access
- **Core**: `app/core/` - Config, exceptions, logging

#### Testing

- Minimum 70% test coverage
- Unit tests for services and repositories
- Integration tests for endpoints
- Use fixtures for test data

#### Documentation

- Update README for new features
- Add/update docs/ if needed
- Docstrings for public functions
- Comments for complex logic

### 5. Contribution Terms

By contributing, you agree that:

1. **License**: Your contributions will be licensed under MIT License
2. **Originality**: You have the rights to contribute the code
3. **Non-Competitive**: Not for directly competing with the original project
4. **Educational Focus**: Aligned with learning and research goals
5. **Respect**: Respectful to other contributors and users

### 6. Review Process

- PRs will be reviewed by the maintainer
- Feedback will be provided within 1-7 days
- Changes may be requested
- Approval required before merge
- Squash merge to maintain clean history

### 7. Recognition

Contributors will be acknowledged in:
- `CONTRIBUTORS.md` file
- Release notes
- About section in documentation

### 8. Getting Help

If you need assistance:

- Read [docs/](docs/) for complete documentation
- Open a discussion for questions
- Create an issue for bug reports
- Contact maintainer for important matters

### 9. Code of Conduct

**Not Acceptable**:
- Harassment or disrespectful behavior
- Spam or excessive self-promotion
- Proprietary code without clear license
- Malicious contributions

**Encouraged**:
- Respect and collaboration
- Constructive feedback
- Inclusive and welcoming behavior
- Focus on education and learning

### 10. For Researchers & Students

We strongly support academic and educational use:

**For Researchers**:
- Explain your research topic
- Share papers/publications that use RogaScan
- Consider contributing improvements back

**For Students**:
- Suitable for thesis, dissertation, or coursework
- Learn FastAPI, OCR, and clean architecture
- Build portfolio with open-source contributions
- Mention on your CV/portfolio

**For Lecturers**:
- Use for teaching materials
- Contribute course improvements
- Student projects can be merged

---

## Contact

- **Maintainer**: amubhya
- **Organization**: RogaTekno

## License

All contributions are licensed under [MIT License](LICENSE) - see LICENSE file for details.

---

**Thank you for contributing to RogaScan!**

Together we make OCR technology accessible for everyone.
