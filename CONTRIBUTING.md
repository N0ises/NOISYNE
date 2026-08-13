# Contributing to NØISYNE

Thank you for your interest in contributing to NØISYNE.

## Development Workflow

1. Fork the repository.
2. Create a feature branch.
3. Follow the project architecture.
4. Write tests for new functionality.
5. Run all tests before committing.
6. Submit a Pull Request.

---

## Coding Standards

- Python 3.12+
- Follow Ruff and Black formatting.
- Add type hints where appropriate.
- Keep functions focused on a single responsibility.

---

## Architecture Rules

- Never introduce circular dependencies.
- Runtime must remain domain-independent.
- Use dependency injection.
- Keep modules modular.
- Do not hardcode model paths.
- Avoid global mutable state.

---

## Testing

Run before every commit:

```bash
pytest
```

---

## Documentation

Update documentation when introducing:

- New modules
- Public APIs
- Architecture changes
- Configuration changes

---

## Commit Style

Examples:

```
feat: add audio embedding provider
fix: runtime cache bug
refactor: simplify loader strategy
docs: update architecture guide
test: add runtime validation tests
```

---

Thank you for helping improve NØISYNE.