# PostgreSQL MCP Server

## Dataset
- NYC taxi - https://www.kaggle.com/datasets/elemento/nyc-yellow-taxi-trip-data?resource=download
- NYC subway - https://data.ny.gov/api/views/ug6q-shqc/rows.csv?accessType=DOWNLOAD

This is a Model Context Protocol (MCP) server that allows Claude Desktop to execute SQL queries against a PostgreSQL database.

## Features

- Execute SQL queries against PostgreSQL database
- Proper MCP protocol implementation
- Error handling and logging
- Support for both SELECT and non-SELECT queries

## Prerequisites

1. Python 3.7 or higher
2. PostgreSQL database running locally
3. Claude Desktop application
4. Required Python packages:
   ```bash
   pip install psycopg2-binary
   ```

## Database Configuration

The server is configured to connect to a PostgreSQL database with these default settings:
- Database: `NYC`
- User: `user`
- Password: `password`
- Host: `localhost`
- Port: `5432`

To change these settings, edit the `DB_CONFIG` dictionary in `query_tool.py`.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install psycopg2-binary
```

### 2. Configure Claude Desktop

1. Open your Claude Desktop configuration file:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

2. Add the MCP server configuration:

```json
{
  "mcpServers": {
    "postgres-query": {
      "command": "python3",
      "args": [
        "/ABSOLUTE/PATH/TO/YOUR/WORKSPACE/query_tool.py"
      ],
      "env": {
        "PYTHONPATH": "/ABSOLUTE/PATH/TO/YOUR/WORKSPACE"
      }
    }
  }
}
```

**Important**: Replace `/ABSOLUTE/PATH/TO/YOUR/WORKSPACE` with the actual absolute path to your workspace directory.

### 3. Restart Claude Desktop

After saving the configuration file, completely restart Claude Desktop.

## Usage

Once configured, you can use the database query tool in Claude Desktop by asking questions like:

- "Show me the first 10 rows from the nyc_taxi_trips table"
- "Count how many trips are in the database"
- "What tables are available in the database?"

The tool will execute your SQL queries and return the results in a formatted way.

## Available Tool

### query_database

**Description**: Execute a SQL query on the PostgreSQL database and return results

**Parameters**:
- `sql` (string, required): The SQL query to execute

**Example queries**:
```sql
SELECT COUNT(*) FROM nyc_taxi_trips;
SELECT * FROM nyc_taxi_trips LIMIT 5;
SHOW TABLES;
```

## Troubleshooting

### Server not showing up in Claude Desktop

1. Check the configuration file syntax is valid JSON
2. Ensure the path to `query_tool.py` is absolute, not relative
3. Restart Claude Desktop completely
4. Check Claude Desktop logs:
   - **macOS**: `~/Library/Logs/Claude/mcp*.log`

### Database connection issues

1. Verify PostgreSQL is running
2. Check database credentials in `DB_CONFIG`
3. Ensure the database exists and is accessible
4. Check server logs for specific error messages

### Tool calls failing

1. Check Claude Desktop logs for errors
2. Verify the SQL syntax is correct
3. Ensure you have proper permissions for the database operations

## Logging

The server logs to stderr, which can be found in Claude Desktop's MCP logs. Logs include:
- Connection attempts
- Query execution details
- Error messages
- Request/response information

## Security Notes

- This server executes SQL queries directly against your database
- Be cautious with queries that modify data (INSERT, UPDATE, DELETE)
- Consider implementing query restrictions for production use
- The current configuration uses basic authentication - consider more secure methods for production


## Some Prompts
- @mcp2 how many trips in janurary 2015 in taxi
- can you correlate data from subway and taxis and figure out most travelled routes
- @postgresdb how many total trips
- on which day maximum trips happened
- most travelled route
- what was the most frequest subway route taken
- can you compare this with taxi data and check if routes where there were most travellers via taxi also have most travellers via subway or is there a difference


