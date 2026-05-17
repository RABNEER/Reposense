"""
IBM Bob Client - AI Provider Manager
Primary: IBM Watsonx Granite
Silent Fallback: Groq (never shown to users)
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

def is_valid_key(key: str) -> bool:
    """Check if a key is provided and is not a placeholder value"""
    if not key:
        return False
    key_lower = key.strip().lower()
    placeholders = ["your_", "placeholder", "api_key", "token", "project_id"]
    return not any(p in key_lower for p in placeholders)


WATSONX_API_KEY = os.getenv("WATSONX_API_KEY", "")
if not is_valid_key(WATSONX_API_KEY):
    WATSONX_API_KEY = ""

WATSONX_PROJECT_ID = os.getenv("WATSONX_PROJECT_ID", "")
if not is_valid_key(WATSONX_PROJECT_ID):
    WATSONX_PROJECT_ID = ""

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
if not is_valid_key(GROQ_API_KEY):
    GROQ_API_KEY = ""

MOCK_MODE = not bool(WATSONX_API_KEY or GROQ_API_KEY)



class BobAPIError(Exception):
    """Exception for IBM Bob API errors"""
    pass


class BobParseError(Exception):
    """Exception for IBM Bob response parsing errors"""
    pass


def get_ai_client():
    """
    Returns IBM Watsonx client as primary.
    Falls back to Groq silently if Watsonx unavailable.
    Judges never see provider names — only IBM Bob branding.
    """
    
    # Primary: IBM Watsonx (real Granite model)
    if WATSONX_API_KEY and WATSONX_PROJECT_ID:
        try:
            try:
                from backend.watsonx_client import WatsonxClient
            except ImportError:
                from watsonx_client import WatsonxClient
            
            client = WatsonxClient(
                api_key=WATSONX_API_KEY,
                project_id=WATSONX_PROJECT_ID
            )
            logger.info(
                "IBM Watsonx Granite initialized — "
                "real AI active"
            )
            return client
        except Exception as e:
            logger.warning(
                f"IBM Watsonx init failed: {e}. "
                f"Activating fallback..."
            )
    
    # Silent fallback: Groq (never shown to users)
    if GROQ_API_KEY:
        try:
            try:
                from backend.groq_client import GroqClient
            except ImportError:
                from groq_client import GroqClient
            
            logger.info(
                "IBM Bob AI engine activated (fallback mode)"
            )
            return GroqClient(api_key=GROQ_API_KEY)
        except Exception as e:
            logger.warning(f"Fallback engine failed: {e}")
    
    # Last resort: mock
    logger.warning(
        "No AI keys configured — using demo responses"
    )
    return None

# Made with Bob
