# Queryus - AI-Powered SQL Assistant

> **🎉 Now Powered by Google Gemini!** Your API key is configured and ready to use.  
> **📖 Quick Links:** [Gemini Setup](GOOGLE_GEMINI_SETUP.md) · [Changes Summary](CHANGES_SUMMARY.md) · [Integration Details](GEMINI_INTEGRATION_COMPLETE.md)

Convert natural language to SQL using AI. Chat with your databases in any language.

![Status](https://img.shields.io/badge/status-production--ready-green)
![Backend](https://img.shields.io/badge/backend-FastAPI-009688)
![Frontend](https://img.shields.io/badge/frontend-React-61DAFB)
![AI](https://img.shields.io/badge/AI-Google%20Gemini-4285F4)

## 🚀 Quick Start

Get running in 5 minutes with **Google Gemini** using **Conda**:

```bash
# 1. Create Conda environment
cd backend
conda env create -f environment.yml
conda activate queryus

# 2. Setup services (PostgreSQL + Redis)
# Option A: Install locally (brew install postgresql redis)
# Option B: Use Docker (see CONDA_SETUP.md)

# 3. Run migrations
alembic upgrade head

# 4. Start backend
uvicorn app.main:app --reload --port 8000

# 5. Start frontend (new terminal)
cd ..
npm install
npm run dev

# 6. Open http://localhost:8080
```

**Your API Key**: Already configured to use Google Gemini! ✅  
**Setup Guide**: See `CONDA_SETUP.md` for detailed instructions.

---

## 🎯 Features

### Core Capabilities
- 🗣️ **Natural Language to SQL** - Ask questions in plain English (or 60+ other languages)
- 🔌 **Multi-Database Support** - PostgreSQL, MySQL, Snowflake, BigQuery, and more
- ⚡ **Three Performance Tiers** - Valtryek (fast), Achillies (balanced), Spryzen (deep)
- 🖼️ **Image Upload** - Upload ER diagrams for better context
- 🔍 **Web Search Integration** - Searches the web for context when needed
- 📊 **Query Execution** - Run queries directly and see results

### Enterprise Features
- 🔐 **Encrypted Credentials** - Fernet encryption for database credentials
- 👥 **RBAC & Policies** - Role-based access control, table allowlists, column masking
- 📝 **Audit Logging** - Complete audit trail of all queries
- 📈 **Prometheus Metrics** - Production-ready observability
- 🌍 **Multilingual** - Detects language automatically, responds in user's language
- 🔄 **Streaming Updates** - Real-time progress via Server-Sent Events

---

## 📁 Project Structure

```
query-companion/
├── backend/              # FastAPI Backend (Python 3.11)
│   ├── app/
│   │   ├── api/         # REST API endpoints
│   │   ├── core/        # 9-stage agent pipeline
│   │   ├── models/      # Data models
│   │   ├── services/    # Business logic
│   │   └── db/          # Database & caching
│   ├── tests/           # Test suite
│   ├── Dockerfile
│   └── docker-compose.yml
│
├── src/                 # React Frontend (TypeScript)
│   ├── components/      # UI components
│   ├── contexts/        # React contexts
│   ├── lib/            # API client & utilities
│   └── pages/          # Page components
│
└── docs/
    ├── QUICKSTART.md                      # 5-minute setup
    ├── INTEGRATION_COMPLETE.md            # Integration overview
    ├── FRONTEND_BACKEND_INTEGRATION.md    # Detailed integration guide
    └── backend/
        ├── README.md                      # Backend documentation
        ├── DEPLOYMENT.md                  # Production deployment
        └── IMPLEMENTATION_SUMMARY.md      # Technical details
```

---

## 🏗️ Architecture

### 9-Stage Agent Pipeline

1. **Language Detection** → Identify user's language (60+ supported)
2. **Context Assembly** → Fetch relevant schema from cache/database
3. **Multimodal Ingestion** → Process uploaded images (ER diagrams)
4. **Tool Planning** → Decide which tools to use (web search, etc.)
5. **SQL Generation** → Generate query using Claude AI
6. **Validation** → Syntax check and safety validation
7. **Policy Enforcement** → Apply RBAC, masking, row-level security
8. **Query Execution** → Run query with timeout and pooling
9. **Response Composition** → Format response in user's language

### Tech Stack

**Backend:**
- FastAPI 0.104+ (async)
- PostgreSQL 15+ (SQLAlchemy 2.0)
- Redis 7+ (caching)
- **Google Gemini API** (Flash, Pro) ✅ Configured
- Anthropic Claude API (optional alternative)
- sqlglot (SQL parsing for 20+ dialects)

**Frontend:**
- React 18 + TypeScript
- Vite (build tool)
- shadcn/ui (components)
- TanStack Query (data fetching)

**Infrastructure:**
- Docker & Docker Compose
- Kubernetes-ready
- Prometheus metrics
- Structured logging (structlog)

---

## 🎮 Usage

### 1. Add Database Connection

```json
{
  "name": "Production DB",
  "type": "postgresql",
  "credentials": {
    "host": "localhost",
    "port": 5432,
    "username": "user",
    "password": "password",
    "database": "mydb"
  }
}
```

### 2. Ask Questions

**English:**
> "Show me top 10 customers by revenue last month"

**Spanish:**
> "Muéstrame los 10 principales clientes por ingresos del mes pasado"

**French:**
> "Montre-moi les 10 meilleurs clients par chiffre d'affaires le mois dernier"

### 3. Get SQL + Results

```sql
SELECT 
  c.name,
  SUM(o.total_amount) as revenue
FROM customers c
JOIN orders o ON c.id = o.customer_id
WHERE o.created_at >= DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')
GROUP BY c.name
ORDER BY revenue DESC
LIMIT 10;
```

Results displayed in interactive table with execution time.

---

## 🔧 Configuration

### Performance Modes

**Valtryek (Fast)**
- Model: Gemini 1.5 Flash
- Schema: Top 5 tables
- Tools: Max 1
- Timeout: 30s
- Auto-adds LIMIT 100

**Achillies (Balanced)** ⭐ Default
- Model: Gemini 1.5 Pro
- Schema: Top 15 tables + relationships
- Tools: Max 3
- Timeout: 120s
- Self-check enabled

**Spryzen (Deep)**
- Model: Gemini 1.5 Pro
- Schema: Top 30 tables + sample data
- Tools: Max 10
- Timeout: 300s
- Multi-candidate generation

### Environment Variables

**Backend (`backend/.env`):**
```env
# LLM Provider
LLM_PROVIDER=google
GOOGLE_API_KEY=AIzaSyBe69gnydcPsiTuAD-FNHXw3yVrimsrV34  # ✅ Your key

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=<from generate_keys.py>
ENCRYPTION_KEY=<from generate_keys.py>

# Optional
TAVILY_API_KEY=tvly-your-key-here  # For web search
```

**Frontend (`.env`):**
```env
VITE_API_URL=http://localhost:8000
```

---

## 📚 Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Get started in 5 minutes
- **[INTEGRATION_COMPLETE.md](./INTEGRATION_COMPLETE.md)** - Integration overview
- **[FRONTEND_BACKEND_INTEGRATION.md](./FRONTEND_BACKEND_INTEGRATION.md)** - Full integration guide
- **[backend/README.md](./backend/README.md)** - Backend documentation
- **[backend/DEPLOYMENT.md](./backend/DEPLOYMENT.md)** - Production deployment
- **API Docs** - http://localhost:8000/api/docs (when running)

---

## 🧪 Testing

### Backend Tests
```bash
cd backend
pytest
```

### API Testing
Visit http://localhost:8000/api/docs for interactive Swagger UI

### Manual Testing
```bash
# Health check
curl http://localhost:8000/health

# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

---

## 🚀 Deployment

### Development
```bash
# Backend
cd backend && docker-compose up

# Frontend
npm run dev
```

### Production

**Backend:**
```bash
cd backend
docker build -t queryus-api .
docker run -d --env-file .env -p 8000:8000 queryus-api
```

**Frontend:**
```bash
npm run build
# Deploy dist/ to CDN or static hosting
```

See `backend/DEPLOYMENT.md` for Kubernetes, monitoring, scaling, and more.

---

## 🔒 Security

- ✅ JWT authentication with secure tokens
- ✅ Fernet encryption for database credentials
- ✅ RBAC and policy enforcement
- ✅ SQL injection prevention (parameterized queries)
- ✅ Query timeout enforcement
- ✅ Audit logging for compliance
- ✅ Read-only connection enforcement
- ✅ DML/DDL operation blocking

---

## 📊 Monitoring

### Metrics (Prometheus)
- HTTP request metrics
- SQL generation latency
- Query execution time
- Tool usage statistics
- Policy violations
- Cache hit/miss rates

Access metrics at: http://localhost:8000/metrics

### Logs
```bash
# View all logs
docker-compose logs -f

# Just API
docker-compose logs -f api

# Database
docker-compose logs -f postgres
```

---

## 🤝 Contributing

While this is a personal project, feel free to:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🙏 Acknowledgments

- **Google** - Gemini AI models (primary LLM)
- **Anthropic** - Claude AI models (alternative)
- **FastAPI** - Web framework
- **React** - Frontend framework
- **shadcn/ui** - UI components
- **sqlglot** - SQL parsing
- **Tavily** - Web search API

---

## 📞 Support

- **Documentation**: See `docs/` folder
- **API Docs**: http://localhost:8000/api/docs
- **Issues**: Check logs with `docker-compose logs`
- **Quick Help**: See `QUICKSTART.md` or `FRONTEND_BACKEND_INTEGRATION.md`

---

## 🎯 Roadmap

✅ **Completed**
- Multi-stage agent pipeline
- Multi-database support
- Image upload & vision
- Web search integration
- Streaming responses
- Policy engine
- Audit logging
- Docker deployment

🚧 **In Progress**
- Connection management UI
- Schema explorer component
- Query history panel
- Settings UI

📋 **Planned**
- Query optimization suggestions
- Cost estimation
- Collaborative features
- More LLM providers

---

## ⚡ Quick Links

- **Start**: `QUICKSTART.md`
- **Integration**: `INTEGRATION_COMPLETE.md`
- **API**: http://localhost:8000/api/docs
- **Metrics**: http://localhost:8000/metrics
- **Frontend**: http://localhost:8080
- **Backend**: http://localhost:8000

---

**Ready to query your databases with AI? Start now with `QUICKSTART.md`!** 🚀
