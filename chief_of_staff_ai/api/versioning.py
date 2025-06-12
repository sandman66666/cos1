# API Versioning and Backward Compatibility System
# This module provides comprehensive API versioning, deprecation management, and backward compatibility

import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timezone
from flask import Blueprint, request, jsonify, g
from functools import wraps
import json
import re
from packaging import version

logger = logging.getLogger(__name__)

# =====================================================================
# API VERSION CONFIGURATION
# =====================================================================

API_VERSIONS = {
    'v1': {
        'version': '1.0.0',
        'status': 'deprecated',
        'supported_until': '2024-12-31',
        'description': 'Legacy API endpoints',
        'prefix': '/api/v1',
        'features': ['basic_email_processing', 'task_extraction'],
        'deprecation_warnings': True
    },
    'v2': {
        'version': '2.0.0',
        'status': 'current',
        'supported_until': None,
        'description': 'Enhanced entity-centric API',
        'prefix': '/api/v2',
        'features': ['entity_processing', 'real_time', 'analytics', 'batch_processing'],
        'deprecation_warnings': False
    },
    'v3': {
        'version': '3.0.0',
        'status': 'beta',
        'supported_until': None,
        'description': 'Next-generation AI Chief of Staff API',
        'prefix': '/api/v3',
        'features': ['ai_agents', 'predictive_intelligence', 'auto_optimization'],
        'deprecation_warnings': False
    }
}

CURRENT_VERSION = 'v2'
DEFAULT_VERSION = 'v2'

# =====================================================================
# VERSION DETECTION AND VALIDATION
# =====================================================================

def get_api_version_from_request() -> str:
    """
    Determine API version from request headers or URL.
    Priority: Header > URL > Default
    """
    # Check for version in headers
    version_header = request.headers.get('API-Version', '').strip()
    if version_header and version_header in API_VERSIONS:
        return version_header
    
    # Check for version in Accept header
    accept_header = request.headers.get('Accept', '')
    version_match = re.search(r'application/vnd\.chief-of-staff\.v(\d+)', accept_header)
    if version_match:
        api_version = f"v{version_match.group(1)}"
        if api_version in API_VERSIONS:
            return api_version
    
    # Check URL path for version
    path = request.path
    version_match = re.search(r'/api/v(\d+)/', path)
    if version_match:
        api_version = f"v{version_match.group(1)}"
        if api_version in API_VERSIONS:
            return api_version
    
    # Default version
    return DEFAULT_VERSION

def validate_api_version(api_version: str) -> tuple[bool, Optional[str]]:
    """
    Validate if API version is supported.
    Returns (is_valid, error_message)
    """
    if api_version not in API_VERSIONS:
        return False, f"Unsupported API version: {api_version}. Supported versions: {', '.join(API_VERSIONS.keys())}"
    
    version_info = API_VERSIONS[api_version]
    
    if version_info['status'] == 'deprecated':
        # Check if still within support period
        if version_info.get('supported_until'):
            support_end = datetime.fromisoformat(version_info['supported_until'] + 'T23:59:59')
            if datetime.utcnow() > support_end:
                return False, f"API version {api_version} is no longer supported. Please upgrade to v{CURRENT_VERSION}."
    
    return True, None

def get_version_features(api_version: str) -> List[str]:
    """Get list of features available in the specified API version"""
    return API_VERSIONS.get(api_version, {}).get('features', [])

def is_feature_available(api_version: str, feature: str) -> bool:
    """Check if a feature is available in the specified API version"""
    return feature in get_version_features(api_version)

# =====================================================================
# VERSION DECORATORS
# =====================================================================

