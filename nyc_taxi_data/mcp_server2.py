# postgres_mcp_server.py
"""
PostgreSQL MCP Server for Claude Desktop using FastMCP
Allows SQL queries to be executed against PostgreSQL database
"""

import asyncio
import logging
import sys
from typing import Dict, Any, Optional
import asyncpg
from datetime import datetime
import os

from mcp.server.fastmcp import FastMCP

# Configure logging to stderr (not stdout for MCP)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "host": os.getenv("POSTGRES_HOST", "localhost"),
    "port": int(os.getenv("POSTGRES_PORT", "5432")),
    "database": os.getenv("POSTGRES_DB", "NYC"),
    "user": os.getenv("POSTGRES_USER", "user"),
    "password": os.getenv("POSTGRES_PASSWORD", "password")
}

# Global database pool
db_pool: Optional[asyncpg.Pool] = None
schema_cache: Dict[str, Any] = {}

# Create FastMCP server
mcp = FastMCP("postgres-query-server")

async def initialize_database():
    """Initialize database connection pool"""
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(
            host=DB_CONFIG["host"],
            port=DB_CONFIG["port"],
            database=DB_CONFIG["database"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            min_size=1,
            max_size=10
        )
        logger.info("Database pool created successfully")
        await cache_schema_info()
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise

async def cache_schema_info():
    """Cache database schema information for better SQL generation"""
    global schema_cache
    try:
        async with db_pool.acquire() as conn:
            # Get all tables and their columns
            query = """
            SELECT
                t.table_name,
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                tc.constraint_type
            FROM information_schema.tables t
            LEFT JOIN information_schema.columns c ON t.table_name = c.table_name
            LEFT JOIN information_schema.table_constraints tc ON t.table_name = tc.table_name
            WHERE t.table_schema = 'public'
            ORDER BY t.table_name, c.ordinal_position;
            """

            rows = await conn.fetch(query)

            for row in rows:
                table_name = row['table_name']
                if table_name not in schema_cache:
                    schema_cache[table_name] = {
                        'columns': [],
                        'constraints': []
                    }

                if row['column_name']:
                    schema_cache[table_name]['columns'].append({
                        'name': row['column_name'],
                        'type': row['data_type'],
                        'nullable': row['is_nullable'] == 'YES',
                        'default': row['column_default']
                    })

                if row['constraint_type']:
                    schema_cache[table_name]['constraints'].append(row['constraint_type'])

            logger.info(f"Cached schema for {len(schema_cache)} tables")
    except Exception as e:
        logger.error(f"Failed to cache schema: {e}")

def get_schema_context() -> str:
    """Generate schema context for SQL generation"""
    context = "Database Schema:\n"
    for table_name, info in schema_cache.items():
        context += f"\nTable: {table_name}\n"
        context += "Columns:\n"
        for col in info['columns']:
            nullable = "NULL" if col['nullable'] else "NOT NULL"
            default = f" DEFAULT {col['default']}" if col['default'] else ""
            context += f"  - {col['name']} ({col['type']}) {nullable}{default}\n"
    return context

async def execute_query(sql: str) -> Dict[str, Any]:
    """Execute SQL query and return results"""
    try:
        async with db_pool.acquire() as conn:
            # Determine if it's a SELECT or modification query
            sql_lower = sql.strip().lower()

            if sql_lower.startswith('select') or sql_lower.startswith('with'):
                # SELECT query
                rows = await conn.fetch(sql)

                # Convert to list of dictionaries
                results = []
                for row in rows:
                    # Convert Row to dict, handling special types
                    row_dict = {}
                    for key, value in row.items():
                        if isinstance(value, datetime):
                            row_dict[key] = value.isoformat()
                        else:
                            row_dict[key] = value
                    results.append(row_dict)

                return {
                    'success': True,
                    'type': 'select',
                    'rows': results,
                    'row_count': len(results)
                }
            else:
                # INSERT, UPDATE, DELETE, etc.
                result = await conn.execute(sql)

                # Extract row count from result string
                row_count = 0
                if result:
                    parts = result.split()
                    if len(parts) >= 2 and parts[-1].isdigit():
                        row_count = int(parts[-1])

                return {
                    'success': True,
                    'type': 'modification',
                    'message': result,
                    'affected_rows': row_count
                }

    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'sql': sql
        }

# FastMCP Tools
@mcp.tool()
async def execute_sql(sql: str, explain_plan: bool = False) -> str:
    """Execute SQL queries against PostgreSQL database. Accepts both SELECT and modification queries (INSERT, UPDATE, DELETE, etc.)."""
    if not sql.strip():
        return "Error: No SQL query provided"

    # Add EXPLAIN if requested
    if explain_plan and sql.lower().strip().startswith('select'):
        sql = f"EXPLAIN ANALYZE {sql}"

    result = await execute_query(sql)

    if result['success']:
        if result['type'] == 'select':
            response = f"Query executed successfully.\n"
            response += f"Returned {result['row_count']} rows.\n\n"

            if result['rows']:
                # Format results as table
                if len(result['rows']) <= 100:  # Limit display for large results
                    response += "Results:\n"
                    import json
                    response += json.dumps(result['rows'], indent=2, default=str)
                else:
                    response += f"Large result set ({len(result['rows'])} rows). Showing first 10:\n"
                    import json
                    response += json.dumps(result['rows'][:10], indent=2, default=str)
                    response += f"\n... and {len(result['rows']) - 10} more rows"
            else:
                response += "No rows returned."
        else:
            response = f"Query executed successfully.\n{result['message']}\n"
            response += f"Affected rows: {result['affected_rows']}"
    else:
        response = f"Query failed: {result['error']}\nSQL: {result.get('sql', 'N/A')}"

    return response

@mcp.tool()
async def get_schema(table_name: str = None) -> str:
    """Get database schema information including tables, columns, and constraints"""
    import json

    if table_name:
        if table_name in schema_cache:
            schema_info = {table_name: schema_cache[table_name]}
        else:
            schema_info = {}

        response = f"Schema for table '{table_name}':\n"
        response += json.dumps(schema_info, indent=2, default=str)
    else:
        response = "Database Schema Information:\n"
        response += json.dumps(schema_cache, indent=2, default=str)

    return response

@mcp.tool()
async def natural_language_query(question: str, return_sql: bool = True) -> str:
    """Convert natural language question to SQL query and execute it. This tool helps translate human questions into proper SQL."""
    if not question.strip():
        return "Error: No question provided"

    # Generate SQL context prompt for the LLM
    schema_context = get_schema_context()

    response = f"Natural Language Query Analysis:\n\n"
    response += f"Question: {question}\n\n"
    response += f"Schema Context Available: {len(schema_cache)} tables\n\n"
    response += "To generate the appropriate SQL query, I need you to analyze the question against the database schema and provide the SQL query. "
    response += "The schema information is available via the get_schema tool if needed.\n\n"
    response += f"Database Schema Summary:\n"
    for table_name in schema_cache.keys():
        response += f"- {table_name}\n"

    response += f"\n\nSchema Details:\n{schema_context}"

    return response

async def main():
    """Main entry point"""
    try:
        # Initialize database connection
        await initialize_database()
        logger.info("Starting PostgreSQL MCP server")

        # Run the FastMCP server using the async method
        await mcp.run_stdio_async()

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        if db_pool:
            await db_pool.close()
            logger.info("Database pool closed")

if __name__ == "__main__":
    asyncio.run(main())
