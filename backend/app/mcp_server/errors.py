class MCPToolError(Exception):
    """Raised by MCP tools for validation/user errors.

    FastMCP renders the exception message back to the caller, so messages
    must be human-readable and explain: what went wrong, why, and what
    input would be valid.
    """
