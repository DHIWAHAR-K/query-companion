# 🐍 Queryus with Conda - Setup Guide

Running Queryus with Conda instead of Docker.

---

## 📋 Prerequisites

- **Conda/Miniconda** installed ([install here](https://docs.conda.io/en/latest/miniconda.html))
- **PostgreSQL** running locally (port 5432)
- **Redis** running locally (port 6379)
- **Node.js 18+** for frontend

---

## 🚀 Quick Setup

### 1. Create Conda Environment

```bash
cd backend
conda env create -f environment.yml
conda activate queryus
```

This creates a `queryus` environment with Python 3.11 and all dependencies including Google Gemini SDK.

### 2. Setup PostgreSQL Database

**Option A: Use existing PostgreSQL**
```bash
# Create database and user
psql postgres
CREATE DATABASE queryus;
CREATE USER queryus WITH PASSWORD 'queryus_dev_password';
GRANT ALL PRIVILEGES ON DATABASE queryus TO queryus;
\q
```

**Option B: Install PostgreSQL via Homebrew (macOS)**
```bash
brew install postgresql@15
brew services start postgresql@15
createdb queryus
```

**Option C: Keep PostgreSQL in Docker**
```bash
docker run -d \
  --name queryus-postgres \
  -e POSTGRES_USER=queryus \
  -e POSTGRES_PASSWORD=queryus_dev_password \
  -e POSTGRES_DB=queryus \
  -p 5432:5432 \
  postgres:15
```

### 3. Setup Redis

**Option A: Install Redis via Homebrew (macOS)**
```bash
brew install redis
brew services start redis
```

**Option B: Keep Redis in Docker**
```bash
docker run -d \
  --name queryus-redis \
  -p 6379:6379 \
  redis:7
```

### 4. Configure Environment

Your `.env` is already configured for local services:
```bash
# backend/.env already has:
DATABASE_URL=postgresql+asyncpg://queryus:queryus_dev_password@localhost:5432/queryus
REDIS_URL=redis://localhost:6379
GOOGLE_API_KEY=AIzaSyBe69gnydcPsiTuAD-FNHXw3yVrimsrV34
LLM_PROVIDER=google
```

### 5. Run Database Migrations

```bash
cd backend
conda activate queryus
alembic upgrade head
```

### 6. Start Backend

```bash
cd backend
conda activate queryus
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be running at: **http://localhost:8000**

### 7. Start Frontend

New terminal:
```bash
npm install
npm run dev
```

Frontend will be running at: **http://localhost:8080**

---

## ✅ Verify Installation

### Check Conda Environment

```bash
conda activate queryus
python --version
# Should show: Python 3.11.x

python -c "import google.generativeai; print('Gemini SDK installed!')"
# Should show: Gemini SDK installed!

python -c "import fastapi; print('FastAPI installed!')"
# Should show: FastAPI installed!
```

### Check Services

**PostgreSQL:**
```bash
psql -h localhost -U queryus -d queryus -c "SELECT version();"
```

**Redis:**
```bash
redis-cli ping
# Should return: PONG
```

**Backend:**
```bash
curl http://localhost:8000/health
# Should return: {"status":"healthy","version":"0.1.0"}
```

**Frontend:**
Open http://localhost:8080 in browser

---

## 🎮 Daily Workflow

### Start Everything

```bash
# Terminal 1: Backend
cd backend
conda activate queryus
uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
npm run dev

# Browser
open http://localhost:8080
```

### Stop Everything

- Press `Ctrl+C` in both terminals
- If using Docker for PostgreSQL/Redis:
  ```bash
  docker stop queryus-postgres queryus-redis
  ```

---

## 🔧 Conda Commands Cheat Sheet

### Environment Management

```bash
# Create environment
conda env create -f environment.yml

# Activate environment
conda activate queryus

# Deactivate environment
conda deactivate

# Update environment
conda env update -f environment.yml --prune

# Remove environment
conda env remove -n queryus

# List environments
conda env list

# Export current environment
conda env export > environment.yml
```

### Package Management

```bash
# Install new package
conda activate queryus
pip install package-name

# Update all packages
pip install --upgrade -r requirements.txt

# List installed packages
pip list

# Check outdated packages
pip list --outdated
```

---

## 🐛 Troubleshooting

### "conda: command not found"

**Install Miniconda:**
```bash
# macOS
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-arm64.sh
bash Miniconda3-latest-MacOSX-arm64.sh

# Linux
curl -O https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh
```

Then restart terminal and run:
```bash
conda init zsh  # or conda init bash
```

### "Could not connect to PostgreSQL"

**Check if PostgreSQL is running:**
```bash
# Homebrew service
brew services list | grep postgresql

# Start if stopped
brew services start postgresql@15

# Or use Docker
docker start queryus-postgres
```

**Check connection:**
```bash
psql -h localhost -U queryus -d queryus
```

### "Could not connect to Redis"

**Check if Redis is running:**
```bash
# Homebrew service
brew services list | grep redis

# Start if stopped
brew services start redis

# Or use Docker
docker start queryus-redis
```

**Test connection:**
```bash
redis-cli ping
```

### "ModuleNotFoundError"

Make sure conda environment is activated:
```bash
conda activate queryus

# Reinstall dependencies
pip install -r requirements.txt
```

### "Port 8000 already in use"

**Find and kill process:**
```bash
lsof -ti:8000 | xargs kill -9
```

### Database Migration Errors

**Reset migrations:**
```bash
cd backend
conda activate queryus

# Drop and recreate database
dropdb queryus
createdb queryus

# Run migrations fresh
alembic upgrade head
```

---

## 🔄 Updating Dependencies

### Add New Python Package

```bash
conda activate queryus
pip install new-package==1.0.0

# Update requirements.txt
pip freeze | grep new-package >> requirements.txt

# Update environment.yml
# (manually add to pip section)
```

### Update Existing Packages

```bash
conda activate queryus

# Update specific package
pip install --upgrade package-name

# Update all packages
pip install --upgrade -r requirements.txt
```

---

## 📊 Performance Comparison

### Conda vs Docker

**Conda Pros:**
- ✅ Faster startup (no container overhead)
- ✅ Direct debugging
- ✅ Better IDE integration
- ✅ Lower memory usage
- ✅ Easier dependency management

**Docker Pros:**
- ✅ Consistent environment
- ✅ Easier deployment
- ✅ Includes PostgreSQL/Redis
- ✅ Isolated from system

**Recommendation:** Use Conda for development, Docker for production/deployment.

---

## 🎯 Hybrid Setup (Best of Both)

Use Conda for Python, Docker for databases:

```bash
# Terminal 1: Start databases with Docker
docker run -d --name queryus-postgres \
  -e POSTGRES_USER=queryus \
  -e POSTGRES_PASSWORD=queryus_dev_password \
  -e POSTGRES_DB=queryus \
  -p 5432:5432 postgres:15

docker run -d --name queryus-redis \
  -p 6379:6379 redis:7

# Terminal 2: Run backend with Conda
cd backend
conda activate queryus
uvicorn app.main:app --reload --port 8000

# Terminal 3: Run frontend
npm run dev
```

**Why?** Conda gives you fast Python dev, Docker handles infrastructure.

---

## 🧪 Testing with Conda

```bash
cd backend
conda activate queryus

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py -v

# Run with output
pytest -s
```

---

## 📚 Next Steps

1. ✅ Conda environment created
2. ✅ PostgreSQL running
3. ✅ Redis running
4. ✅ Migrations complete
5. ✅ Backend started
6. ✅ Frontend started
7. 🎯 Open http://localhost:8080 and chat with Gemini!

---

## 💡 Pro Tips

### Auto-activate Environment

Add to `~/.zshrc` or `~/.bashrc`:
```bash
# Auto-activate queryus when entering project
cd() {
  builtin cd "$@"
  if [[ -f environment.yml ]]; then
    conda activate queryus
  fi
}
```

### Create Aliases

```bash
# Add to ~/.zshrc
alias qstart="cd ~/path/to/query-companion/backend && conda activate queryus && uvicorn app.main:app --reload"
alias qtest="cd ~/path/to/query-companion/backend && conda activate queryus && pytest"
alias qfrontend="cd ~/path/to/query-companion && npm run dev"
```

### VS Code Integration

Install extensions:
- Python (Microsoft)
- Pylance (Microsoft)

Configure `.vscode/settings.json`:
```json
{
  "python.defaultInterpreterPath": "${env:HOME}/miniconda3/envs/queryus/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  "python.formatting.provider": "black"
}
```

---

## 🎊 You're All Set!

Your Queryus is now running with Conda! 🐍

**Start developing:**
```bash
conda activate queryus
cd backend
uvicorn app.main:app --reload
```

Happy coding! 🚀
