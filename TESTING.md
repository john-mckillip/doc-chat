# Testing Guide for DocChat

Complete testing documentation for achieving and maintaining 100% code coverage.

## Table of Contents
- [Overview](#overview)
- [Backend Testing](#backend-testing)
- [Frontend Testing](#frontend-testing)
- [Running Tests](#running-tests)
- [CI/CD Pipeline](#cicd-pipeline)
- [Coverage Requirements](#coverage-requirements)

## Overview

This project maintains **100% test coverage** for both backend and frontend code. All tests are run automatically in CI/CD via GitHub Actions on every push and pull request.

### Test Statistics
- **Backend**: ~70 test functions across 3 test files
- **Frontend**: ~96 test functions across 7 test files
- **Total**: ~166 comprehensive test functions
- **Coverage Target**: 100% lines, branches, functions, and statements

## Backend Testing

### Technology Stack
- **pytest** - Test framework
- **pytest-asyncio** - Async test support
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities
- **httpx** - FastAPI test client

### Test Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures and mocks
│   ├── test_app.py            # FastAPI endpoints (~20 tests)
│   ├── test_indexer.py        # Document indexing (~30 tests)
│   └── test_retriever.py      # RAG and LLM (~20 tests)
├── requirements-dev.txt       # Testing dependencies
└── pytest.ini                 # Pytest configuration
```

### Running Backend Tests

```bash
cd backend

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage report
pytest --cov=. --cov-report=html --cov-report=term-missing

# Run specific test file
pytest tests/test_indexer.py

# Run specific test
pytest tests/test_app.py::TestRESTEndpoints::test_index_documents_success

# Run with verbose output
pytest -v

# View coverage report
open htmlcov/index.html  # or your browser
```

### Backend Test Coverage

#### test_app.py - FastAPI Application Tests
- ✅ REST endpoint success/failure paths
- ✅ WebSocket connection lifecycle
- ✅ WebSocket indexing with progress callbacks
- ✅ WebSocket chat streaming
- ✅ Conversation history management
- ✅ CORS configuration
- ✅ Error handling and validation

#### test_indexer.py - Document Indexing Tests
- ✅ Initialization with/without existing index
- ✅ File hash computation (MD5)
- ✅ File type filtering (10+ extensions)
- ✅ New file indexing
- ✅ Modified file detection and re-indexing
- ✅ Unchanged file skipping
- ✅ Deleted file handling
- ✅ Empty file handling
- ✅ Text chunking with overlap
- ✅ Progress callbacks (12 message types)
- ✅ Metadata persistence
- ✅ Statistics retrieval
- ✅ Encoding error handling

#### test_retriever.py - Retrieval and LLM Tests
- ✅ Index loading (existing/missing)
- ✅ Vector similarity search
- ✅ Deleted chunk filtering
- ✅ Top-k retrieval
- ✅ Streaming response generation
- ✅ Conversation history integration
- ✅ Source metadata extraction
- ✅ Claude API integration
- ✅ JSON serialization

### Backend Mocking Strategy

All external dependencies are mocked:
- **FAISS** - In-memory mock index
- **SentenceTransformer** - Fixed random embeddings
- **Anthropic Client** - Mock streaming responses
- **File System** - Temporary directories via pytest fixtures

## Frontend Testing

### Technology Stack
- **Vitest** - Fast unit test framework
- **Testing Library** - React component testing
- **jsdom** - DOM simulation
- **@testing-library/user-event** - User interaction simulation
- **@testing-library/jest-dom** - Custom matchers

### Test Structure

```
frontend/
├── src/
│   ├── __tests__/
│   │   └── App.test.tsx
│   ├── components/__tests__/
│   │   ├── Chat.test.tsx
│   │   ├── IndexStatus.test.tsx
│   │   ├── MessageList.test.tsx
│   │   └── SourcePanel.test.tsx
│   ├── hooks/__tests__/
│   │   ├── useWebSocket.test.ts
│   │   └── useIndexWebSocket.test.ts
│   └── test/
│       ├── setup.ts              # Global test setup
│       └── mocks/
│           └── websocket.ts      # WebSocket mock
├── vitest.config.ts              # Vitest configuration
└── package.json                  # Test scripts
```

### Running Frontend Tests

```bash
cd frontend

# Install dependencies
npm install

# Run tests (watch mode)
npm test

# Run tests once
npm run test:run

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui

# View coverage report
open coverage/index.html  # or your browser
```

### Frontend Test Coverage

#### App.test.tsx - Main Application Tests
- ✅ Component mounting and rendering
- ✅ Stats fetching on mount
- ✅ Conditional rendering (IndexStatus vs Chat)
- ✅ Error handling for API failures
- ✅ onIndexComplete callback

#### Chat.test.tsx - Chat Component Tests
- ✅ Message input and submission
- ✅ Form validation (empty messages)
- ✅ Disabled states (not connected, streaming)
- ✅ Re-index modal open/close
- ✅ Re-index form submission
- ✅ WebSocket connection status
- ✅ Modal auto-close after indexing
- ✅ Source panel conditional rendering
- ✅ Last assistant message extraction

#### IndexStatus.test.tsx - Indexing UI Tests
- ✅ Initial render states
- ✅ Form submission validation
- ✅ Error state display
- ✅ Progress phase rendering
- ✅ Stats display after completion
- ✅ onIndexComplete callback
- ✅ Supported file types display

#### MessageList.test.tsx - Message Display Tests
- ✅ Empty state rendering
- ✅ User vs assistant message styling
- ✅ Auto-scroll on new messages
- ✅ Streaming indicator
- ✅ Message formatting (whitespace-pre-wrap)

#### SourcePanel.test.tsx - Source Citation Tests
- ✅ Source panel rendering
- ✅ Source numbering
- ✅ File path truncation
- ✅ Full path in title attribute
- ✅ Single/multiple source handling

#### useWebSocket.test.ts - Chat WebSocket Hook Tests
- ✅ Connection establishment
- ✅ Connection status tracking
- ✅ Message sending
- ✅ Message type handling (sources, content, done)
- ✅ Message accumulation during streaming
- ✅ Streaming state management
- ✅ Error handling
- ✅ Cleanup on unmount

#### useIndexWebSocket.test.ts - Indexing WebSocket Hook Tests
- ✅ Connection on startIndexing
- ✅ All 12+ message type handlers
- ✅ Progress state updates
- ✅ Stats state on completion
- ✅ Error handling
- ✅ Cleanup on unmount
- ✅ Prevent multiple simultaneous indexing

### Frontend Mocking Strategy

- **WebSocket** - Full mock implementation with message simulation
- **fetch API** - Mocked for stats endpoint
- **scrollIntoView** - Mocked to prevent DOM errors
- **console methods** - Mocked to reduce test noise

## Running Tests

### Quick Start

```bash
# Backend tests
cd backend && pytest

# Frontend tests
cd frontend && npm test

# Both with coverage
cd backend && pytest --cov
cd frontend && npm run test:coverage
```

### Full Test Suite

```bash
# From project root

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt -r requirements-dev.txt
pytest --cov=. --cov-report=html

# Frontend
cd ../frontend
npm install
npm run test:coverage
```

## CI/CD Pipeline

### GitHub Actions Workflow

File: `.github/workflows/ci.yml`

#### Features
- **Matrix Testing**
  - Python: 3.10, 3.11, 3.12
  - Node.js: 18, 20, 21

- **Backend Job**
  - Install dependencies
  - Run pytest with 100% coverage requirement
  - Upload coverage to Codecov
  - Generate HTML coverage report

- **Frontend Job**
  - Install dependencies
  - Run type checking
  - Run ESLint
  - Run vitest with 100% coverage requirement
  - Upload coverage to Codecov
  - Generate HTML coverage report

- **Build Job**
  - Runs after tests pass
  - Builds frontend production bundle
  - Uploads build artifacts

- **Coverage Report Job**
  - Summarizes coverage from all jobs
  - Displays in GitHub Actions summary

### Triggers
- Push to `main` or `develop` branches
- Pull requests to `main` or `develop` branches

### Badges

Add to your README.md:

```markdown
![Backend Tests](https://github.com/john-mckillip/doc-chat/workflows/CI%2FCD%20Pipeline/badge.svg)
![Frontend Tests](https://github.com/john-mckillip/doc-chat/workflows/CI%2FCD%20Pipeline/badge.svg)
![Coverage](https://codecov.io/gh/john-mckillip/doc-chat/branch/main/graph/badge.svg)
```

## Coverage Requirements

### Thresholds

Both backend and frontend enforce **100% coverage**:

**Backend (pytest.ini):**
```ini
--cov-fail-under=100
```

**Frontend (vitest.config.ts):**
```typescript
coverage: {
  lines: 100,
  functions: 100,
  branches: 100,
  statements: 100
}
```

### What's Covered

✅ **100% Line Coverage** - Every line of code is executed
✅ **100% Branch Coverage** - Every if/else path is tested
✅ **100% Function Coverage** - Every function is called
✅ **100% Statement Coverage** - Every statement is executed

### What's Excluded

Files excluded from coverage requirements:
- Test files themselves (`**/*.test.*`, `**/__tests__/**`)
- Test utilities (`src/test/**`)
- Type definitions (`src/types/**`, `src/vite-env.d.ts`)
- Entry point (`src/main.tsx`)
- Configuration files

## Maintaining Coverage

### Adding New Code

When adding new features:

1. **Write tests first** (TDD approach)
2. **Run coverage locally** before committing
3. **Ensure 100% coverage** for new code
4. **Update this guide** if new test patterns emerge

### Common Testing Patterns

**Testing WebSocket interactions:**
```typescript
const mockWs = new MockWebSocket('ws://localhost:8000/ws/chat')
mockWs.simulateMessage({ type: 'content', data: 'Hello' })
```

**Testing async operations:**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

**Testing React components:**
```typescript
const { getByText } = render(<MyComponent />)
await waitFor(() => {
  expect(getByText('Expected Text')).toBeInTheDocument()
})
```

**Mocking dependencies:**
```python
def test_with_mock(mocker):
    mock_func = mocker.patch('module.function')
    mock_func.return_value = 'mocked'
```

## Troubleshooting

### Backend Tests Failing

```bash
# Clear pytest cache
rm -rf .pytest_cache __pycache__ **/__pycache__

# Reinstall dependencies
pip install --force-reinstall -r requirements-dev.txt

# Run with verbose output
pytest -vv
```

### Frontend Tests Failing

```bash
# Clear cache
rm -rf node_modules/.vite

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install

# Run with verbose output
npm test -- --reporter=verbose
```

### Coverage Not 100%

```bash
# Backend - See uncovered lines
pytest --cov=. --cov-report=term-missing

# Frontend - See uncovered lines
npm run test:coverage
```

## Best Practices

1. **Write tests alongside code** - Don't wait until the end
2. **Test behavior, not implementation** - Focus on what, not how
3. **Use descriptive test names** - Should read like documentation
4. **Keep tests isolated** - No shared state between tests
5. **Mock external dependencies** - Tests should be fast and deterministic
6. **Test edge cases** - Empty inputs, errors, boundary conditions
7. **Maintain test readability** - Tests are documentation

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Vitest Documentation](https://vitest.dev/)
- [Testing Library](https://testing-library.com/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [GitHub Actions](https://docs.github.com/en/actions)

---

**Questions or Issues?**

Open an issue at: https://github.com/john-mckillip/doc-chat/issues
