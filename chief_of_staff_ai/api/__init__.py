# Enhanced API Package - Entity-Centric API Layer
# This package provides modern, efficient API endpoints that leverage the enhanced processor architecture

__version__ = '2.0.0'
__description__ = 'Enhanced AI Chief of Staff API with entity-centric processing'

# Export main API components - only the ones that exist
from .enhanced_endpoints import enhanced_api_bp

__all__ = [
    'enhanced_api_bp'
] 