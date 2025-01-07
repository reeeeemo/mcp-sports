import asyncio
import argparse
from fastmcp import FastMCP
from enum import Enum
import requests
import logging

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sports-mcp-server")

# Init our MCP server
mcp = FastMCP("sports")

# SportsRadar API constants
API_BASE = "https://api.sportradar.com/"

# Tool names
class AncestryTools(str, Enum):
    LIST_FILES = "list_files"
    RENAME_FILE = "rename_file"
    VIEW_FILES = "view_file"


'''
    MAIN SERVER CODE
'''
def serve(api_key: str | None = None) -> None:
    if not api_key:
        raise ValueError("API_KEY is required.")
    # Run MCP Server
    mcp.run()
    
async def main():
    parser = argparse.ArgumentParser( description='Provide accurate and up-to-date sports stats via SportRadar' ) 
    parser.add_argument( '--api-key', type=str, required=True, help='API Key for SportRadar' )
    
    args = parser.parse_args()
    
    # Pass API key to our server func
    serve(args.api_key)
    

if __name__ == "__main__":
    asyncio.run(main())