def api_version(min_version: str = None, max_version: str = None, 
                required_features: List[str] = None, deprecated_in: str = None):
    """
    Decorator to specify API version requirements for endpoints.
    
    Args:
        min_version: Minimum API version required
        max_version: Maximum API version supported
        required_features: List of features required for this endpoint
        deprecated_in: Version in which this endpoint was deprecated
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get and validate API version
            api_version = get_api_version_from_request()
            is_valid, error_msg = validate_api_version(api_version)
            
            if not is_valid:
                return jsonify({
                    'success': False,
                    'error': error_msg,
                    'code': 'UNSUPPORTED_API_VERSION',
                    'supported_versions': list(API_VERSIONS.keys()),
                    'current_version': CURRENT_VERSION
                }), 400
            
            # Check version range
            if min_version and version.parse(API_VERSIONS[api_version]['version']) < version.parse(API_VERSIONS[min_version]['version']):
                return jsonify({
                    'success': False,
                    'error': f"This endpoint requires API version {min_version} or higher",
                    'code': 'VERSION_TOO_LOW',
                    'current_request_version': api_version,
                    'minimum_required': min_version
                }), 400
            
            if max_version and version.parse(API_VERSIONS[api_version]['version']) > version.parse(API_VERSIONS[max_version]['version']):
                return jsonify({
                    'success': False,
                    'error': f"This endpoint is not available in API version {api_version}",
                    'code': 'VERSION_TOO_HIGH',
                    'current_request_version': api_version,
                    'maximum_supported': max_version
                }), 400
            
            # Check required features
            if required_features:
                available_features = get_version_features(api_version)
                missing_features = [f for f in required_features if f not in available_features]
                
                if missing_features:
                    return jsonify({
                        'success': False,
                        'error': f"Required features not available in {api_version}: {', '.join(missing_features)}",
                        'code': 'MISSING_FEATURES',
                        'required_features': required_features,
                        'available_features': available_features
                    }), 400
            
            # Store version info in g
            g.api_version = api_version
            g.api_version_info = API_VERSIONS[api_version]
            
            # Add deprecation warning if needed
            response_headers = {}
            if deprecated_in and version.parse(API_VERSIONS[api_version]['version']) >= version.parse(API_VERSIONS[deprecated_in]['version']):
                response_headers['Deprecation'] = 'true'
                response_headers['Sunset'] = API_VERSIONS[api_version].get('supported_until', 'TBD')
                response_headers['Link'] = f'</api/{CURRENT_VERSION}>; rel="successor-version"'
            
            # Execute the function
            result = f(*args, **kwargs)
            
            # Add version headers to response
            if isinstance(result, tuple) and len(result) == 2:
                response, status_code = result
                if hasattr(response, 'headers'):
                    for header, value in response_headers.items():
                        response.headers[header] = value
                    response.headers['API-Version'] = api_version
                    response.headers['API-Current-Version'] = CURRENT_VERSION
                return response, status_code
            
            return result
            
        return decorated_function
    return decorator

def requires_feature(feature_name: str):
    """Decorator to require a specific feature to be available in the API version"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_version = getattr(g, 'api_version', get_api_version_from_request())
            
            if not is_feature_available(api_version, feature_name):
                return jsonify({
                    'success': False,
                    'error': f"Feature '{feature_name}' is not available in API version {api_version}",
                    'code': 'FEATURE_NOT_AVAILABLE',
                    'required_feature': feature_name,
                    'available_features': get_version_features(api_version)
                }), 400
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def deprecated(since_version: str, remove_in_version: str = None, alternative: str = None):
    """
    Decorator to mark endpoints as deprecated.
    
    Args:
        since_version: Version when deprecation started
        remove_in_version: Version when endpoint will be removed
        alternative: Suggested alternative endpoint
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            api_version = getattr(g, 'api_version', get_api_version_from_request())
            
            # Add deprecation warning to response
            result = f(*args, **kwargs)
            
            deprecation_message = f"This endpoint is deprecated since API version {since_version}."
            if remove_in_version:
                deprecation_message += f" It will be removed in version {remove_in_version}."
            if alternative:
                deprecation_message += f" Please use {alternative} instead."
            
            # Handle different response types
            if isinstance(result, tuple) and len(result) == 2:
                response_data, status_code = result
                
                # Add deprecation info to JSON response
                if hasattr(response_data, 'get_json'):
                    json_data = response_data.get_json() or {}
                    if isinstance(json_data, dict):
                        json_data['deprecation_warning'] = deprecation_message
                        response_data.data = json.dumps(json_data)
                
                # Add deprecation headers
                if hasattr(response_data, 'headers'):
                    response_data.headers['Deprecation'] = 'true'
                    response_data.headers['Sunset'] = API_VERSIONS.get(remove_in_version, {}).get('supported_until', 'TBD')
                    if alternative:
                        response_data.headers['Link'] = f'<{alternative}>; rel="alternate"'
                
                return response_data, status_code
            
            return result
            
        return decorated_function
    return decorator

# =====================================================================
# BACKWARD COMPATIBILITY HANDLERS
# =====================================================================

class BackwardCompatibilityMapper:
    """Maps old API endpoints to new ones with data transformation"""
    
    def __init__(self):
        self.mappings = {}
        self.transformers = {}
    
    def register_mapping(self, old_endpoint: str, new_endpoint: str, 
                        request_transformer: Callable = None, 
                        response_transformer: Callable = None):
        """
        Register a mapping from old endpoint to new endpoint.
        
        Args:
            old_endpoint: Old API endpoint pattern
            new_endpoint: New API endpoint pattern
            request_transformer: Function to transform request data
            response_transformer: Function to transform response data
        """
        self.mappings[old_endpoint] = new_endpoint
        self.transformers[old_endpoint] = {
            'request': request_transformer,
            'response': response_transformer
        }
    
    def get_mapping(self, endpoint: str) -> Optional[Dict]:
        """Get mapping information for an endpoint"""
        for old_endpoint, new_endpoint in self.mappings.items():
            if re.match(old_endpoint.replace('*', '.*'), endpoint):
                return {
                    'new_endpoint': new_endpoint,
                    'transformers': self.transformers.get(old_endpoint, {})
                }
        return None

# Global compatibility mapper
compatibility_mapper = BackwardCompatibilityMapper()

# =====================================================================
# V1 TO V2 COMPATIBILITY MAPPINGS
# =====================================================================

def transform_v1_email_request(data: Dict) -> Dict:
    """Transform V1 email processing request to V2 format"""
    if not data:
        return data
    
    # V1 used 'email_content', V2 uses 'email_data'
    if 'email_content' in data:
        data['email_data'] = data.pop('email_content')
    
    # V1 used 'extract_tasks', V2 uses 'real_time'
    if 'extract_tasks' in data:
        data['real_time'] = data.pop('extract_tasks')
    
    # Add default V2 parameters
    data.setdefault('batch_size', 10)
    data.setdefault('legacy_mode', True)
    
    return data

def transform_v1_email_response(data: Dict) -> Dict:
    """Transform V2 email processing response to V1 format"""
    if not data or not isinstance(data, dict):
        return data
    
    # V1 expected simpler structure
    if 'result' in data and isinstance(data['result'], dict):
        result = data['result']
        
        # Extract key V1 fields
        v1_response = {
            'success': data.get('success', True),
            'processed_emails': result.get('total_processed', 0),
            'extracted_tasks': result.get('tasks_created', 0),
            'processing_time': result.get('total_processing_time', 0)
        }
        
        # Add tasks if available
        if 'tasks' in result:
            v1_response['tasks'] = result['tasks']
        
        return v1_response
    
    return data

def transform_v1_task_request(data: Dict) -> Dict:
    """Transform V1 task creation request to V2 format"""
    if not data:
        return data
    
    # V1 used 'task_text', V2 uses 'description'
    if 'task_text' in data:
        data['description'] = data.pop('task_text')
    
    # V1 used 'assigned_to', V2 uses 'assignee_email'
    if 'assigned_to' in data:
        data['assignee_email'] = data.pop('assigned_to')
    
    return data

# Register compatibility mappings
compatibility_mapper.register_mapping(
    r'/api/v1/process-email',
    '/api/v2/emails/process',
    request_transformer=transform_v1_email_request,
    response_transformer=transform_v1_email_response
)

compatibility_mapper.register_mapping(
    r'/api/v1/extract-tasks',
    '/api/v2/tasks/from-email',
    request_transformer=transform_v1_email_request,
    response_transformer=transform_v1_email_response
)

compatibility_mapper.register_mapping(
    r'/api/v1/create-task',
    '/api/v2/tasks',
    request_transformer=transform_v1_task_request
)

# =====================================================================
# VERSION MANAGEMENT ENDPOINTS
# =====================================================================

# Create versioning blueprint
versioning_bp = Blueprint('versioning', __name__, url_prefix='/api')

@versioning_bp.route('/versions', methods=['GET'])
def get_api_versions():
    """Get information about all available API versions"""
    try:
        versions_info = {}
        
        for version_key, version_data in API_VERSIONS.items():
            versions_info[version_key] = {
                'version': version_data['version'],
                'status': version_data['status'],
                'description': version_data['description'],
                'prefix': version_data['prefix'],
                'features': version_data['features'],
                'supported_until': version_data.get('supported_until'),
                'is_current': version_key == CURRENT_VERSION,
                'is_default': version_key == DEFAULT_VERSION
            }
        
        return jsonify({
            'success': True,
            'data': {
                'versions': versions_info,
                'current_version': CURRENT_VERSION,
                'default_version': DEFAULT_VERSION,
                'version_selection_methods': [
                    'Header: API-Version',
                    'Accept: application/vnd.chief-of-staff.v{N}+json',
                    'URL: /api/v{N}/'
                ]
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting API versions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@versioning_bp.route('/version', methods=['GET'])
def get_current_version():
    """Get current API version information"""
    try:
        api_version = get_api_version_from_request()
        version_info = API_VERSIONS.get(api_version, {})
        
        return jsonify({
            'success': True,
            'data': {
                'detected_version': api_version,
                'version_info': version_info,
                'current_version': CURRENT_VERSION,
                'is_deprecated': version_info.get('status') == 'deprecated',
                'features_available': version_info.get('features', [])
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting current version: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

@versioning_bp.route('/migration-guide', methods=['GET'])
def get_migration_guide():
    """Get migration guide for upgrading between API versions"""
    try:
        from_version = request.args.get('from', 'v1')
        to_version = request.args.get('to', CURRENT_VERSION)
        
        if from_version not in API_VERSIONS or to_version not in API_VERSIONS:
            return jsonify({
                'success': False,
                'error': 'Invalid version specified',
                'available_versions': list(API_VERSIONS.keys())
            }), 400
        
        migration_guide = {
            'from_version': from_version,
            'to_version': to_version,
            'breaking_changes': _get_breaking_changes(from_version, to_version),
            'new_features': _get_new_features(from_version, to_version),
            'deprecated_endpoints': _get_deprecated_endpoints(from_version),
            'endpoint_mappings': _get_endpoint_mappings(from_version, to_version),
            'migration_steps': _get_migration_steps(from_version, to_version)
        }
        
        return jsonify({
            'success': True,
            'data': migration_guide,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting migration guide: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat()
        }), 500

# =====================================================================
# MIGRATION GUIDE HELPERS
# =====================================================================

def _get_breaking_changes(from_version: str, to_version: str) -> List[Dict]:
    """Get list of breaking changes between versions"""
    breaking_changes = []
    
    if from_version == 'v1' and to_version in ['v2', 'v3']:
        breaking_changes.extend([
            {
                'type': 'request_format',
                'description': 'Email processing request format changed',
                'old_format': '{"email_content": "...", "extract_tasks": true}',
                'new_format': '{"email_data": "...", "real_time": true}',
                'impact': 'medium'
            },
            {
                'type': 'response_format',
                'description': 'Response structure is now more detailed',
                'old_format': '{"success": true, "tasks": [...]}',
                'new_format': '{"success": true, "data": {"result": {...}}}',
                'impact': 'high'
            },
            {
                'type': 'authentication',
                'description': 'JWT authentication now required for most endpoints',
                'old_format': 'Session-based authentication',
                'new_format': 'Bearer token in Authorization header',
                'impact': 'high'
            }
        ])
    
    return breaking_changes

def _get_new_features(from_version: str, to_version: str) -> List[Dict]:
    """Get list of new features available in target version"""
    new_features = []
    
    if from_version == 'v1' and to_version in ['v2', 'v3']:
        new_features.extend([
            {
                'feature': 'entity_processing',
                'description': 'Entity-centric processing with relationships',
                'endpoints': ['/api/v2/entities/*']
            },
            {
                'feature': 'real_time',
                'description': 'Real-time processing and WebSocket support',
                'endpoints': ['/api/realtime/*']
            },
            {
                'feature': 'analytics',
                'description': 'Comprehensive analytics and insights',
                'endpoints': ['/api/analytics/*']
            },
            {
                'feature': 'batch_processing',
                'description': 'Batch processing for high-volume operations',
                'endpoints': ['/api/batch/*']
            }
        ])
    
    return new_features

def _get_deprecated_endpoints(version: str) -> List[Dict]:
    """Get list of deprecated endpoints in the specified version"""
    deprecated = []
    
    if version == 'v1':
        deprecated.extend([
            {
                'endpoint': '/api/v1/process-email',
                'alternative': '/api/v2/emails/process',
                'removal_date': '2024-12-31'
            },
            {
                'endpoint': '/api/v1/extract-tasks',
                'alternative': '/api/v2/tasks/from-email',
                'removal_date': '2024-12-31'
            }
        ])
    
    return deprecated

def _get_endpoint_mappings(from_version: str, to_version: str) -> Dict:
    """Get endpoint mappings between versions"""
    mappings = {}
    
    if from_version == 'v1' and to_version == 'v2':
        mappings = {
            '/api/v1/process-email': '/api/v2/emails/process',
            '/api/v1/extract-tasks': '/api/v2/tasks/from-email',
            '/api/v1/create-task': '/api/v2/tasks',
            '/api/v1/get-tasks': '/api/v2/tasks',
            '/api/v1/health': '/api/v2/health'
        }
    
    return mappings

def _get_migration_steps(from_version: str, to_version: str) -> List[Dict]:
    """Get step-by-step migration instructions"""
    steps = []
    
    if from_version == 'v1' and to_version == 'v2':
        steps = [
            {
                'step': 1,
                'title': 'Update Authentication',
                'description': 'Implement JWT authentication using /api/auth/login',
                'code_example': 'Authorization: Bearer <jwt_token>'
            },
            {
                'step': 2,
                'title': 'Update Request Formats',
                'description': 'Change request field names according to breaking changes',
                'code_example': '{"email_data": "...", "real_time": true}'
            },
            {
                'step': 3,
                'title': 'Update Response Handling',
                'description': 'Handle new response structure with data wrapper',
                'code_example': 'response.data.result instead of response directly'
            },
            {
                'step': 4,
                'title': 'Leverage New Features',
                'description': 'Optionally integrate entity processing and analytics',
                'code_example': 'Use /api/v2/entities/* for relationship management'
            }
        ]
    
    return steps

# =====================================================================
# UTILITY FUNCTIONS
# =====================================================================

def add_version_headers(response, api_version: str = None):
    """Add version-related headers to response"""
    if api_version is None:
        api_version = get_api_version_from_request()
    
    if hasattr(response, 'headers'):
        response.headers['API-Version'] = api_version
        response.headers['API-Current-Version'] = CURRENT_VERSION
        response.headers['API-Supported-Versions'] = ', '.join(API_VERSIONS.keys())
        
        # Add deprecation warning if needed
        version_info = API_VERSIONS.get(api_version, {})
        if version_info.get('status') == 'deprecated':
            response.headers['Deprecation'] = 'true'
            if version_info.get('supported_until'):
                response.headers['Sunset'] = version_info['supported_until']
    
    return response

def get_version_from_url(url: str) -> Optional[str]:
    """Extract API version from URL"""
    match = re.search(r'/api/v(\d+)/', url)
    if match:
        return f"v{match.group(1)}"
    return None

# Export all components
__all__ = [
    'api_version',
    'requires_feature', 
    'deprecated',
    'get_api_version_from_request',
    'validate_api_version',
    'get_version_features',
    'is_feature_available',
    'compatibility_mapper',
    'versioning_bp',
    'add_version_headers',
    'API_VERSIONS',
    'CURRENT_VERSION'
] 