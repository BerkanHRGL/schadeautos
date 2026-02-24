# Contributing to Car Damage Finder

Thank you for your interest in contributing to Car Damage Finder! This document provides guidelines and information for contributors.

## 🤝 How to Contribute

### Reporting Bugs

1. **Check existing issues** first to avoid duplicates
2. **Use the bug report template** when creating new issues
3. **Include detailed information**:
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Docker version, etc.)
   - Screenshots if applicable
   - Log output if relevant

### Suggesting Features

1. **Check the roadmap** and existing feature requests
2. **Create a detailed feature request** including:
   - Use case and motivation
   - Proposed solution
   - Alternative solutions considered
   - Implementation complexity estimate

### Code Contributions

1. **Fork the repository**
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following the coding standards
4. **Test thoroughly** (see Testing section)
5. **Commit with descriptive messages** following conventional commits
6. **Push to your fork** and create a pull request

## 🏗️ Development Setup

### Prerequisites
- Docker and Docker Compose
- Python 3.11+ (for local backend development)
- Node.js 18+ (for local frontend development)
- Git

### Local Development

#### Backend Development
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies

# Run with hot reloading
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Development
```bash
cd frontend
npm install
npm start  # Starts on http://localhost:3000
```

#### Full Stack with Docker
```bash
docker-compose up -d
```

## 📋 Coding Standards

### Backend (Python)

#### Code Style
- Follow **PEP 8** standards
- Use **Black** for code formatting
- Use **isort** for import sorting
- Use **mypy** for type checking

```bash
# Format code
black backend/
isort backend/

# Type checking
mypy backend/

# Linting
flake8 backend/
```

#### Best Practices
- Use type hints for all functions
- Write docstrings for public functions
- Use Pydantic models for data validation
- Handle exceptions gracefully
- Log important events and errors
- Use dependency injection for services

#### Example Code Structure
```python
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

def get_cars(
    db: Session = Depends(get_db),
    skip: int = 0,
    limit: int = 100
) -> List[Car]:
    """
    Retrieve cars with pagination.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of car objects
    """
    return db.query(Car).offset(skip).limit(limit).all()
```

### Frontend (React/TypeScript)

#### Code Style
- Use **Prettier** for code formatting
- Use **ESLint** for linting
- Use **TypeScript** for type safety

```bash
# Format and lint
npm run format
npm run lint
npm run type-check
```

#### Best Practices
- Use functional components with hooks
- Implement proper error boundaries
- Use React Query for data fetching
- Implement loading and error states
- Use TypeScript interfaces for props
- Follow component composition patterns

#### Example Component Structure
```tsx
interface CarCardProps {
  car: Car;
  onSelect?: (car: Car) => void;
}

export const CarCard: React.FC<CarCardProps> = ({ car, onSelect }) => {
  const handleClick = useCallback(() => {
    onSelect?.(car);
  }, [car, onSelect]);

  return (
    <div className="car-card" onClick={handleClick}>
      {/* Component content */}
    </div>
  );
};
```

### Database

#### Migrations
- Use Alembic for database migrations
- Create descriptive migration names
- Test migrations both up and down
- Review migrations before committing

```bash
# Create migration
alembic revision --autogenerate -m "Add car damage keywords table"

# Apply migration
alembic upgrade head

# Downgrade migration
alembic downgrade -1
```

### Docker

#### Best Practices
- Use multi-stage builds for production images
- Minimize image size
- Use specific version tags
- Include health checks
- Follow security best practices

## 🧪 Testing

### Backend Testing

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=backend --cov-report=html

# Run specific test file
pytest tests/test_scrapers.py

# Run specific test
pytest tests/test_scrapers.py::test_marktplaats_scraper
```

#### Test Structure
```python
import pytest
from fastapi.testclient import TestClient
from backend.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_get_cars(client):
    response = client.get("/api/cars")
    assert response.status_code == 200
    assert "cars" in response.json()
```

### Frontend Testing

```bash
# Run tests
npm test

# Run with coverage
npm test -- --coverage

# Run specific test
npm test CarCard.test.tsx
```

#### Test Structure
```tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { CarCard } from '../CarCard';

describe('CarCard', () => {
  const mockCar = {
    id: 1,
    make: 'BMW',
    model: '320i',
    price: 15000,
  };

  test('renders car information', () => {
    render(<CarCard car={mockCar} />);
    expect(screen.getByText('BMW 320i')).toBeInTheDocument();
    expect(screen.getByText('€15,000')).toBeInTheDocument();
  });
});
```

### Integration Testing

```bash
# Test with Docker Compose
docker-compose -f docker-compose.test.yml up --abort-on-container-exit
```

## 📝 Commit Convention

We follow [Conventional Commits](https://conventionalcommits.org/) specification:

### Format
```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

