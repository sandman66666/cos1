#!/usr/bin/env python3
"""
Focused Code Export Script for AI Chief of Staff
Exports only the key, reusable code that's specific to this system
"""

import os
import datetime
from pathlib import Path

def is_key_file(file_path):
    """Determine if a file contains key, reusable code"""
    
    # Key files that contain unique business logic
    key_files = [
        'main.py',  # Core Flask app with our specific endpoints
        'chief_of_staff_ai/config/settings.py',  # Claude 4 Opus config
        'chief_of_staff_ai/auth/gmail_auth.py',  # Google OAuth integration
        'chief_of_staff_ai/models/database.py',  # Database models
        'chief_of_staff_ai/processors/email_quality_filter.py',  # Tier system
        'chief_of_staff_ai/engagement_analysis/smart_contact_strategy.py',  # Contact extraction
        'Claude_workers.txt',  # Claude workers guide
    ]
    
    # Key directories with business logic
    key_directories = [
        'chief_of_staff_ai/agents/',  # AI agents
        'api/routes/',  # API endpoints
        'chief_of_staff_ai/processors/',  # Email processing
        'chief_of_staff_ai/intelligence/',  # Business intelligence
    ]
    
    file_str = str(file_path)
    
    # Check exact files
    for key_file in key_files:
        if file_str.endswith(key_file):
            return True
    
    # Check directories
    for key_dir in key_directories:
        if key_dir in file_str and file_path.suffix == '.py':
            return True
    
    return False

def get_code_summary(file_path):
    """Get a focused summary of what the code does"""
    
    summaries = {
        'main.py': 'Core Flask app with Claude 4 Opus integration, Google OAuth, and tier system endpoints',
        'settings.py': 'Claude 4 Opus configuration with agent capabilities and MCP connectors',
        'gmail_auth.py': 'Google OAuth integration for Gmail API access',
        'database.py': 'SQLAlchemy models for users, emails, contacts, and trusted contacts',
        'email_quality_filter.py': 'Contact tier classification system (Tier 1 = sent emails)',
        'smart_contact_strategy.py': 'Extracts contacts from sent emails and builds trusted contact database',
        'Claude_workers.txt': 'Official Anthropic guide for Claude agent capabilities',
    }
    
    filename = file_path.name
    for key, summary in summaries.items():
        if key in filename:
            return summary
    
    # For agent files
    if 'agents/' in str(file_path):
        return f'AI agent: {filename.replace(".py", "").replace("_", " ").title()}'
    
    # For API routes
    if 'api/routes/' in str(file_path):
        return f'API endpoints: {filename.replace(".py", "").replace("_", " ").title()}'
    
    # For processors
    if 'processors/' in str(file_path):
        return f'Email processor: {filename.replace(".py", "").replace("_", " ").title()}'
    
    return 'Business logic component'

def export_key_code():
    """Export only the key, reusable code to opus_key.txt"""
    
    output_file = 'opus_key.txt'
    base_path = Path('.')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("AI CHIEF OF STAFF - KEY CODE EXPORT (FOCUSED)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("This export contains only the key, reusable code specific to this system:\n")
        f.write("- Claude 4 Opus integration with agent capabilities\n")
        f.write("- Google OAuth and Gmail API integration\n")
        f.write("- Contact extraction from sent emails\n")
        f.write("- Tier classification system (Tier 1 = sent emails)\n")
        f.write("- Core database models and API endpoints\n")
        f.write("- Business intelligence and email processing\n")
        f.write("=" * 80 + "\n\n")
        
        # Table of contents
        f.write("TABLE OF CONTENTS\n")
        f.write("=" * 40 + "\n")
        
        key_files_found = []
        for root, dirs, files in os.walk('.'):
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules']]
            
            for file in files:
                file_path = Path(root) / file
                if is_key_file(file_path):
                    relative_path = file_path.relative_to(base_path)
                    summary = get_code_summary(file_path)
                    key_files_found.append((relative_path, summary))
                    f.write(f"• {relative_path} - {summary}\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Export the actual code
        for relative_path, summary in key_files_found:
            file_path = base_path / relative_path
            
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE: {relative_path}\n")
            f.write(f"PURPOSE: {summary}\n")
            f.write(f"{'='*80}\n")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as code_file:
                    content = code_file.read()
                    
                    # For main.py, only include the key parts
                    if file_path.name == 'main.py':
                        lines = content.split('\n')
                        filtered_lines = []
                        skip_section = False
                        
                        for line in lines:
                            # Skip long HTML templates
                            if 'return f"""' in line or 'return """' in line:
                                skip_section = True
                            elif skip_section and '"""' in line:
                                skip_section = False
                                continue
                            
                            if not skip_section:
                                filtered_lines.append(line)
                        
                        content = '\n'.join(filtered_lines)
                    
                    f.write(content)
                    f.write('\n\n')
                    
            except UnicodeDecodeError:
                f.write(f"[Binary file - {file_path.suffix} format]\n\n")
            except Exception as e:
                f.write(f"[Error reading file: {e}]\n\n")
        
        # Add key insights section
        f.write("\n" + "=" * 80 + "\n")
        f.write("KEY IMPLEMENTATION INSIGHTS\n")
        f.write("=" * 80 + "\n")
        f.write("""
CRITICAL POINTS FOR REUSE:

1. CONTACT TIER SYSTEM:
   - ALL contacts from sent emails = Tier 1 (no exceptions)
   - Use get_trusted_contacts() to get sent email recipients
   - Simple rule: if you sent them an email, they're important

2. GOOGLE OAUTH INTEGRATION:
   - Requires Gmail API scope for reading sent emails
   - Store refresh tokens for background processing
   - Use gmail_auth.py for OAuth flow

3. CLAUDE 4 OPUS AGENT SETUP:
   - Model: "claude-opus-4-20250514" 
   - Enable code execution, Files API, MCP connectors
   - Set autonomous confidence thresholds (85%+ autonomous)

4. EMAIL EXTRACTION PATTERN:
   - Query sent emails using Gmail API
   - Extract recipient emails and names
   - Create TrustedContact records
   - Sync to Person records for UI display

5. DATABASE ARCHITECTURE:
   - Users table for OAuth tokens
   - Emails table for email content
   - People table for contact display
   - TrustedContacts table for sent email recipients

6. API ENDPOINT PATTERN:
   - Always check authentication first
   - Use get_current_user() for session isolation
   - Return JSON with success/error structure
   - Handle database exceptions gracefully

7. SIMPLE TIER LOGIC:
   - Don't overcomplicate tier classification
   - User request: "All sent emails = Tier 1"
   - Implementation: return len(trusted_contacts) as tier_1_count
""")
        
        # Footer
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF KEY CODE EXPORT\n")
        f.write("=" * 80 + "\n")
    
    print(f"Key code exported to {output_file}")
    
    # Get file size
    size = os.path.getsize(output_file)
    print(f"Export file size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    print(f"Files included: {len([f for f in os.listdir('.') if os.path.isfile(f)])}")

if __name__ == "__main__":
    export_key_code() 