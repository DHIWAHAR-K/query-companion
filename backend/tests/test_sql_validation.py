"""SQL validation tests"""
import pytest
from app.core.agent.stages.validation import validate_sql
from app.models.domain import SQLDialect, Schema


@pytest.fixture
def mock_schema():
    """Create mock schema for testing"""
    return Schema(
        tables=[
            {
                "name": "users",
                "columns": [
                    {"name": "id", "type": "INTEGER"},
                    {"name": "email", "type": "VARCHAR"}
                ]
            }
        ],
        relationships=[]
    )


def test_valid_select_query(mock_schema):
    """Test validation of valid SELECT query"""
    sql = "SELECT id, email FROM users WHERE id = 1"
    result = validate_sql(sql, mock_schema, SQLDialect.POSTGRESQL)
    
    assert result.status == "valid"
    assert result.safe_to_execute is True


def test_dangerous_drop_query(mock_schema):
    """Test detection of DROP statement"""
    sql = "DROP TABLE users"
    result = validate_sql(sql, mock_schema, SQLDialect.POSTGRESQL)
    
    assert result.status == "warning"
    assert any("DROP" in msg for msg in result.messages)


def test_select_star_warning(mock_schema):
    """Test warning for SELECT *"""
    sql = "SELECT * FROM users"
    result = validate_sql(sql, mock_schema, SQLDialect.POSTGRESQL)
    
    assert any("SELECT *" in msg for msg in result.messages)


def test_cross_join_warning(mock_schema):
    """Test warning for CROSS JOIN without LIMIT"""
    sql = "SELECT * FROM users CROSS JOIN users"
    result = validate_sql(sql, mock_schema, SQLDialect.POSTGRESQL)
    
    assert result.status == "warning"
    assert any("CROSS JOIN" in msg for msg in result.messages)


def test_invalid_syntax(mock_schema):
    """Test detection of invalid SQL syntax"""
    sql = "SELECTTT id FROM users"
    result = validate_sql(sql, mock_schema, SQLDialect.POSTGRESQL)
    
    assert result.status == "error"
    assert result.safe_to_execute is False
