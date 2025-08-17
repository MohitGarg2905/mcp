import sys
import json
import logging
import psycopg2
from typing import Any, Dict, List

# Configure logging to stderr (not stdout for MCP)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)

# PostgreSQL connection config
DB_CONFIG = {
    "dbname": "NYC",
    "user": "user",
    "password": "password",
    "host": "localhost",
    "port": 5432,
}

def query_db(sql: str) -> Dict[str, Any]:
    """Execute SQL query against PostgreSQL database."""
    try:
        logger.info(f"Executing query: {sql[:100]}...")
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(sql)

        # Fetch all rows from SELECT queries; commit other types
        if sql.strip().lower().startswith("select"):
            rows = cur.fetchall()
            cols = [desc[0] for desc in cur.description]
            result = [dict(zip(cols, row)) for row in rows]
            logger.info(f"Query returned {len(result)} rows")
        else:
            conn.commit()
            result = {"status": "Query executed successfully"}
            logger.info("Non-SELECT query executed successfully")

        cur.close()
        conn.close()
        return {"result": result}
    except Exception as e:
        logger.error(f"Database error: {str(e)}")
        return {"error": str(e)}

def handle_initialize(req: Dict[str, Any]) -> Dict[str, Any]:
    """Handle MCP initialize request."""
    logger.info("Handling initialize request")
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "serverInfo": {
                "name": "postgres-query-server",
                "version": "1.0.0"
            }
        }
    }

def handle_tools_list(req: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/list request."""
    logger.info("Handling tools/list request")
    return {
        "jsonrpc": "2.0",
        "id": req["id"],
        "result": {
            "tools": [
                {
                    "name": "query_database",
                    "description": "Execute a SQL query on the PostgreSQL database and return results",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "sql": {
                                "type": "string",
                                "description": "The SQL query to execute"
                            }
                        },
                        "required": ["sql"]
                    }
                }
            ]
        }
    }

def handle_tools_call(req: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tools/call request."""
    logger.info("Handling tools/call request")

    params = req.get("params", {})
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if tool_name != "query_database":
        return {
            "jsonrpc": "2.0",
            "id": req["id"],
            "error": {
                "code": -32602,
                "message": f"Unknown tool: {tool_name}"
            }
        }

    sql = arguments.get("sql", "")
    if not sql:
        return {
            "jsonrpc": "2.0",
            "id": req["id"],
            "error": {
                "code": -32602,
                "message": "Missing required parameter: sql"
            }
        }

    # Execute the query
    result = query_db(sql)

    response = {
        "jsonrpc": "2.0",
        "id": req["id"],
    }

    if "error" in result:
        response["error"] = {
            "code": -32001,
            "message": f"Database error: {result['error']}"
        }
    else:
        response["result"] = {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(result["result"], indent=2, default=str)
                }
            ]
        }

    return response

def send_error_response(req: Dict[str, Any], code: int, message: str) -> None:
    """Send an error response."""
    # Only send 'id' if req contains it and it's not null
    if "id" in req and req["id"] is not None:
        resp = {
            "jsonrpc": "2.0",
            "id": req["id"],
            "error": {"code": code, "message": message}
        }
        print(json.dumps(resp), flush=True)
    # For notifications (no id): Do not send a reply

def main() -> None:
    """Main server loop."""
    logger.info("Starting PostgreSQL MCP server")

    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                logger.info("EOF received, shutting down")
                break

            line = line.strip()
            if not line:
                continue

            logger.debug(f"Received request: {line}")
            req = json.loads(line)
            method = req.get("method")

            if method == "initialize":
                resp = handle_initialize(req)
            elif method == "tools/list":
                resp = handle_tools_list(req)
            elif method == "tools/call":
                resp = handle_tools_call(req)
            elif method == "resources/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req["id"],
                    "result": {
                        "resources": []
                    }
                }
            elif method == "prompts/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req["id"],
                    "result": {
                        "prompts": []
                    }
                }
            else:
                logger.warning(f"Unknown method: {method}")
                send_error_response(req, -32601, f"Method {method} not found.")
                continue  # Do not print resp below for unknown method

            print(json.dumps(resp), flush=True)
            logger.debug(f"Sent response for method: {method}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {str(e)}")
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "Parse error"}
            }
            print(json.dumps(err_resp), flush=True)
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            req_id = req.get("id") if isinstance(req, dict) else None
            err_resp = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal error: {str(e)}"}
            }
            print(json.dumps(err_resp), flush=True)


if __name__ == "__main__":
    main()
