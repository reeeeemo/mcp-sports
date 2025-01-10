from enum import Enum
from dataclasses import dataclass
from typing import Dict

class SupportedSports(str, Enum):
    NFL = "nfl"
    
def get_supported_sports_string() -> str:
        return ', '.join([s.value for s in SupportedSports])

@dataclass
class Sport:
    name: SupportedSports
    supported_langs: list[str]
    api_ver: str
    official: bool
    
    def __init__(self, name: str = SupportedSports.NFL, supported_langs: list[str] = [], api_ver: str = "v7", official: bool = True):
        self.name = SupportedSports(name)
        self.langs = supported_langs
        self.ver = api_ver
        self.official = official
        
# API versions, since there is no dynamic way to call this :,)
sports: Dict[SupportedSports, Sport] = {
    SupportedSports.NFL: Sport(SupportedSports.NFL, ["br", "da", "de", "en", "es", "fi", "fr", "it", "ja", "nl", "no", "se", "tr"], "v7", official=True)
}