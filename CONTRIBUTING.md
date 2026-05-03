# Contributing to RepoSense 🤝

Thank you for your interest in contributing to RepoSense! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)

## Code of Conduct

By participating in this project, you agree to:

- Be respectful and inclusive
- Welcome newcomers and help them learn
- Focus on what is best for the community
- Show empathy towards other community members

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/reposense.git
   cd reposense
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL_OWNER/reposense.git
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Setup

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with IBM_BOB_API_KEY=mock for development
uvicorn main:app --reload
```

### Frontend Setup

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

### Running Tests

```bash
# Backend tests
cd backend
pytest tests/ -v

# Frontend tests
cd frontend
npm test
```

## How to Contribute

### Reporting Bugs

Before creating a bug report:
- Check existing issues to avoid duplicates
- Collect information about the bug
- Test with the latest version

Include in your bug report:
- Clear, descriptive title
- Steps to reproduce
- Expected vs actual behavior
- Screenshots if applicable
- Environment details (OS, Python/Node version)

### Suggesting Features

Feature requests are welcome! Please:
- Use a clear, descriptive title
- Provide detailed description of the feature
- Explain why this feature would be useful
- Include examples or mockups if possible

### Code Contributions

We welcome code contributions! Here are some areas:

**Backend:**
- New IBM Bob mode integrations
- Additional GitHub API features
- Performance optimizations
- Better error handling
- More comprehensive tests

**Frontend:**
- UI/UX improvements
- New visualization components
- Accessibility enhancements
- Mobile responsiveness
- Export format options

**Documentation:**
- Tutorial improvements
- API documentation
- Code examples
- Translation to other languages

## Coding Standards

### Python (Backend)

Follow PEP 8 style guide:

```bash
# Format code
black .

# Check style
flake8 .

# Type checking
mypy .
```

**Key conventions:**
- Use type hints for function parameters and returns
- Write docstrings for all public functions/classes
- Keep functions focused and small
- Use async/await for I/O operations
- Handle errors explicitly

**Example:**
```python
async def fetch_repo_context(github_url: str) -> dict:
    """
    Fetch repository context from GitHub API.
    
    Args:
        github_url: Full GitHub repository URL
        
    Returns:
        Dictionary containing repository metadata and files
        
    Raises:
        GitHubError: If repository cannot be accessed
    """
    # Implementation
```

### JavaScript/React (Frontend)

Follow Airbnb JavaScript Style Guide:

```bash
# Lint code
npm run lint

# Format code
npm run format
```

**Key conventions:**
- Use functional components with hooks
- Prop types or TypeScript for type safety
- Descriptive component and variable names
- Extract reusable logic into custom hooks
- Keep components small and focused

**Example:**
```jsx
/**
 * Repository input component
 * @param {Function} onAnalyze - Callback when analysis is triggered
 */
function RepoInput({ onAnalyze }) {
  const [url, setUrl] = useState('');
  
  const handleSubmit = (e) => {
    e.preventDefault();
    if (isValidGitHubUrl(url)) {
      onAnalyze(url);
    }
  };
  
  return (
    // JSX
  );
}
```

### Commit Messages

Follow conventional commits format:

```
type(scope): subject

body (optional)

footer (optional)
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(backend): add caching for GitHub API responses

fix(frontend): resolve loading state not clearing on error

docs(readme): update installation instructions

test(backend): add tests for bob_client error handling
```

## Testing

### Backend Tests

```bash
cd backend
pytest tests/ -v --cov=. --cov-report=html
```

Write tests for:
- All new functions and endpoints
- Edge cases and error conditions
- Integration between components

**Example:**
```python
@pytest.mark.asyncio
async def test_analyze_repository_success():
    """Test successful repository analysis"""
    response = await client.post(
        "/api/v1/analyze",
        json={"github_url": "https://github.com/test/repo"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "project_name" in data
```

### Frontend Tests

```bash
cd frontend
npm test
```

Write tests for:
- Component rendering
- User interactions
- State management
- API integration

**Example:**
```jsx
import { render, screen, fireEvent } from '@testing-library/react';
import RepoInput from './RepoInput';

test('calls onAnalyze with valid URL', () => {
  const mockAnalyze = jest.fn();
  render(<RepoInput onAnalyze={mockAnalyze} />);
  
  const input = screen.getByPlaceholderText(/github url/i);
  const button = screen.getByText(/analyze/i);
  
  fireEvent.change(input, { 
    target: { value: 'https://github.com/test/repo' } 
  });
  fireEvent.click(button);
  
  expect(mockAnalyze).toHaveBeenCalledWith('https://github.com/test/repo');
});
```

## Pull Request Process

1. **Update your branch** with latest upstream:
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```

2. **Run tests** and ensure they pass:
   ```bash
   # Backend
   cd backend && pytest tests/ -v
   
   # Frontend
   cd frontend && npm test
   ```

3. **Update documentation** if needed:
   - README.md for user-facing changes
   - Code comments for implementation details
   - API docs for endpoint changes

4. **Create pull request**:
   - Use a clear, descriptive title
   - Reference related issues
   - Describe what changed and why
   - Include screenshots for UI changes
   - List any breaking changes

5. **PR template**:
   ```markdown
   ## Description
   Brief description of changes
   
   ## Type of Change
   - [ ] Bug fix
   - [ ] New feature
   - [ ] Breaking change
   - [ ] Documentation update
   
   ## Testing
   - [ ] Tests pass locally
   - [ ] Added new tests
   - [ ] Manual testing completed
   
   ## Screenshots (if applicable)
   
   ## Related Issues
   Closes #123
   ```

6. **Code review**:
   - Address reviewer feedback
   - Keep discussions focused and professional
   - Update PR based on suggestions

7. **Merge**:
   - Squash commits if requested
   - Ensure CI passes
   - Wait for maintainer approval

## Issue Guidelines

### Creating Issues

Use issue templates when available:

**Bug Report Template:**
```markdown
**Describe the bug**
Clear description of the bug

**To Reproduce**
1. Go to '...'
2. Click on '...'
3. See error

**Expected behavior**
What should happen

**Screenshots**
If applicable

**Environment:**
- OS: [e.g., Windows 10]
- Python version: [e.g., 3.11]
- Node version: [e.g., 18.0]
```

**Feature Request Template:**
```markdown
**Is your feature request related to a problem?**
Description of the problem

**Describe the solution you'd like**
Clear description of desired feature

**Describe alternatives you've considered**
Other solutions considered

**Additional context**
Any other context or screenshots
```

### Working on Issues

1. **Comment** on the issue to claim it
2. **Ask questions** if anything is unclear
3. **Update** the issue with progress
4. **Link** your PR to the issue

## Development Workflow

### Typical Workflow

```bash
# 1. Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# 2. Create feature branch
git checkout -b feature/my-feature

# 3. Make changes and commit
git add .
git commit -m "feat: add my feature"

# 4. Push to your fork
git push origin feature/my-feature

# 5. Create pull request on GitHub
```

### Branch Naming

- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation
- `refactor/` - Code refactoring
- `test/` - Test additions/updates

Examples:
- `feature/add-pdf-export`
- `fix/loading-state-bug`
- `docs/update-api-guide`

## Questions?

- **Documentation**: Check [README.md](./README.md) and [QUICKSTART.md](./QUICKSTART.md)
- **Discussions**: Use GitHub Discussions for questions
- **Issues**: Create an issue for bugs or feature requests
- **Email**: support@reposense.dev

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Mentioned in release notes
- Credited in the project

Thank you for contributing to RepoSense! 🎉

---

Built with ❤️ for IBM Bob Hackathon 2024