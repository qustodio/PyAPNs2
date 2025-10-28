# Tests

This directory contains the test suite for the PyAPNs2 library.

## Test Structure

- `test_client.py` - Tests for core APNs client functionality
- `test_credentials.py` - Tests for different credential types and authentication
- `test_payload.py` - Tests for payload creation and validation
- `test_errors.py` - Tests for error handling and exception classes

## Running Tests

### Run all tests

```bash
poetry run pytest
```

### Run tests with coverage

```bash
poetry run pytest --cov=apns2 --cov-report=html
```

### Run specific tests

```bash
# Client tests only
poetry run pytest test/test_client.py

# Single test function
poetry run pytest test/test_client.py::test_send_notification_success

# Tests by marker
poetry run pytest -m "not slow"
```

### Async tests

Async tests run automatically with pytest-asyncio. No additional configuration required.

## Coverage

The test suite maintains high code coverage. Run the following to see current coverage:

```bash
# Generate HTML coverage report
poetry run coverage html

# View coverage in terminal
poetry run coverage report --show-missing
```

The HTML report is generated in `htmlcov/index.html`.

## Test Types

### Unit Tests

- Test individual functions and classes
- Use mocks for external dependencies
- Fast execution

### Integration Tests

- Test component interactions
- Marked with `@pytest.mark.integration`

### Async Tests

- Test asynchronous functionality directly
- Use `@pytest.mark.asyncio` decorator

## Best Practices

1. **Naming**: Tests follow the pattern `test_<what>_<condition>`
2. **Fixtures**: Reuse fixtures for common setup
3. **Mocking**: Mock external dependencies (httpx, ssl, etc.)
4. **Assertions**: Use descriptive assertions with clear failure messages
5. **Coverage**: Maintain coverage above 90%
6. **Typing**: All test functions have proper type annotations

## Configuration

The test configuration is defined in `pyproject.toml`:

- **pytest**: Configured with strict options and coverage reporting
- **coverage**: Excludes test files and includes proper exclusion patterns
- **asyncio**: Auto-mode enabled for seamless async test execution

## Adding New Tests

1. Identify the functionality to test
2. Add the test to the appropriate file
3. Use existing fixtures when possible
4. Mock external dependencies
5. Ensure coverage doesn't decrease
6. Follow the established patterns

### Example Test Template

```python
def test_new_functionality() -> None:
    """Test that new functionality works correctly."""
    # Arrange
    setup_data = create_test_data()

    # Act
    result = function_under_test(setup_data)

    # Assert
    assert result == expected_result
```

### Async Test Template

```python
@pytest.mark.asyncio
async def test_async_functionality() -> None:
    """Test async functionality."""
    # Arrange
    mock_dependency = AsyncMock()

    # Act
    result = await async_function_under_test(mock_dependency)

    # Assert
    assert result == expected_result
    mock_dependency.assert_called_once()
```

