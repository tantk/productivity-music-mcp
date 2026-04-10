"""Productivity Music MCP Server — GLM 5.1 DJ-managed, multi-source audio plugin."""

from .server import mcp


def main():
    mcp.run()
