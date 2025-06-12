# Enhanced API Package - Entity-Centric API Layer
# This package provides modern, efficient API endpoints that leverage the enhanced processor architecture

__version__ = '2.0.0'
__description__ = 'Enhanced AI Chief of Staff API with entity-centric processing'

# Export main API components
from .enhanced_endpoints import enhanced_api_bp
from .realtime_endpoints import realtime_api_bp
from .analytics_endpoints import analytics_api_bp
from .entity_endpoints import entity_api_bp

__all__ = [
    'enhanced_api_bp',
    'realtime_api_bp', 
    'analytics_api_bp',
    'entity_api_bp'
] 