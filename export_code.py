#!/usr/bin/env python3
"""
Code Export Script for AI Chief of Staff
Exports all code to opus.txt with full content for app-specific files
and brief descriptions for standard/mundane files.
"""

import os
import datetime
from pathlib import Path

def is_app_specific_file(file_path):
    """Determine if a file is app-specific and should have full content exported"""
    
    # Files that should have full content (app-specific)
    app_specific_patterns = [
        'main.py',
        'config/settings.py',
        'auth/gmail_auth.py',
        'models/database.py',
        'processors/email_quality_filter.py',
        'engagement_analysis/smart_contact_strategy.py',
        'agents/',
        'api/routes/',
        'processors/',
        'auth/',
        'engagement_analysis/',
        'intelligence/',
        'calendar_integration/',
        'Claude_workers.txt'
    ]
    
    # File extensions that are typically app-specific
    app_specific_extensions = ['.py', '.txt', '.md', '.json', '.env']
    
    # Skip these mundane files
    skip_patterns = [
        '__pycache__',
        '.git',
        '.pyc',
        'node_modules',
        '.DS_Store',
        'flask.log',
        '.sqlite',
        '__init__.py',  # Usually just package markers
        'requirements.txt'  # Standard dependency file
    ]
    
    file_str = str(file_path)
    
    # Skip patterns
    for pattern in skip_patterns:
        if pattern in file_str:
            return False
    
    # Check if it matches app-specific patterns
    for pattern in app_specific_patterns:
        if pattern in file_str:
            return True
    
    # Check extension
    if file_path.suffix in app_specific_extensions:
        return True
    
    return False

def get_file_description(file_path):
    """Get a brief description for mundane files"""
    
    descriptions = {
        '__init__.py': 'Package initialization file',
        'requirements.txt': 'Python dependencies list',
        '.gitignore': 'Git ignore patterns',
        'README.md': 'Project documentation',
        '.env': 'Environment variables',
        '.env.example': 'Environment variables template'
    }
    
    filename = file_path.name
    
    if filename in descriptions:
        return descriptions[filename]
    
    if file_path.suffix == '.pyc':
        return 'Compiled Python bytecode'
    elif file_path.suffix == '.log':
        return 'Log file'
    elif file_path.suffix == '.sqlite':
        return 'SQLite database file'
    elif 'test' in filename.lower():
        return 'Test file'
    else:
        return f'Standard {file_path.suffix} file'

def export_code_to_file():
    """Export all code to opus.txt"""
    
    output_file = 'opus.txt'
    base_path = Path('.')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("AI CHIEF OF STAFF - COMPLETE CODEBASE EXPORT\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Export includes app-specific code with full content\n")
        f.write(f"and brief descriptions for standard files\n")
        f.write("=" * 80 + "\n\n")
        
        # Walk through all files
        for root, dirs, files in os.walk('.'):
            # Skip hidden directories and common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                file_path = Path(root) / file
                relative_path = file_path.relative_to(base_path)
                
                try:
                    if is_app_specific_file(file_path):
                        # Full content for app-specific files
                        f.write(f"\n{'='*60}\n")
                        f.write(f"FILE: {relative_path}\n")
                        f.write(f"{'='*60}\n")
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8') as code_file:
                                content = code_file.read()
                                f.write(content)
                                f.write('\n')
                        except UnicodeDecodeError:
                            # Handle binary files
                            f.write(f"[Binary file - {file_path.suffix} format]\n")
                        except Exception as e:
                            f.write(f"[Error reading file: {e}]\n")
                    
                    else:
                        # Brief description for mundane files
                        description = get_file_description(file_path)
                        f.write(f"FILE: {relative_path} - {description}\n")
                
                except Exception as e:
                    f.write(f"ERROR processing {relative_path}: {e}\n")
        
        # Footer
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF CODEBASE EXPORT\n")
        f.write("=" * 80 + "\n")
    
    print(f"Code exported to {output_file}")
    
    # Get file size
    size = os.path.getsize(output_file)
    print(f"Export file size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")

if __name__ == "__main__":
    export_code_to_file() 