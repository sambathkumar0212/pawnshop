import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    """Load the appropriate environment file based on DJANGO_ENV."""
    env = os.getenv('DJANGO_ENV', 'development')
    env_file = f'.env.{env}'
    env_path = Path(__file__).resolve().parent / env_file
    
    if not env_path.exists():
        raise FileNotFoundError(f"Environment file {env_file} not found")
    
    load_dotenv(env_path)
    print(f"Loaded environment from {env_file}")
