# Contributing to AetherOS Desktop

## Code of Conduct
This project follows a Code of Conduct. By participating, you agree to maintain a respectful and inclusive environment.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/YOUR-USERNAME/aetheros.git`
3. Set up development environment: See [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)
4. Create a feature branch: `git checkout -b feature/my-feature`

## Development Process

### 1. Find or Create an Issue
- Check existing issues for something to work on
- Create a new issue describing what you want to do
- Wait for maintainer feedback before starting significant work

### 2. Make Changes
- Follow existing code style and conventions
- Write tests for new functionality
- Update documentation as needed
- Ensure all existing tests pass

### 3. Commit Guidelines
```
type(scope): brief description

- Use conventional commits: feat:, fix:, docs:, refactor:, test:, chore:
- Keep commits focused on single changes
- Write clear commit messages
```

### 4. Submit a Pull Request
1. Push your branch: `git push origin feature/my-feature`
2. Open a PR against the `main` branch
3. Fill out the PR template
4. Ensure CI checks pass

## Pull Request Checklist
- [ ] Code follows project style (lint passes)
- [ ] TypeScript strict mode passes
- [ ] Tests pass and coverage is maintained
- [ ] New code includes tests
- [ ] Documentation updated (README, API docs, etc.)
- [ ] CHANGELOG.md updated with change description
- [ ] i18n strings added for new UI text
- [ ] Accessibility considered (ARIA labels, keyboard nav)
- [ ] No new secrets or credentials introduced

## Code Style
- TypeScript strict mode enabled
- ESLint + Prettier for formatting
- Components follow existing patterns (shadcn/ui + Tailwind v4)
- Nanostores for state management
- No classes; prefer functions and hooks
- Descriptive variable names; avoid abbreviations

## Testing Requirements
- Unit tests for new stores and utilities
- Component tests for new UI components
- Electron module tests for main process changes

## Security Requirements
All code is reviewed for:
- Path traversal vulnerabilities
- IPC channel misuse
- Credential exposure
- XSS and injection attacks
- Insecure deserialization

## Questions?
- Open a discussion on GitHub
- Join our Discord community
- Ask in the PR comments
