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
import time

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
    
    def get_data(self, sport_name: SupportedSports, sublink: str) -> str:
        base_url = self.get_base_url(sport_name)
        final_url = base_url + sublink
        params = {'api_key': mcp.api_key}
        headers = {'accept': 'application/json'}
        
        logger.info(f'Requesting URL {final_url}')
        logger.info(f'API_KEY: {params}')
        
        response = requests.get(final_url, params=params, headers=headers)
        time.sleep(1) # no too many request errors
        logger.info(f'Response Status Code {response.status_code}')
        
        if not response.ok:
            return f'API request failed with status {response.status_code}: {response.text}'
        
        data = response.json()
        logger.info(f'Response Data: {json.dumps(data, indent=2)}')
        
        return data

mcp.config = SportRadarConfig()

'''
    RESOURCES
    
    Note: anything with a JSON or XML over 100,000 lines should have a resource attached 
    (so it can get returned in chunks and cached for later use if needed)
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
        sched_id = data.get('id')
        if sched_id in self._cache:
            return self._cache[sched_id]
        
        self._cache[sched_id] = data
        return data
    
mcp.season_schedule = SeasonSchedule()

@mcp.resource("sports://leaguetransactions/{_cache}")
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

@mcp.resource("sports://gamestats/{_cache}")
@dataclass
class GameStats:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_stats(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a stats list from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_nfl_stats,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
    
    def parse_nfl_stats(self, data: dict) -> dict:
        stats_id = data.get('id')
        if stats_id in self._cache:
            return self._cache[stats_id]
        
        self._cache[stats_id] = data
        return data
        
 
mcp.game_stats = GameStats()

@mcp.resource("sports://leaguestats/{_cache}")
@dataclass
class LeagueStats:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_stats(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a league heirarchy from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_nfl_stats,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
    
    def parse_nfl_stats(self, data: dict) -> dict:
        stats_id = data.get('league').get('id')
        if stats_id in self._cache:
            return self._cache[stats_id]
        
        self._cache[stats_id] = data
        return data
   
mcp.league_stats = LeagueStats()

@mcp.resource("sports://teamstats/{_cache}")
@dataclass
class TeamStats:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_stats(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a list of team stats from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_nfl_stats,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
    
    def parse_nfl_stats(self, data: dict) -> dict:
        stats_id = data.get('id')
        if stats_id in self._cache:
            return self._cache[stats_id]
        
        self._cache[stats_id] = data
        return data
    
    
mcp.team_stats = TeamStats()

@mcp.resource("sports://teamstats/{_cache}")
@dataclass
class PlayerStats:
    _cache: dict = field(default_factory=dict)
    
    async def get(self, _cache: str) -> dict:
        if _cache in self._cache:
            return self._cache[_cache]
        return {}
    
    def parse_stats(self, data: dict, sport: SupportedSports) -> dict:
        '''
            When given a list of player stats from a sport to parse, give the correct parser to the correct sport
        '''
        parser_map = {
            SupportedSports.NFL: self.parse_nfl_stats,    
        }
        
        parser = parser_map.get(sport)
        if not parser:
            logger.error(f"No parser implemented for sport {sport}")
            raise ValueError(f"No parser implemented for sport: {sport}")
        
        return parser(data)
    
    def parse_nfl_stats(self, data: dict) -> dict:
        stats_id = data.get('id')
        if stats_id in self._cache:
            return self._cache[stats_id]
        
        self._cache[stats_id] = data
        return data

mcp.player_stats = PlayerStats()

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
async def get_schedule(week: Annotated[int, Field(description="Week schedule for sport. 1 (NO 0 WEEK) (September) - 18 (January) weeks for the season. Playoff resets to 1-4 weeks.)")] = 0,
                       type: Annotated[str, Field(description="Type of season, PRE (pre season), REG (regular season), PST (post season)")] = "REG",
                       year: Annotated[int, Field(description="Year of season")] = 2024,
                       sport: Annotated[str, Field(description=f"Sport to get schedule for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets a week schedule for the sport given. 
    Args:
        sport: Sport to get schedule for.
        week: Week of the sport to get 
            - NFL: 1 (September) - 18 (January) weeks for the season. 5 Playoff weeks after (1-4 weeks)
        type: Type of season (PRE, REG, PST)
        year: Year of season (2024, 2025, etc.)
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/games/{year}/{type}/{week}/schedule.{mcp.config.format}')
        parsed_data = mcp.season_schedule.parse_schedule(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f"Error getting schedule: {str(e)}")
        return f'Error getting schedule: {str(e)}'

@mcp.tool()
async def get_daily_transactions(year: int, 
                                 month: int, 
                                 day: int, 
                                 sport: Annotated[str, Field(description=f"Sport to get transactions for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets info on transactions done in sports teams throughout the year. 
    Args:
        year: Year to get transactions for
        month: Month to get transactions for
        day: Day to get transactions for
        sport: Sport to get transactions for.'''
    try:    
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/league/{year}/{month}/{day}/transactions.{mcp.config.format}')
        parsed_data = mcp.league_transactions.parse_transactions(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f"Error getting transactions: {str(e)}")
        return f'Error getting transactions: {str(e)}'

