import os
from typing import Dict, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings and configuration"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    
    # Database Configuration
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        # Default to SQLite for local development
        DATABASE_URL = 'sqlite:///chief_of_staff.db'
    else:
        # Handle Heroku PostgreSQL URL format
        if DATABASE_URL.startswith('postgres://'):
            DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
    GOOGLE_REDIRECT_URI = os.getenv('GOOGLE_REDIRECT_URI', 'http://localhost:5000/auth/callback')
    
    # Gmail API Configuration
    GMAIL_SCOPES = [
        'openid',
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/calendar.readonly',
        'https://www.googleapis.com/auth/userinfo.email',
        'https://www.googleapis.com/auth/userinfo.profile'
    ]
    
    # Claude/Anthropic Configuration
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    CLAUDE_MODEL = "claude-3-5-sonnet-20241022"
    
    # Email Processing Configuration
    EMAIL_FETCH_LIMIT = int(os.getenv('EMAIL_FETCH_LIMIT', 50))
    EMAIL_DAYS_BACK = int(os.getenv('EMAIL_DAYS_BACK', 30))
    EMAIL_BATCH_SIZE = int(os.getenv('EMAIL_BATCH_SIZE', 10))
    
    # Multi-tenant Configuration
    MAX_USERS_PER_INSTANCE = int(os.getenv('MAX_USERS_PER_INSTANCE', 1000))
    USER_DATA_RETENTION_DAYS = int(os.getenv('USER_DATA_RETENTION_DAYS', 365))
    
    # Application Settings
    HOST: str = os.getenv('HOST', '0.0.0.0')
    
    # Google OAuth & APIs
    OPENAI_API_KEY: str = os.getenv('OPENAI_API_KEY', '')
    OPENAI_REDIRECT_URI: str = os.getenv('OPENAI_REDIRECT_URI', 'http://localhost:5000/auth/openai/callback')
    
    # Calendar API Settings
    CALENDAR_SCOPES = [
        'https://www.googleapis.com/auth/calendar.readonly'
    ]
    
    # AI & Language Models
    OPENAI_MODEL: str = os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    
    # Redis Settings (for Celery)
    REDIS_URL: str = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # Vector Database Settings
    VECTOR_DB_TYPE: str = os.getenv('VECTOR_DB_TYPE', 'faiss')  # faiss, weaviate, qdrant
    VECTOR_DB_PATH: str = os.getenv('VECTOR_DB_PATH', 'data/vector_store')
    EMBEDDING_MODEL: str = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L6-v2')
    
    # Email Processing Settings
    EMAIL_FETCH_LIMIT: int = int(os.getenv('EMAIL_FETCH_LIMIT', '50'))
    EMAIL_DAYS_BACK: int = int(os.getenv('EMAIL_DAYS_BACK', '30'))
    EMAIL_BATCH_SIZE: int = int(os.getenv('EMAIL_BATCH_SIZE', '10'))
    
    # Task Extraction Settings
    TASK_EXTRACTION_PROMPT_VERSION: str = os.getenv('TASK_EXTRACTION_PROMPT_VERSION', 'v1')
    ENABLE_AUTO_TASK_EXTRACTION: bool = os.getenv('ENABLE_AUTO_TASK_EXTRACTION', 'True').lower() == 'true'
    
    # Memory & Context Settings
    MAX_CONVERSATION_HISTORY: int = int(os.getenv('MAX_CONVERSATION_HISTORY', '20'))
    CONTEXT_WINDOW_SIZE: int = int(os.getenv('CONTEXT_WINDOW_SIZE', '8000'))
    
    # Security Settings
    SESSION_TIMEOUT_HOURS: int = int(os.getenv('SESSION_TIMEOUT_HOURS', '24'))
    ENABLE_OFFLINE_MODE: bool = os.getenv('ENABLE_OFFLINE_MODE', 'False').lower() == 'true'
    
    # Logging Settings
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE: str = os.getenv('LOG_FILE', 'logs/chief_of_staff.log')
    
    # File Storage Settings
    UPLOAD_FOLDER: str = os.getenv('UPLOAD_FOLDER', 'data/uploads')
    MAX_UPLOAD_SIZE: int = int(os.getenv('MAX_UPLOAD_SIZE', '16777216'))  # 16MB
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx', 'doc', 'md'}
    
    @classmethod
    def validate_config(cls) -> List[str]:
        """
        Validate required configuration settings
        
        Returns:
            List of missing or invalid configuration items
        """
        errors = []
        
        # Required settings
        required_settings = [
            ('GOOGLE_CLIENT_ID', cls.GOOGLE_CLIENT_ID),
            ('GOOGLE_CLIENT_SECRET', cls.GOOGLE_CLIENT_SECRET),
            ('ANTHROPIC_API_KEY', cls.ANTHROPIC_API_KEY)
        ]
        
        for setting_name, setting_value in required_settings:
            if not setting_value:
                errors.append(f"Missing required setting: {setting_name}")
        
        # Validate database URL
        if not cls.DATABASE_URL:
            errors.append("DATABASE_URL is required")
        
        return errors
    
    @classmethod
    def get_gmail_auth_config(cls) -> Dict:
        """
        Get Gmail OAuth configuration for Google Auth library
        
        Returns:
            Dictionary with OAuth configuration
        """
        return {
            "web": {
                "client_id": cls.GOOGLE_CLIENT_ID,
                "client_secret": cls.GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                "redirect_uris": [cls.GOOGLE_REDIRECT_URI]
            }
        }
    
    @classmethod
    def is_production(cls) -> bool:
        """Check if running in production environment"""
        return cls.FLASK_ENV == 'production' or 'heroku' in cls.DATABASE_URL.lower()
    
    @classmethod
    def is_heroku(cls) -> bool:
        """Check if running on Heroku"""
        return bool(os.getenv('DYNO'))
    
    @classmethod
    def create_directories(cls):
        """Create necessary directories"""
        directories = [
            'data',
            'data/uploads',
            'data/vector_store',
            'logs',
            'tests/data'
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

# Initialize settings instance
settings = Settings()

# Validate required settings on import
try:
    settings.validate_config()
except ValueError as e:
    print(f"Configuration Error: {e}")
    print("Please check your .env file and ensure all required variables are set.")