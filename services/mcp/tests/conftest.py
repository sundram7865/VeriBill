import sys
from pathlib import Path

# The MCP package lives in services/mcp; make it importable without installing it.
MCP_DIR = Path(__file__).resolve().parent.parent
if str(MCP_DIR) not in sys.path:
    sys.path.insert(0, str(MCP_DIR))
