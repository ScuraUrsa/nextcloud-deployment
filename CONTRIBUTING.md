# Contributing to Nextcloud Self-Hosted Deployment

## Development Setup

```bash
# Clone the repository
git clone https://github.com/ScuraUrsa/nextcloud-deployment.git
cd nextcloud-deployment

# Python test dependencies
python3 -m venv venv
source venv/bin/activate
pip install -r tests/requirements-test.txt

# Ansible linting tools
pip install ansible-lint yamllint

# Pre-commit hooks (optional)
pip install pre-commit
pre-commit install
```

## Code Quality Standards

### Python
- All code must pass `ruff`, `mypy --strict`, and `bandit` with zero errors
- Type hints required on all function signatures
- Docstrings required on all public functions
- Tests must be self-contained and idempotent

### Ansible
- All playbooks must pass `ansible-playbook --syntax-check`
- All files must pass `ansible-lint` with zero errors
- All YAML must pass `yamllint`
- All shell commands must use `changed_when` and `failed_when` explicitly
- Roles must be idempotent (running twice produces no changes)

### Git
- Branch naming: `feature/<description>`, `fix/<description>`, `docs/<description>`
- Commit messages: descriptive, present tense
- PRs require passing CI before merge

## Testing

```bash
# Smoke tests (critical path only)
pytest -m smoke

# All tests except slow and external
pytest -m "not slow and not external"

# Identity tests (SSO flows)
pytest -m identity

# Tier tests (feature gating)
pytest -m tiers

# Billing tests (subscription lifecycle)
pytest -m billing

# Full suite (requires deployed instance)
NEXTCLOUD_URL=https://your-instance.com pytest
```

## Architecture Decisions

All major architectural decisions are documented as ADRs in `NEXTCLOUD_DEPLOYMENT_REPORT.md`. Before proposing a change that affects architecture, read the relevant ADR first.

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
