import os

from .server import mcp

if __name__ == "__main__":
    # MCP_TRANSPORT=stdio (default) launches over stdio — used by Claude Desktop
    # locally via `docker exec`. MCP_TRANSPORT=http runs a standalone Streamable
    # HTTP server (alternative to mounting it into the FastAPI app in main.py).
    transport = os.getenv("MCP_TRANSPORT", "stdio").lower()
    if transport in ("http", "streamable-http", "streamable_http"):
        mcp.settings.host = os.getenv("MCP_HOST", "0.0.0.0")
        mcp.settings.port = int(os.getenv("MCP_PORT", "8001"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run(transport="stdio")
