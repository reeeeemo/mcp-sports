# Sports MCP Server
[![MIT licensed][mit-badge]][mit-url]
[![Python Version][python-badge]][python-url]
[![PyPI version][pypi-badge]][pypi-url]

[mit-badge]: https://img.shields.io/pypi/l/mcp.svg
[mit-url]: https://github.com/reeeeemo/mcp-sports/blob/main/LICENSE
[python-badge]: https://img.shields.io/pypi/pyversions/mcp.svg
[python-url]: https://www.python.org/downloads/
[pypi-badge]: https://badge.fury.io/py/mcp-sports-server.svg
[pypi-url]: https://pypi.org/project/mcp-sports-server


<strong>Built on top of the [Model Context Protocol Python SDK](https://modelcontextprotocol.io)</strong>

## Overview
Python server implementing Model Context Protocol (MCP) for interactability with real-time sports stats via [**SportRadar**](https://sportradar.com/)

## Supported Sports
- NFL

**Note:** Please check **Development** for adding more sport support

## Features
- Get game, league and player stats
- Get team rosters and schedules
- Get tournament info and player transactions

**Note:** The server will need an API key from SportRadar. [Here is the instruction link](https://developer.sportradar.com/football/docs/football-ig-account-setup)

## Resources
- `sports://seasonsched/{_cache}`: Season schedule cache
- `sports://leaguetransactions/{_cache}`: League transactions cache / parser
- `sports://gamestats/{_cache}`: Game stats cache
- `sports://leaguestats/{_cache}`: League stats cache
- `sports://teamstats/{_cache}`: Team stats cache
- `sports://playerstats/{_cache}`: Player stats cache

## Tools

- **update_api_config**
    - Update SportRadar's API configuration settings 
    - Args
        - language (str)
        - access_level (str) -> trial or production api key
        - format (str) -> data return format (JSON or XML)
- **get_schedule**
    - Gets a specific week schedule for the sport given
    - Args
        - sport (str) 
        - week (int)
        - type (str) -> type of season (PRE, REG, PST)
        - year (int)
- **get_daily_transactions**
    - Gets info on transactions done in sports teams throughout the year
    - Args
        - year (int)
        - month (int)
        - day (int)
        - sport (str)
- **get_game_stats**
    - Gets statistical info on a specific sports game using it's ID
    - Args
        - game_id (str)
        - sport (str)
- **get_league_info**
    - Gets top-level info about each team in the sport provided
    - Args
        - sport (str)
- **get_team_roster**
    - Gets franchise team info + complete roster of players in the sport provided
    - Args
        - team_id (str)
        - sport (str)
- **get_tournament_list**
    - Gets lists of tournaments that are happening for the sport in that year
    - Args
        - sport (str)
        - year (int)
- **get_tournament_info**
    - Gets information of a tournament that is happening for the sport
    - Args
        - tournament_id (str)
        - sport (str)
- **get_player_stats**
    - Gets top-level info about each player in the sport provided
    - Args
        - sport (str)
        - player_id (str)
- **get_address**
    - When given coordinates (lat and lon), find the address
    - Args
        - lat (float)
        - lon (float)


## Usage with Claude Desktop

### Installing Manually
1. First, install the package:
```pip install mcp-sports-server```


2. Add this to your `claude_desktop_config.json` 

```json
{
  "mcpServers": {
     "sports": {
       "command": "mcp-sports-server",
       "args": ["--api-key", "your_api_key"]
     }
  }
}
```
## Development
As currently there is only NFL support. If there is enough interest more sports will be added.

If you want to create your own sport support, you can fork this repo and either make your own MCP server, or push changes to this current server.

Most of the code inside has DOCTYPE comments about how to add a new sport, essentially to add a new sport:
1. Create a new Sport inside of `sportsclasses.py`
2. Update MCP Resources *(more specifically the `parser_map` to include your sport parsing function)*
3. Update MCP Tools as needed *(you will need to update the Annotated parameters in tools)*
## License

This project is licensed under the MIT License - see the LICENSE file for details.
