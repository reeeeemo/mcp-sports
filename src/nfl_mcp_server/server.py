import asyncio
from dataclasses import dataclass
from typing import Literal
import json
import argparse
from dataclasses import dataclass
from fastmcp import FastMCP
from enum import Enum
import requests
import logging

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sports-mcp-server")

# Init our MCP server
mcp = FastMCP("sports")

'''
    SPORTSRADAR API CONSTANTS
'''
class Sport:
    def __init__(self, name: str = "nfl", supported_langs: list = [], api_ver: str = "v7"):
        self.name = name
        self.langs = supported_langs
        self.ver = api_ver
        

# API versions, since there is no dynamic way to call this :,)
mcp.sports = {
    "nfl": Sport("nfl", ["br", "da", "de", "en", "es", "fi", "fr", "it", "ja", "nl", "no", "se", "tr"], "v7"),
    "nba": Sport("nba", ["br", "en", "es", "fr", "ru", "zh"], "v8"),
    "nhl": Sport("nhl", ["br", "en", "es", "fr", "ru", "zh"], "v7"),
    "mlb": Sport("mlb", ["en"], "v7"),
    "ncaafb": Sport("ncaafb", ["en"], "v7"),
}
        
@dataclass
class SportRadarConfig:
    format: Literal["json", "xml"] = "json"
    access_level: Literal["trial", "production"] = "trial"
    cur_lang: str = "en"
    
    def get_base_url(self, sport_name: str = "") -> str:
        sport = mcp.sports.get(sport_name)
        if sport is None:
            return f"Sport {sport} was not in list of supported sports or is unavailable on SportsRadar. Contact developer for additions"
        
        if sport.name in ["nfl", "nhl", "mls", "g-league"]: # official leagues that support SportRadar
            return f"https://api.sportradar.com/{sport.name}/official/{self.access_level}/{sport.ver}/{self.cur_lang}"
        return f"https://api.sportradar.com/{sport.name}/{self.access_level}/{sport.ver}/{self.cur_lang}"

mcp.config = SportRadarConfig()

'''
    TOOLS
'''
@mcp.tool()
async def update_api_config(language: str | None = None,
                            access_level: str | None = None,
                            format: str | None = None) -> str:
    '''Update SportRadar's API config settings (language, trial or production api key, etc.)'''
    if language:
        mcp.config.cur_lang = language
    if access_level:
        mcp.config.access_level = access_level
    if format:
        mcp.config.format = format
        
    return f"""Updated Configs:
    Format: {mcp.config.format}
    Language: {mcp.config.cur_lang}
    Access Level: {mcp.config.access_level}
    Base URL (updated): {mcp.config.get_base_url()}"""

@mcp.tool()
async def get_season_schedule(sport: str = "nfl", schedule: Literal["current_season", "current_week"] = "current_season") -> str:
    '''Gets current schedule for the sport given (current week or current season)'''
    try:
        url = f"{mcp.config.get_base_url(sport)}/games/{schedule}/schedule.{mcp.config.format}"
        params = {"api_key": mcp.api_key}
        headers = {"accept": "application/json"}
        
        logger.info(f"Requesting URL {url}")
        logger.info(f"API_KEY: {params}")
        
        response = requests.get(url, params=params, headers=headers)
        logger.info(f"Response Status Code: {response.status_code}")
        
        if not response.ok:
            return f"API request failed with status {response.status_code}: {response.text}"
        
        data = response.json()
        logger.info(f"Response Data: {json.dumps(data, indent=2)}")

        return json.dumps(data, indent=2)
    except Exception as e:
        logger.error(f"Error getting schedule: {str(e)}")
        return f'Error getting schedule: {str(e)}'

@mcp.tool()
async def get_daily_transactions(year: int, month: int, day: int, sport: str = "nfl"):
    '''Gets info on transactions done in sports teams throughout the year. '''
    pass

'''
    RESOURCES
'''


'''
    MAIN SERVER CODE
'''
async def serve(api_key: str | None = None) -> None:
    if not api_key:
        raise ValueError("API_KEY is required.")
    # Run MCP Server
    mcp.api_key = api_key
    await mcp.run_stdio_async()
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser( description='Provide accurate and up-to-date sports stats via SportRadar' ) 
    parser.add_argument( '--api-key', type=str, required=True, help='API Key for SportRadar' )
    
    args = parser.parse_args()
    
    # Pass API key to our server func
    asyncio.run(serve(args.api_key))