@mcp.tool()
async def get_game_stats(game_id: str, 
                         sport: Annotated[str, Field(description=f"Sport to get game stats for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets statistical info on a specific sports game using it's ID
    Args:
        game_id: ID for the game
        sport: Sport to get stats for
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/games/{game_id}/statistics.{mcp.config.format}')
        parsed_data = mcp.game_stats.parse_stats(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f"Error getting stats: {str(e)}")
        return f"Error getting stats: {str(e)}"
    
@mcp.tool()
async def get_league_info(sport: Annotated[str, Field(description=f"Sport to get league info for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets top-level info about each team in the sport provided
    Args:
        sport: Sport to get league info for
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/league/hierarchy.{mcp.config.format}')
        parsed_data = mcp.league_stats.parse_stats(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f'Error getting league info: {str(e)}')
        return f'Error getting league info: {str(e)}'

@mcp.tool()
async def get_team_roster(team_id: str = None, 
                          sport: Annotated[str, Field(description=f"Sport to get league info for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets franchise team info + complete roster of players in the sport provided
    Args:
        sport: Sport to get team roster for
        team_id: Team to get the roster + info for
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/teams/{team_id}/full_roster.{mcp.config.format}')
        parsed_data = mcp.team_stats.parse_stats(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f'Error getting team info: {str(e)}')
        return f'Error getting team info: {str(e)}'
    
@mcp.tool()
async def get_tournament_list(year: int, 
                              sport: Annotated[str, Field(description=f"Sport to get league info for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets lists of tournaments that are happening for the sport in that year
    Args:
        sport: Sport to get list of tournaments for
        year: Year of the tournament
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/tournaments/{year}/PST/schedule.{mcp.config.format}')
        return json.dump(data, indent=2)
    except Exception as e:
        logger.error(f'Error getting tournament info: {str(e)}')
        return f'Error getting tournament info: {str(e)}'
    
async def get_tournament_info(tournament_id: str = None, 
                              sport: Annotated[str, Field(description=f"Sport to get league info for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets information of a tournament that is happening for the sport
    Args:
        tournament_id: id of the tournament
        sport: Sport to get info of tournament from
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/tournaments/{tournament_id}/schedule.{mcp.config.format}')
        return json.dump(data, indent=2)
    except Exception as e:
        logger.error(f'Error getting tournament info: {str(e)}')
        return f'Error getting tournament info: {str(e)}'

@mcp.tool()
async def get_player_stats(player_id: str,
                           sport: Annotated[str, Field(description=f"Sport to get player info for. Supported vals: {get_supported_sports_string()}")] = "nfl") -> str:
    '''Gets top-level info about each player in the sport provided
    Args:
        sport: Sport to get league info for
        player_id: ID of the player that we are requesting info for
    '''
    try:
        sport_enum = SupportedSports(sport.lower())
        data = mcp.config.get_data(sport_enum, f'/players/{player_id}/profile.{mcp.config.format}')
        parsed_data = mcp.player_stats.parse_stats(data, sport_enum)
        return json.dumps(parsed_data, indent=2)
    except Exception as e:
        logger.error(f'Error getting league info: {str(e)}')
        return f'Error getting league info: {str(e)}'

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