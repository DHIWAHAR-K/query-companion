# Queryus Backend

AI-powered conversational SQL assistant backend built with FastAPI.

## Features

- 🤖 Multi-stage agent pipeline for SQL generation
- 🔐 JWT authentication with encrypted credentials
- 🗄️ Multiple database dialect support (PostgreSQL, MySQL, Snowflake, etc.)
- ⚡ Three performance modes (Valtryek, Achillies, Spryzen)
- 🌍 Multilingual support with automatic language detection
- 🔍 SQL validation and safety checks
- 📊 Query execution with timeout controls

## Tech Stack

- **Framework**: FastAPI 0.104+
- **Database**: PostgreSQL with SQLAlchemy 2.0 (async)
- **Cache**: Redis
- **LLM**: Anthropic Claude API
- **SQL Parsing**: sqlglot

## Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Anthropic API key

### Installation

1. Clone the repository:
```bash
cd backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file:
```bash
cp .env.example .env
```

5. Update `.env` with your configuration:
```env
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/queryus
REDIS_URL=redis://localhost:6379
ANTHROPIC_API_KEY=sk-ant-your-key-here
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-fernet-key
```

To generate a Fernet encryption key:
```python
from cryptography.fernet import Fernet
print(Fernet.generate_key().decode())
```

6. Run database migrations:
```bash
alembic upgrade head
```

### Running the Server

Development mode:
```bash
uvicorn app.main:app --reload --port 8000
```

Production mode:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### API Documentation

Once running, access:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

## Architecture

### Agent Pipeline

The core of Queryus is a 9-stage pipeline:

1. **Language Detection**: Identify user's language using langdetect
2. **Context Assembly**: Gather schema metadata and conversation history
3. **Multimodal Ingestion**: Process image attachments (ER diagrams, screenshots)
4. **Tool Planning**: Decide which tools to invoke (web search, schema samples)
5. **SQL Generation**: Generate query using Claude API
6. **Validation**: Check syntax and safety (DML/DDL detection, LIMIT checks)
7. **Policy Enforcement**: Apply RBAC, column masking, row-level security
8. **Execution**: Run query with timeout and result streaming
9. **Response Composition**: Format response in user's language

### Project Structure

```
backend/
├── app/
│   ├── api/v1/              # API endpoints
│   │   ├── auth.py          # Authentication
│   │   ├── chat.py          # Chat/messaging
│   │   ├── connections.py   # DB connections
│   │   └── schema.py        # Schema introspection
│   ├── core/                # Core business logic
│   │   ├── agent/           # Agent runtime
│   │   │   ├── runtime.py   # Main orchestrator
│   │   │   └── stages/      # Pipeline stages
│   │   ├── security/        # Auth & encryption
│   │   └── sql/             # SQL utilities
│   ├── models/              # Data models
│   │   ├── database.py      # SQLAlchemy ORM
│   │   ├── domain.py        # Pydantic domain models
│   │   └── schemas.py       # API request/response
│   ├── services/            # Business services
│   ├── db/                  # Database setup
│   └── utils/               # Utilities
├── alembic/                 # Database migrations
├── config.yaml              # Mode configurations
└── requirements.txt         # Dependencies
```

## Performance Modes

### Valtryek (Fast)
- Model: claude-haiku-3-5
- Max schema tables: 5
- Max tool calls: 1
- Auto-add LIMIT 100
- Timeout: 30s

### Achillies (Balanced)
- Model: claude-sonnet-4
- Max schema tables: 15
- Max tool calls: 3
- Suggest LIMIT 1000
- Timeout: 120s
- Self-check enabled

### Spryzen (Deep)
- Model: claude-opus-4-5
- Max schema tables: 30
- Max tool calls: 10
- No limit restrictions
- Timeout: 300s
- Multi-candidate generation
- EXPLAIN PLAN analysis

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `GET /api/v1/auth/me` - Get current user

### Chat
- `POST /api/v1/chat/message` - Send message and get SQL
- `GET /api/v1/chat/conversations` - List conversations
- `GET /api/v1/chat/conversations/{id}` - Get conversation details

### Connections
- `POST /api/v1/connections` - Create DB connection
- `GET /api/v1/connections` - List connections
- `GET /api/v1/connections/{id}` - Get connection
- `DELETE /api/v1/connections/{id}` - Delete connection
- `POST /api/v1/connections/test` - Test connection

## Development

### Running Tests
```bash
pytest
```

### Database Migrations

Create new migration:
```bash
alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
alembic upgrade head
```

Rollback:
```bash
alembic downgrade -1
```

## Environment Variables

See `.env.example` for all configuration options.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `ANTHROPIC_API_KEY`: Claude API key
- `SECRET_KEY`: JWT signing key
- `ENCRYPTION_KEY`: Fernet key for credential encryption
- `CORS_ORIGINS`: Allowed frontend origins

## License

MIT
