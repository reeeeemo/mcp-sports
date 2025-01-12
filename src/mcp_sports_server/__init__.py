import asyncio
import argparse
from .main import serve as async_serve


def serve():
    parser = argparse.ArgumentParser( description='Provide accurate and up-to-date sports stats via SportRadar' ) 
    parser.add_argument( '--api-key', type=str, required=True, help='API Key for SportRadar' )
    
    args = parser.parse_args()
    
    # Pass API key to our server func
    asyncio.run(async_serve(args.api_key))
    
__all__ = ['serve']
