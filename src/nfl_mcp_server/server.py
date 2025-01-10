import asyncio
from calendar import month
from dataclasses import dataclass, field
from typing import Annotated, Literal, Dict
import json
import argparse
from fastmcp import FastMCP
import requests
import logging
from geopy.geocoders import Nominatim
from sportsclasses import SupportedSports, Sport, get_supported_sports_string, sports
from pydantic import Field

# Logging config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sports-mcp-server")

# Init our MCP server
mcp = FastMCP("sports")

'''
    SPORTSRADAR API CONSTANTS
'''

mcp.sports = sports
        
@dataclass
class SportRadarConfig:
    format: Literal["json", "xml"] = "json"
    access_level: Literal["trial", "production"] = "trial"
    cur_lang: str = "en"
    
    def get_base_url(self, sport_name: SupportedSports) -> str:
        sport = mcp.sports.get(sport_name)
        if sport is None:
            return f"Sport {sport} was not in list of supported sports or is unavailable on SportsRadar. Contact developer for additions"
        
        if sport.name in [SupportedSports.NFL]: # official leagues that support SportRadar
            return f"https://api.sportradar.com/{sport.name.value}/official/{self.access_level}/{sport.ver}/{self.cur_lang}"
        return f"https://api.sportradar.com/{sport.name.value}/{self.access_level}/{sport.ver}/{self.cur_lang}"
    

mcp.config = SportRadarConfig()

'''
    RESOURCES
'''

@mcp.resource("sports://seasonsched/{_cache}")
@dataclass
class SeasonSchedule:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_schedule(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a schedule from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_football_schedule,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
        
    def parse_football_schedule(self, data: dict) -> dict:
        sched_id = data.get('season').get('id')
        if sched_id in self._cache:
            return self._cache[sched_id]

        weeks = []
        
        season = {
            'id': data.get('season').get('id'),
            'year': data.get('season').get('year'),
            'weeks': weeks
        }
        
        for week in data.get('weeks', []):
            games = []
            if week.get('games'):
                for game in week.get('games'):
                    venue = game.get('venue', {})
                    location = venue.get('location', {})
                    
                    temp_game = {
                        'id': game.get('id'),
                        'date': game.get('scheduled'),
                        'location': {
                            'lat': location.get('lat'),
                            'lng': location.get('lng')
                        },
                        'stadium': venue.get('name'),
                        'home_team': game.get('home', {}).get('name'),
                        'away_team': game.get('away', {}).get('name'),
                        'score_home': game.get('scoring', {}).get('home_points'),
                        'score_away': game.get('scoring', {}).get('away_points')
                    }
                    games.append(temp_game)

                temp_week = {
                    'id': week.get('id'),
                    'num': week.get('sequence'),
                    'games': games
                }
                weeks.append(temp_week)
        
        self._cache[sched_id] = season
        return season
    
mcp.season_schedule = SeasonSchedule()

@mcp.resource("sports://transactions/{_cache}")
@dataclass
class LeagueTransactions:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_transactions(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a transaction list from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_nfl_transactions,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
    
    def parse_nfl_transactions(self, data: dict) -> dict:
        transaction_id = data.get('league').get('id') + data.get('start_time') + data.get('end_time')
        if transaction_id in self._cache:
            return self._cache[transaction_id]
        
        players = []

        league = {
            'id': transaction_id,
            'name': data.get('league').get('name'),
            'start_time': data.get('start_time'),
            'end_time': data.get('end_time'),
            'players': players
        }
        
        if not data.get('players'):
            return 'No transactions done on this day.'
        
        for plr in data.get('players'):
            transactions = []
            player = {
                'name': plr.get('name'),
                'position': plr.get('position'),
                'transactions': transactions
            }
            for transaction in plr.get('transactions'):
                recieving_team = transaction.get('to_team')
                ta_temp = {
                    'transaction': transaction.get('desc'),
                    'effective': transaction.get('effective_date'),
                    'status_before': transaction.get('status_before'),
                    'recieving_team': recieving_team.get('market') + " " + recieving_team.get('name')
                }
                transactions.append(ta_temp)
            players.append(player)
            
        self._cache[transaction_id] = league
        return league
    
mcp.league_transactions = LeagueTransactions()
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
    Base URL (updated): {mcp.config.get_base_url(SupportedSports.NFL)}"""

@mcp.tool()
async def get_season_schedule(week: Annotated[int, Field(description="Week schedule for sport. 1 (NO 0 WEEK) (September) - 18 (January) weeks for the season. 5 Playoff weeks after.)")] = 0, 
                              sport: Annotated[str, Field(description=f"Sport to get schedule for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets current schedule for the sport given. 
    Args:
        sport: Sport to get schedule for.
        week: Week of the sport to get 
            - NFL: 1 (September) - 18 (January) weeks for the season. 5 Playoff weeks after
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        url = f"{mcp.config.get_base_url(sport_enum)}/games/current_season/schedule.{mcp.config.format}"
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

        parsed_data = mcp.season_schedule.parse_schedule(data, sport_enum)
        parsed_data = [week_val for week_val in parsed_data.get('weeks') if week_val.get('num') == week]
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f"Error getting schedule: {str(e)}")
        return f'Error getting schedule: {str(e)}'

@mcp.tool()
async def get_daily_transactions(year: int, 
                                 month: int, 
                                 day: int, 
                                 sport: Annotated[str, Field(description=f"Sport to get schedule for. Supported vals: {get_supported_sports_string()}")] = "nfl"):
    '''Gets info on transactions done in sports teams throughout the year. 
    Args:
        year: Year to get transactions for
        month: Month to get transactions for
        day: Day to get transactions for
        sport: Sport to get transactions for.'''
    try:    
        sport_enum = SupportedSports(sport.lower())
        url = f"{mcp.config.get_base_url(sport_enum)}/league/{year}/{month}/{day}/transactions.{mcp.config.format}"
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
        
        parsed_data = mcp.league_transactions.parse_transactions(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f"Error getting schedule: {str(e)}")
        return f'Error getting schedule: {str(e)}'

@mcp.tool()
async def get_address(lat: float, lon: float) -> str:
    '''When given coordinates (latitude and longitude), find the address
    '''
    geolocator = Nominatim(user_agent='sports-mcp-server')
    location = geolocator.reverse((lat, lon))
    return location.address

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