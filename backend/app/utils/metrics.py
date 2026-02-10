"""Prometheus metrics configuration"""
from prometheus_client import Counter, Histogram, Gauge
import structlog

logger = structlog.get_logger()

# Request metrics
http_requests_total = Counter(
    'queryus_http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'queryus_http_request_duration_seconds',
    'HTTP request duration',
    ['method', 'endpoint']
)

# SQL generation metrics
sql_generation_total = Counter(
    'queryus_sql_generation_total',
    'Total SQL generations',
    ['mode', 'dialect', 'status']
)

sql_generation_duration_seconds = Histogram(
    'queryus_sql_generation_duration_seconds',
    'SQL generation duration',
    ['mode']
)

# Query execution metrics
query_execution_total = Counter(
    'queryus_query_execution_total',
    'Total query executions',
    ['dialect', 'status']
)

query_execution_duration_seconds = Histogram(
    'queryus_query_execution_duration_seconds',
    'Query execution duration',
    ['dialect']
)

query_rows_returned = Histogram(
    'queryus_query_rows_returned',
    'Number of rows returned by queries',
    ['dialect']
)

# Tool usage metrics
tool_usage_total = Counter(
    'queryus_tool_usage_total',
    'Tool usage count',
    ['tool', 'status']
)

tool_duration_seconds = Histogram(
    'queryus_tool_duration_seconds',
    'Tool execution duration',
    ['tool']
)

# Policy metrics
policy_enforcement_total = Counter(
    'queryus_policy_enforcement_total',
    'Policy enforcement events',
    ['policy_type', 'result']
)

policy_violations_total = Counter(
    'queryus_policy_violations_total',
    'Policy violations',
    ['policy_type']
)

# Agent runtime metrics
agent_pipeline_duration_seconds = Histogram(
    'queryus_agent_pipeline_duration_seconds',
    'Full agent pipeline duration',
    ['mode']
)

agent_pipeline_stage_duration_seconds = Histogram(
    'queryus_agent_pipeline_stage_duration_seconds',
    'Individual pipeline stage duration',
    ['stage', 'mode']
)

# Active connections gauge
active_connections = Gauge(
    'queryus_active_connections',
    'Number of active database connections'
)

# Cache metrics
cache_hits_total = Counter(
    'queryus_cache_hits_total',
    'Cache hits',
    ['cache_type']
)

cache_misses_total = Counter(
    'queryus_cache_misses_total',
    'Cache misses',
    ['cache_type']
)


def record_sql_generation(mode: str, dialect: str, duration: float, status: str):
    """Record SQL generation metrics"""
    sql_generation_total.labels(mode=mode, dialect=dialect, status=status).inc()
    sql_generation_duration_seconds.labels(mode=mode).observe(duration)


def record_query_execution(dialect: str, duration: float, row_count: int, status: str):
    """Record query execution metrics"""
    query_execution_total.labels(dialect=dialect, status=status).inc()
    query_execution_duration_seconds.labels(dialect=dialect).observe(duration)
    query_rows_returned.labels(dialect=dialect).observe(row_count)


def record_tool_usage(tool: str, duration: float, status: str):
    """Record tool usage metrics"""
    tool_usage_total.labels(tool=tool, status=status).inc()
    tool_duration_seconds.labels(tool=tool).observe(duration)


def record_policy_enforcement(policy_type: str, result: str, is_violation: bool = False):
    """Record policy enforcement metrics"""
    policy_enforcement_total.labels(policy_type=policy_type, result=result).inc()
    if is_violation:
        policy_violations_total.labels(policy_type=policy_type).inc()
