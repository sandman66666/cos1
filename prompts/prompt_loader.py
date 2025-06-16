"""
Prompt Loader Utility
====================

Utility functions for loading and formatting prompts from the prompts directory.
This allows centralized management of all AI prompts used throughout the system.
"""

import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class PromptLoader:
    """Utility class for loading and formatting prompts"""
    
    def __init__(self, prompts_dir: str = "prompts"):
        """
        Initialize the prompt loader
        
        Args:
            prompts_dir: Directory containing prompt files
        """
        self.prompts_dir = prompts_dir
        self._prompt_cache = {}
    
    def load_prompt(self, category: str, prompt_name: str, **variables) -> str:
        """
        Load and format a prompt with variables
        
        Args:
            category: Prompt category (e.g., 'knowledge_tree', 'email_intelligence')
            prompt_name: Name of the prompt file (without .txt extension)
            **variables: Variables to substitute in the prompt
            
        Returns:
            Formatted prompt string
            
        Example:
            prompt = loader.load_prompt(
                'email_intelligence', 
                'email_analysis_system',
                user_email='user@example.com',
                business_context='Tech startup focused on AI'
            )
        """
        try:
            # Create cache key
            cache_key = f"{category}/{prompt_name}"
            
            # Load from cache or file
            if cache_key not in self._prompt_cache:
                prompt_path = os.path.join(self.prompts_dir, category, f"{prompt_name}.txt")
                
                if not os.path.exists(prompt_path):
                    raise FileNotFoundError(f"Prompt file not found: {prompt_path}")
                
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    prompt_template = f.read()
                
                # Remove documentation comments (lines starting with #)
                lines = prompt_template.split('\n')
                content_lines = []
                for line in lines:
                    stripped = line.strip()
                    if not stripped.startswith('#'):
                        content_lines.append(line)
                
                # Remove leading empty lines
                while content_lines and not content_lines[0].strip():
                    content_lines.pop(0)
                
                prompt_template = '\n'.join(content_lines)
                self._prompt_cache[cache_key] = prompt_template
            
            # Format with variables
            prompt_template = self._prompt_cache[cache_key]
            
            if variables:
                try:
                    formatted_prompt = prompt_template.format(**variables)
                except KeyError as e:
                    logger.error(f"Missing variable {e} for prompt {cache_key}")
                    # Return template with placeholder for missing variables
                    formatted_prompt = prompt_template
            else:
                formatted_prompt = prompt_template
            
            logger.debug(f"Loaded prompt {cache_key} with {len(variables)} variables")
            return formatted_prompt
            
        except Exception as e:
            logger.error(f"Failed to load prompt {category}/{prompt_name}: {str(e)}")
            raise
    
    def get_available_prompts(self) -> Dict[str, list]:
        """
        Get a list of all available prompts organized by category
        
        Returns:
            Dictionary mapping category names to lists of prompt names
        """
        available = {}
        
        try:
            if not os.path.exists(self.prompts_dir):
                logger.warning(f"Prompts directory not found: {self.prompts_dir}")
                return available
            
            for category in os.listdir(self.prompts_dir):
                category_path = os.path.join(self.prompts_dir, category)
                
                if os.path.isdir(category_path):
                    prompts = []
                    for file in os.listdir(category_path):
                        if file.endswith('.txt'):
                            prompts.append(file[:-4])  # Remove .txt extension
                    available[category] = prompts
            
            return available
            
        except Exception as e:
            logger.error(f"Failed to get available prompts: {str(e)}")
            return available
    
    def validate_prompt(self, category: str, prompt_name: str) -> bool:
        """
        Validate that a prompt exists and can be loaded
        
        Args:
            category: Prompt category
            prompt_name: Prompt name
            
        Returns:
            True if prompt exists and is valid
        """
        try:
            prompt_path = os.path.join(self.prompts_dir, category, f"{prompt_name}.txt")
            return os.path.exists(prompt_path)
        except Exception:
            return False
    
    def clear_cache(self):
        """Clear the prompt cache"""
        self._prompt_cache.clear()
        logger.info("Prompt cache cleared")


# Global prompt loader instance
prompt_loader = PromptLoader()

# Convenience functions
def load_prompt(category: str, prompt_name: str, **variables) -> str:
    """Convenience function to load a prompt"""
    return prompt_loader.load_prompt(category, prompt_name, **variables)

def get_available_prompts() -> Dict[str, list]:
    """Convenience function to get available prompts"""
    return prompt_loader.get_available_prompts()

def validate_prompt(category: str, prompt_name: str) -> bool:
    """Convenience function to validate a prompt"""
    return prompt_loader.validate_prompt(category, prompt_name)


# Prompt categories and names for easy reference
class PromptCategories:
    """Constants for prompt categories and names"""
    
    # Knowledge Tree
    KNOWLEDGE_TREE = "knowledge_tree"
    BUILD_INITIAL_TREE = "build_initial_tree"
    REFINE_EXISTING_TREE = "refine_existing_tree"
    ASSIGN_EMAIL_TO_TREE = "assign_email_to_tree"
    
    # Email Intelligence
    EMAIL_INTELLIGENCE = "email_intelligence"
    EMAIL_ANALYSIS_SYSTEM = "email_analysis_system"
    
    # Task Extraction
    TASK_EXTRACTION = "task_extraction"
    TASK_EXTRACTION_360 = "360_task_extraction"
    
    # Intelligence Chat
    INTELLIGENCE_CHAT = "intelligence_chat"
    ENHANCED_CHAT_SYSTEM = "enhanced_chat_system"


# Example usage functions for common prompts
def get_knowledge_tree_build_prompt(user_email: str, emails_data: str) -> str:
    """Get the initial knowledge tree building prompt"""
    return load_prompt(
        PromptCategories.KNOWLEDGE_TREE,
        PromptCategories.BUILD_INITIAL_TREE,
        user_email=user_email,
        emails_data=emails_data
    )

def get_email_analysis_prompt(user_email: str, business_context: str) -> str:
    """Get the email analysis system prompt"""
    return load_prompt(
        PromptCategories.EMAIL_INTELLIGENCE,
        PromptCategories.EMAIL_ANALYSIS_SYSTEM,
        user_email=user_email,
        business_context=business_context
    )

def get_tactical_task_extraction_prompt(email_context: str, context_strength: float, connection_count: int) -> str:
    """Get the tactical 360-degree task extraction prompt"""
    return load_prompt(
        PromptCategories.TASK_EXTRACTION,
        PromptCategories.TASK_EXTRACTION_360,
        enhanced_email_context=email_context,
        context_strength=context_strength,
        connection_count=connection_count
    )

def get_knowledge_aware_chat_prompt(user_email: str, business_context: str) -> str:
    """Get the knowledge tree aware chat system prompt (ONLY option)"""
    return load_prompt(
        PromptCategories.INTELLIGENCE_CHAT,
        PromptCategories.ENHANCED_CHAT_SYSTEM,
        user_email=user_email,
        business_context=business_context
    ) 