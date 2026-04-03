"""Entry point for running the MCP server: python -m stratifyai.mcp_server"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="StratifyAI MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="MCP transport to use (default: stdio)",
    )
    args = parser.parse_args()

    from stratifyai.mcp_server.server import mcp

    mcp.run(transport=args.transport)


if __name__ == "__main__":
    main()
