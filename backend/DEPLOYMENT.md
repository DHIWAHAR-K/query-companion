# Queryus Backend - Deployment Guide

## Quick Start (Development)

### Prerequisites
- Docker & Docker Compose
- Anthropic API key

### Steps

1. **Clone and setup**
```bash
cd backend
cp .env.example .env
```

2. **Add your API keys to `.env`**
```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
TAVILY_API_KEY=tvly-your-key-here  # Optional
```

3. **Generate secure keys**
```bash
python scripts/generate_keys.py
# Copy output to .env file
```

4. **Start services**
```bash
docker-compose up -d
```

5. **Run migrations**
```bash
docker-compose exec api alembic upgrade head
```

6. **Access API**
- API: http://localhost:8000
- Docs: http://localhost:8000/api/docs
- Metrics: http://localhost:8000/metrics

---

## Production Deployment

### 1. Environment Configuration

Create `.env` with production values:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@prod-db:5432/queryus
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://prod-redis:6379

# Security (GENERATE NEW KEYS!)
SECRET_KEY=<from generate_keys.py>
ENCRYPTION_KEY=<from generate_keys.py>

# LLM
ANTHROPIC_API_KEY=sk-ant-your-key
VALTRYEK_MODEL=claude-haiku-3-5-20241022
ACHILLIES_MODEL=claude-sonnet-4-20250514
SPRYZEN_MODEL=claude-opus-4-5-20251101

# Tools
TAVILY_API_KEY=tvly-your-key
ENABLE_WEB_SEARCH=true
ENABLE_VISION=true

# App
DEBUG=false
CORS_ORIGINS=https://your-frontend.com
MAX_CONCURRENT_QUERIES=50
DEFAULT_QUERY_TIMEOUT=300
MAX_RESULT_ROWS=10000
```

### 2. Database Setup

```bash
# Create database
createdb queryus

# Run migrations
alembic upgrade head
```

### 3. Docker Build

```bash
docker build -t queryus-api:latest .
```

### 4. Run Container

```bash
docker run -d \
  --name queryus-api \
  --env-file .env \
  -p 8000:8000 \
  queryus-api:latest
```

### 5. Health Check

```bash
curl http://localhost:8000/health
```

---

## Kubernetes Deployment

### ConfigMap for config.yaml
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: queryus-config
data:
  config.yaml: |
    modes:
      valtryek:
        model: claude-haiku-3-5-20241022
        timeout_seconds: 30
      achillies:
        model: claude-sonnet-4-20250514
        timeout_seconds: 120
      spryzen:
        model: claude-opus-4-5-20251101
        timeout_seconds: 300
```

### Secret for sensitive data
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: queryus-secrets
type: Opaque
stringData:
  DATABASE_URL: postgresql+asyncpg://...
  REDIS_URL: redis://...
  ANTHROPIC_API_KEY: sk-ant-...
  SECRET_KEY: ...
  ENCRYPTION_KEY: ...
```

### Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: queryus-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: queryus-api
  template:
    metadata:
      labels:
        app: queryus-api
    spec:
      containers:
      - name: api
        image: queryus-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - secretRef:
            name: queryus-secrets
        volumeMounts:
        - name: config
          mountPath: /app/config.yaml
          subPath: config.yaml
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
      volumes:
      - name: config
        configMap:
          name: queryus-config
---
apiVersion: v1
kind: Service
metadata:
  name: queryus-api
spec:
  selector:
    app: queryus-api
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

---

## Monitoring

### Prometheus Setup

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'queryus'
    static_configs:
      - targets: ['queryus-api:8000']
    metrics_path: '/metrics'
```

### Key Metrics to Monitor

- `queryus_http_requests_total` - Total requests
- `queryus_sql_generation_duration_seconds` - SQL generation latency
- `queryus_query_execution_duration_seconds` - Query execution time
- `queryus_policy_violations_total` - Policy violations
- `queryus_cache_hits_total` / `queryus_cache_misses_total` - Cache performance

### Grafana Dashboard

Import dashboard JSON from `monitoring/grafana-dashboard.json`

---

## Backup & Recovery

### Database Backup
```bash
# Backup
pg_dump queryus > backup-$(date +%Y%m%d).sql

# Restore
psql queryus < backup-20260210.sql
```

### Redis Backup
```bash
# Redis automatically creates dump.rdb
# Copy from container:
docker cp queryus-redis:/data/dump.rdb ./redis-backup.rdb
```

---

## Security Checklist

- [ ] Change all default passwords
- [ ] Generate new SECRET_KEY and ENCRYPTION_KEY
- [ ] Enable HTTPS (use reverse proxy like nginx)
- [ ] Set up firewall rules
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Set up log aggregation
- [ ] Enable database encryption at rest
- [ ] Implement secrets rotation
- [ ] Set up intrusion detection

---

## Scaling Considerations

### Horizontal Scaling
- Run multiple API instances behind load balancer
- Each instance connects to shared PostgreSQL and Redis
- Use connection pooling efficiently

### Vertical Scaling
- Increase `DB_POOL_SIZE` for more concurrent queries
- Increase `MAX_CONCURRENT_QUERIES` setting
- Add more CPU/memory to containers

### Database Scaling
- Use PostgreSQL read replicas for read-heavy workloads
- Consider partitioning audit_logs table by date
- Implement query result caching in Redis

---

## Troubleshooting

### API won't start
```bash
# Check logs
docker-compose logs api

# Common issues:
# - Database not ready: wait longer
# - Missing env vars: check .env file
# - Port conflict: change port in docker-compose.yml
```

### High latency
```bash
# Check metrics
curl http://localhost:8000/metrics

# Common causes:
# - Anthropic API latency: use faster model (Valtryek)
# - Database slow: check query performance, add indexes
# - Redis down: check redis connection
```

### Policy errors
```bash
# Check audit logs
SELECT * FROM audit_logs 
WHERE execution_status = 'blocked' 
ORDER BY timestamp DESC 
LIMIT 10;
```

---

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/queryus
- Documentation: https://docs.queryus.dev
- Email: support@queryus.dev
