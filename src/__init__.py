"""Productivity Music MCP Server — GLM 5.1 DJ-managed, multi-source audio plugin."""


def main():
    from .server import mcp
    mcp.run()
