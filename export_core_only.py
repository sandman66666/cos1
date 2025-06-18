#!/usr/bin/env python3
"""
Core Only Export Script for AI Chief of Staff
Exports ONLY the absolute essential files needed to recreate this system
"""

import os
import datetime
from pathlib import Path

def get_core_files():
    """Return only the absolute essential files for recreating this system"""
    
    # ONLY the most essential files - no duplicates, no reference materials
    core_files = [
        'main.py',  # Core Flask app with tier endpoints
        'chief_of_staff_ai/config/settings.py',  # Claude 4 Opus config
        'chief_of_staff_ai/auth/gmail_auth.py',  # Google OAuth integration
        'chief_of_staff_ai/models/database.py',  # Database models
        'chief_of_staff_ai/processors/email_quality_filter.py',  # Tier classification
        'chief_of_staff_ai/engagement_analysis/smart_contact_strategy.py',  # Contact extraction
        'api/routes/settings_routes.py',  # Settings API endpoints
        'requirements.txt',  # Dependencies
    ]
    
    return core_files

def get_file_summary(filename):
    """Get a focused summary of what each core file does"""
    
    summaries = {
        'main.py': 'Core Flask app with Google OAuth, contact tier endpoints, and Claude 4 Opus integration',
        'settings.py': 'Claude 4 Opus agent configuration with MCP connectors and autonomous capabilities',
        'gmail_auth.py': 'Google OAuth flow for Gmail API access and token management',
        'database.py': 'SQLAlchemy models: Users, Emails, People, TrustedContacts, etc.',
        'email_quality_filter.py': 'Contact tier classification system (Tier 1 = sent emails)',
        'smart_contact_strategy.py': 'Extracts contacts from sent emails via Gmail API',
        'settings_routes.py': 'API endpoints for contact tiers and email quality settings',
        'requirements.txt': 'Python dependencies including anthropic, flask, google-auth',
    }
    
    for key, summary in summaries.items():
        if key in filename:
            return summary
    
    return 'Core business logic component'

def export_core_only():
    """Export only the core essential files to opus_core.txt"""
    
    output_file = 'opus_core.txt'
    base_path = Path('.')
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write("=" * 80 + "\n")
        f.write("AI CHIEF OF STAFF - CORE CODE EXPORT (ESSENTIAL ONLY)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Generated on: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("This export contains ONLY the essential files to recreate this system:\n\n")
        f.write("CORE FUNCTIONALITY:\n")
        f.write("• Google OAuth integration for Gmail API access\n")
        f.write("• Contact extraction from sent emails\n")
        f.write("• Simple tier system: ALL sent email recipients = Tier 1\n")
        f.write("• Claude 4 Opus integration with agent capabilities\n")
        f.write("• Flask API endpoints for contact management\n")
        f.write("• SQLAlchemy database models\n")
        f.write("=" * 80 + "\n\n")
        
        # Get core files
        core_files = get_core_files()
        
        # Table of contents
        f.write("CORE FILES (8 files only):\n")
        f.write("=" * 40 + "\n")
        
        existing_files = []
        for core_file in core_files:
            file_path = base_path / core_file
            if file_path.exists():
                summary = get_file_summary(core_file)
                existing_files.append((core_file, summary))
                f.write(f"• {core_file} - {summary}\n")
            else:
                f.write(f"• {core_file} - [FILE NOT FOUND]\n")
        
        f.write("\n" + "=" * 80 + "\n\n")
        
        # Export the actual core code
        for core_file, summary in existing_files:
            file_path = base_path / core_file
            
            f.write(f"\n{'='*80}\n")
            f.write(f"FILE: {core_file}\n")
            f.write(f"PURPOSE: {summary}\n")
            f.write(f"{'='*80}\n")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as code_file:
                    content = code_file.read()
                    
                    # For main.py, filter out long HTML templates but keep the key endpoints
                    if file_path.name == 'main.py':
                        lines = content.split('\n')
                        filtered_lines = []
                        skip_html = False
                        
                        for line in lines:
                            # Skip long HTML templates but keep short ones
                            if ('return f"""' in line or 'return """' in line) and len(line) > 100:
                                skip_html = True
                                filtered_lines.append(line.split('"""')[0] + '"""[HTML TEMPLATE REMOVED]"""')
                            elif skip_html and '"""' in line:
                                skip_html = False
                                continue
                            elif not skip_html:
                                filtered_lines.append(line)
                        
                        content = '\n'.join(filtered_lines)
                    
                    f.write(content)
                    f.write('\n\n')
                    
            except UnicodeDecodeError:
                f.write(f"[Binary file - {file_path.suffix} format]\n\n")
            except Exception as e:
                f.write(f"[Error reading file: {e}]\n\n")
        
        # Add implementation guide
        f.write("\n" + "=" * 80 + "\n")
        f.write("IMPLEMENTATION GUIDE FOR AI REUSE\n")
        f.write("=" * 80 + "\n")
        f.write("""
STEP-BY-STEP RECREATION:

1. DEPENDENCIES:
   pip install -r requirements.txt

2. GOOGLE OAUTH SETUP:
   - Create Google Cloud project
   - Enable Gmail API
   - Create OAuth 2.0 credentials
   - Add to environment: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET

3. CLAUDE 4 OPUS SETUP:
   - Get Anthropic API key
   - Set ANTHROPIC_API_KEY environment variable
   - Model: "claude-opus-4-20250514"

4. DATABASE SETUP:
   - SQLAlchemy auto-creates SQLite database
   - Models: User, Email, Person, TrustedContact

5. CORE LOGIC:
   - Gmail API extracts sent email recipients
   - All sent email recipients = TrustedContact records
   - All TrustedContacts = Tier 1 (no exceptions)
   - API endpoint returns len(trusted_contacts) as tier_1_count

6. KEY ENDPOINTS:
   - /api/extract-sent-contacts - Extract contacts from Gmail
   - /api/email-quality/contact-tiers - Get tier counts for UI

CRITICAL INSIGHT:
The user's key requirement was simple: "All sent emails = Tier 1"
Don't overcomplicate the tier logic. Just count TrustedContact records.
""")
        
        # Footer
        f.write("\n" + "=" * 80 + "\n")
        f.write("END OF CORE CODE EXPORT\n")
        f.write("=" * 80 + "\n")
    
    print(f"Core code exported to {output_file}")
    
    # Get file size
    size = os.path.getsize(output_file)
    print(f"Export file size: {size:,} bytes ({size / 1024 / 1024:.2f} MB)")
    print(f"Core files included: {len(existing_files)}")

if __name__ == "__main__":
    export_core_only() 