### Types
- **feat**: New feature
- **fix**: Bug fix
- **docs**: Documentation changes
- **style**: Code style changes (formatting, etc.)
- **refactor**: Code refactoring
- **test**: Adding or updating tests
- **chore**: Build process or auxiliary tool changes
- **perf**: Performance improvements

### Examples
```bash
feat(scraper): add support for autoscout24.nl

fix(api): handle missing car images gracefully

docs: update installation instructions

style(frontend): format code with prettier

refactor(database): optimize car query performance

test(scraper): add unit tests for damage keyword detection

chore(docker): update base image to python 3.11
```

## 🔄 Pull Request Process

### Before Submitting

1. **Update your branch** with the latest main:
   ```bash
   git checkout main
   git pull origin main
   git checkout your-feature-branch
   git rebase main
   ```

2. **Run all tests** and ensure they pass
3. **Update documentation** if needed
4. **Test your changes** thoroughly

### PR Template

When creating a pull request, please include:

- **Clear title** describing the change
- **Detailed description** of what was changed and why
- **Testing performed** (manual and automated)
- **Screenshots** for UI changes
- **Breaking changes** (if any)
- **Related issues** (closes #123)

### Review Process

1. **Automated checks** must pass (CI/CD, tests, linting)
2. **Code review** by at least one maintainer
3. **Manual testing** if needed
4. **Documentation review** for user-facing changes
5. **Merge** by maintainer after approval

## 🏗️ Architecture Guidelines

### Backend Architecture

```
backend/
├── api/
│   ├── routes/          # FastAPI route handlers
│   └── schemas.py       # Pydantic models
├── database/
│   ├── models.py        # SQLAlchemy models
│   └── database.py      # Database configuration
├── scrapers/
│   ├── base_scraper.py  # Abstract scraper base
│   └── site_scrapers.py # Site-specific scrapers
├── services/
│   ├── scraping_service.py     # Scraping orchestration
│   ├── notification_service.py # Email notifications
│   └── filter_service.py       # Damage detection
└── main.py              # FastAPI application
```

### Frontend Architecture

```
frontend/src/
├── components/          # Reusable UI components
├── pages/              # Page-level components
├── services/           # API calls and utilities
├── hooks/              # Custom React hooks
├── types/              # TypeScript type definitions
└── utils/              # Helper functions
```

### Adding New Features

#### New Scraper
1. Extend `BaseScraper` class
2. Implement required abstract methods
3. Add to scraping service
4. Write unit tests
5. Update documentation

#### New API Endpoint
1. Define Pydantic schemas
2. Create route handler
3. Add database operations if needed
4. Write tests
5. Update API documentation

#### New UI Component
1. Create component with TypeScript
2. Add to Storybook (if applicable)
3. Write unit tests
4. Update design system documentation

## 🚀 Release Process

### Version Numbering
We follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Checklist
1. Update version numbers
2. Update CHANGELOG.md
3. Run full test suite
4. Build and test Docker images
5. Create release tag
6. Deploy to staging
7. Perform smoke tests
8. Deploy to production
9. Create GitHub release

## 🆘 Getting Help

### Resources
- **Documentation**: See README.md and wiki
- **API Docs**: http://localhost:8000/docs (when running)
- **Issue Tracker**: GitHub Issues
- **Discussions**: GitHub Discussions

### Contact
- Create an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

## 📜 Code of Conduct

### Our Standards
- **Be respectful** and inclusive
- **Be constructive** in feedback
- **Be patient** with newcomers
- **Be collaborative** and helpful
- **Focus on the code**, not the person

### Unacceptable Behavior
- Harassment or discrimination
- Trolling or inflammatory comments
- Personal attacks
- Publishing private information
- Spam or off-topic content

### Enforcement
Violations may result in:
1. Warning
2. Temporary ban
3. Permanent ban

Report issues to project maintainers.

## 🎯 Roadmap

### Planned Features
- [ ] Additional Dutch car websites
- [ ] Advanced filtering (transmission, fuel type)
- [ ] Price history tracking
- [ ] Mobile app
- [ ] API for third-party integrations
- [ ] Machine learning for damage classification
- [ ] Integration with Dutch RDW database

### Contribution Opportunities
- **Beginner friendly**: Documentation improvements, UI enhancements
- **Intermediate**: New scraper implementations, API endpoints
- **Advanced**: Performance optimization, ML features, mobile app

Thank you for contributing to Car Damage Finder! 🚗✨