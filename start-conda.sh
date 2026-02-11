#!/bin/bash
# Queryus Quick Start Script (Conda)

set -e

echo "🐍 Starting Queryus with Conda..."

# Check if conda is installed
if ! command -v conda &> /dev/null; then
    echo "❌ Conda not found. Please install Miniconda:"
    echo "   https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# Check if environment exists
if ! conda env list | grep -q "queryus"; then
    echo "📦 Creating Conda environment..."
    cd backend
    conda env create -f environment.yml
    cd ..
    echo "✅ Environment created!"
else
    echo "✅ Environment already exists"
fi

# Check PostgreSQL
echo "🔍 Checking PostgreSQL..."
if pg_isready -h localhost -p 5432 &> /dev/null; then
    echo "✅ PostgreSQL is running"
else
    echo "⚠️  PostgreSQL not running. Options:"
    echo "   1. Start with Homebrew: brew services start postgresql"
    echo "   2. Use Docker: docker run -d --name queryus-postgres -e POSTGRES_USER=queryus -e POSTGRES_PASSWORD=queryus_dev_password -e POSTGRES_DB=queryus -p 5432:5432 postgres:15"
    read -p "   Start PostgreSQL with Docker? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker run -d --name queryus-postgres \
          -e POSTGRES_USER=queryus \
          -e POSTGRES_PASSWORD=queryus_dev_password \
          -e POSTGRES_DB=queryus \
          -p 5432:5432 \
          postgres:15
        echo "✅ PostgreSQL started in Docker"
        sleep 3
    else
        echo "❌ Please start PostgreSQL manually"
        exit 1
    fi
fi

# Check Redis
echo "🔍 Checking Redis..."
if redis-cli ping &> /dev/null; then
    echo "✅ Redis is running"
else
    echo "⚠️  Redis not running. Options:"
    echo "   1. Start with Homebrew: brew services start redis"
    echo "   2. Use Docker: docker run -d --name queryus-redis -p 6379:6379 redis:7"
    read -p "   Start Redis with Docker? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker run -d --name queryus-redis -p 6379:6379 redis:7
        echo "✅ Redis started in Docker"
        sleep 2
    else
        echo "❌ Please start Redis manually"
        exit 1
    fi
fi

# Run migrations
echo "🗄️  Running database migrations..."
cd backend
eval "$(conda shell.bash hook)"
conda activate queryus
alembic upgrade head
cd ..
echo "✅ Migrations complete!"

echo ""
echo "🎉 Setup complete!"
echo ""
echo "To start the app:"
echo ""
echo "  Terminal 1 (Backend):"
echo "    cd backend"
echo "    conda activate queryus"
echo "    uvicorn app.main:app --reload --port 8000"
echo ""
echo "  Terminal 2 (Frontend):"
echo "    npm run dev"
echo ""
echo "  Browser:"
echo "    http://localhost:8080"
echo ""
