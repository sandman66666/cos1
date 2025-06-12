#!/usr/bin/env python3
"""
Fix Model Imports - Replace old models with enhanced models in database.py
This script updates the model definitions to use the enhanced models.
"""

import os
import re

def fix_model_imports():
    """Fix the model import and usage issue"""
    
    database_py_path = 'models/database.py'
    
    if not os.path.exists(database_py_path):
        print(f"Error: {database_py_path} not found!")
        return False
    
    print("🔧 Fixing model imports in database.py...")
    
    # Read the current file
    with open(database_py_path, 'r') as f:
        content = f.read()
    
    # Check if we need to fix imports
    if 'from models.enhanced_models import' in content and 'class Email(Base):' in content:
        print("✅ Model conflict detected - will fix by updating imports")
        
        # Strategy: Update the model references to use enhanced models directly
        # Instead of having duplicate model definitions
        
        # Replace the old model class definitions with aliases to enhanced models
        replacements = [
            # Replace class definitions with aliases
            (r'class Email\(Base\):.*?(?=class|\Z)', 'Email = EnhancedEmail\n'),
            (r'class Task\(Base\):.*?(?=class|\Z)', 'Task = EnhancedTask\n'),
            (r'class Person\(Base\):.*?(?=class|\Z)', 'Person = EnhancedPerson\n'),
            (r'class Topic\(Base\):.*?(?=class|\Z)', 'Topic = EnhancedTopic\n'),
            (r'class Project\(Base\):.*?(?=class|\Z)', 'Project = EnhancedProject\n'),
        ]
        
        # Apply replacements
        new_content = content
        for pattern, replacement in replacements:
            # Use DOTALL flag to match across newlines
            new_content = re.sub(pattern, replacement, new_content, flags=re.DOTALL)
        
        # Also update the enhanced model imports to remove the "Enhanced" prefix
        new_content = new_content.replace(
            'Topic as EnhancedTopic, Person as EnhancedPerson, Task as EnhancedTask,',
            'Topic, Person, Task,'
        )
        new_content = new_content.replace(
            'Email as EnhancedEmail, CalendarEvent, Project as EnhancedProject,',
            'Email, CalendarEvent, Project,'
        )
        
        # Create backup
        backup_path = f'{database_py_path}.backup'
        with open(backup_path, 'w') as f:
            f.write(content)
        print(f"📁 Created backup: {backup_path}")
        
        # Write the fixed content
        with open(database_py_path, 'w') as f:
            f.write(new_content)
        
        print("✅ Model imports fixed successfully!")
        print("🔄 The application now uses enhanced models with all the new columns.")
        return True
    
    elif 'from models.enhanced_models import' not in content:
        print("❌ Enhanced model imports not found - database.py needs manual update")
        return False
    
    else:
        print("✅ Model imports appear to be correct already")
        return True

def create_simple_model_fix():
    """Create a simpler fix - just update the Base metadata"""
    
    fix_script = """# Quick fix for SQLAlchemy metadata cache issue
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from models.database import get_db_manager
from models.enhanced_models import Base as EnhancedBase

def refresh_metadata():
    db_manager = get_db_manager()
    
    # Clear the metadata cache
    db_manager.engine.dispose()
    
    # Reflect the actual database schema
    EnhancedBase.metadata.reflect(bind=db_manager.engine)
    
    print("✅ SQLAlchemy metadata refreshed")

if __name__ == "__main__":
    refresh_metadata()
"""
    
    with open('refresh_metadata.py', 'w') as f:
        f.write(fix_script)
    
    print("📝 Created refresh_metadata.py as a backup solution")

if __name__ == "__main__":
    print("🔧 AI Chief of Staff - Model Import Fix")
    print("="*50)
    
    success = fix_model_imports()
    
    if not success:
        print("\n🔧 Creating alternative solution...")
        create_simple_model_fix()
    
    print("\n📋 NEXT STEPS:")
    print("1. Restart the application to clear SQLAlchemy cache")
    print("2. Test email processing to confirm the fix")
    print("3. If issues persist, run: python refresh_metadata.py") 