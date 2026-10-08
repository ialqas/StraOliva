import os

from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

from .tools import assessment, plan, predictions, state, workouts

# The HTTP transport's DNS-rebinding protection only accepts Host headers for
# localhost by default, so clients reaching the server via its LAN IP get
# "421 Invalid Host header". MCP_ALLOWED_HOSTS adds extra hosts (comma-separated,
# e.g. "192.168.178.50:*,straoliva.local:*"), or "*" to disable the check.
_LOCAL_HOSTS = ["127.0.0.1:*", "localhost:*", "[::1]:*"]
_extra_hosts = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]

if _extra_hosts == ["*"]:
    _transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
else:
    _hosts = _LOCAL_HOSTS + _extra_hosts
    _transport_security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=_hosts,
        allowed_origins=[f"http://{h}" for h in _hosts],
    )

mcp = FastMCP("straoliva", transport_security=_transport_security)

state.register(mcp)
workouts.register(mcp)
predictions.register(mcp)
plan.register(mcp)
assessment.register(mcp)

if __name__ == "__main__":
    mcp.run(transport="stdio")
