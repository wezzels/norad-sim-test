# Makefile for local development

.PHONY: test test-unit test-integration coverage lint clean install

# Default target
all: install

# Install dependencies
install:
	pip install -e .
	pip install pytest pytest-cov pytest-html flake8 black isort mypy

# Run all tests
test:
	python run_tests.py --verbose

# Run unit tests only
test-unit:
	python run_tests.py --unit --verbose

# Run integration tests only
test-integration:
	python run_tests.py --integration --verbose

# Run with coverage report
coverage:
	python run_tests.py --coverage --verbose
	open htmlcov/index.html || xdg-open htmlcov/index.html

# Run linting
lint:
	flake8 simulator/ tests/ --max-line-length=100 --exclude=venv,__pycache__
	black --check simulator/ tests/ --line-length=100
	isort --check-only --diff simulator/ tests/

# Run type checking
typecheck:
	mypy simulator/ --ignore-missing-imports

# Run security scan
security:
	bandit -r simulator/
	safety check

# Clean generated files
clean:
	rm -rf __pycache__
	rm -rf .pytest_cache
	rm -rf htmlcov
	rm -rf .coverage
	rm -rf coverage.xml
	rm -rf test-results.xml
	rm -rf report.html
	rm -rf bandit-report.json
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Run all checks (pre-commit)
check: lint typecheck test
	@echo "All checks passed!"

# Format code
format:
	black simulator/ tests/ --line-length=100
	isort simulator/ tests/

# Generate requirements.txt (if needed)
requirements:
	pip freeze > requirements.txt

# Run specific test file
test-file:
	@echo "Usage: make test-file FILE=test_ballistics.py"
	@python run_tests.py --file $(FILE) --verbose