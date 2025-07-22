# Only for development
format:
	uv run ruff format -v .

lint:
	uv run ruff check --select I --fix .	

unit-test:
	uv run pytest 

pre-commit:
	@echo "🚀 Running pre-commit checks..."
	@echo "📝 Step 1: Formatting code..."
	@uv run ruff format -v . || (echo "❌ Formatting failed!" && exit 1)
	@echo "✅ Formatting complete!"
	@echo ""
	@echo "🔍 Step 2: Linting code..."
	@uv run ruff check --select I --fix . || (echo "❌ Linting failed!" && exit 1)
	@echo "✅ Linting complete!"
	@echo ""
	@echo "🧪 Step 3: Running unit tests..."
	@uv run pytest || (echo "❌ Tests failed!" && exit 1)
	@echo "✅ All pre-commit checks passed! 🎉"

# Quick version without verbose output
pre-commit-quick:
	@echo "🚀 Running quick pre-commit checks..."
	@uv run ruff format . && uv run ruff check --select I --fix . && uv run pytest --tb=short
	@echo "✅ All checks passed! 🎉"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache/ .coverage htmlcov/ coverage.xml 2>/dev/null || true

.PHONY: format lint unit-test pre-commit pre-commit-quick clean
