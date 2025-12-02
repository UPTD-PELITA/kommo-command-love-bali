#!/bin/bash
# =============================================================================
# Post-create script for kommo-command dev container
# =============================================================================

set -e

echo "🚀 Setting up kommo-command development environment..."

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install package in editable mode with dev dependencies
echo "📦 Installing package with dev dependencies..."
pip install -e ".[dev]"

# Copy .env.example to .env if .env doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from template..."
    cp .devcontainer/.env.example .env
    echo "⚠️  Please edit .env with your configuration values"
else
    echo "✅ .env file already exists"
fi

# Display setup instructions
echo ""
echo "=============================================="
echo "✅ Development environment ready!"
echo "=============================================="
echo ""
echo "📋 Next steps:"
echo ""
echo "1. Configure environment variables:"
echo "   Edit .env with your Firebase and Kommo credentials"
echo ""
echo "2. Add your Google service account file:"
echo "   Place your service-account.json in the project root"
echo "   Update GOOGLE_SERVICE_ACCOUNT_FILE in .env"
echo ""
echo "3. Run the application:"
echo "   python -m kommo_command"
echo ""
echo "4. Run tests:"
echo "   pytest"
echo ""
echo "5. Code quality tools:"
echo "   black .        # Format code"
echo "   ruff check .   # Lint code"
echo "   mypy src/      # Type check"
echo ""
echo "=============================================="
