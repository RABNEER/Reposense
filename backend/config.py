"""
Configuration management for RepoSense backend
Loads and validates all environment variables
"""
import os
from typing import Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class ConfigError(Exception):
    """Raised when required configuration is missing"""
    pass


class Config:
    """Application configuration"""
    
    # IBM Bob API Configuration
    IBM_BOB_API_KEY: str = os.getenv("IBM_BOB_API_KEY", "")
    IBM_BOB_BASE_URL: str = os.getenv("IBM_BOB_BASE_URL", "https://api.ibm.com/bob/v1")
    IBM_BOB_API_URL: str = os.getenv("IBM_BOB_API_URL", os.getenv("IBM_BOB_BASE_URL", "https://api.ibm.com/bob/v1"))
    IBM_BOB_TIMEOUT: float = float(os.getenv("IBM_BOB_TIMEOUT", "60"))
    IBM_BOB_MAX_RETRIES: int = int(os.getenv("IBM_BOB_MAX_RETRIES", "3"))
    
    # GitHub API Configuration
    GITHUB_TOKEN: Optional[str] = os.getenv("GITHUB_TOKEN")
    
    # Repository Analysis Limits
    MAX_FILES_TO_READ: int = int(os.getenv("MAX_FILES_TO_READ", "50"))
    MAX_FILE_SIZE_KB: int = int(os.getenv("MAX_FILE_SIZE_KB", "100"))
    
    # CORS Configuration
    ALLOWED_ORIGINS: list[str] = os.getenv(
        "ALLOWED_ORIGINS", 
        "http://localhost:3000,http://localhost:5173"
    ).split(",")
    CORS_ORIGINS: list[str] = ALLOWED_ORIGINS
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info").upper()
    
    # Application Metadata
    APP_NAME: str = "RepoSense"
    APP_VERSION: str = "1.0.0"
    
    @classmethod
    def validate(cls) -> None:
        """
        Validate that all required configuration is present
        Raises ConfigError if critical configuration is missing
        """
        if not cls.IBM_BOB_API_KEY:
            raise ConfigError(
                "IBM_BOB_API_KEY environment variable is required. "
                "Set it in your .env file or use 'mock' for development."
            )
        
        if cls.IBM_BOB_API_KEY != "mock" and not cls.IBM_BOB_BASE_URL:
            raise ConfigError(
                "IBM_BOB_BASE_URL environment variable is required when using real API key"
            )
        
        if cls.MAX_FILES_TO_READ < 1:
            raise ConfigError("MAX_FILES_TO_READ must be at least 1")
        
        if cls.MAX_FILE_SIZE_KB < 1:
            raise ConfigError("MAX_FILE_SIZE_KB must be at least 1")
        
        if cls.LOG_LEVEL not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ConfigError(
                f"Invalid LOG_LEVEL: {cls.LOG_LEVEL}. "
                "Must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL"
            )
    
    @classmethod
    def is_mock_mode(cls) -> bool:
        """Check if running in mock mode (no real IBM Bob API calls)"""
        return cls.IBM_BOB_API_KEY == "mock"
    
    @classmethod
    def get_github_headers(cls) -> dict[str, str]:
        """Get headers for GitHub API requests"""
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": f"{cls.APP_NAME}/{cls.APP_VERSION}"
        }
        
        if cls.GITHUB_TOKEN:
            headers["Authorization"] = f"token {cls.GITHUB_TOKEN}"
        
        return headers


# Validate configuration on import
try:
    Config.validate()
except ConfigError as e:
    print(f"❌ Configuration Error: {e}")
    print("Please check your .env file and ensure all required variables are set.")
    raise

# Made with Bob
