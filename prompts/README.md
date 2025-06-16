# AI Chief of Staff - Prompts Library

This folder contains all the prompts used throughout the AI Chief of Staff system, organized by functionality. Each prompt file includes:

- **Goal**: The specific purpose and objective of the prompt
- **Context**: When and how the prompt is used
- **Input Variables**: What dynamic data is inserted into the prompt
- **Expected Output**: The format and structure of the expected response

## Prompt Categories

### 📊 Knowledge Tree Prompts (`knowledge_tree/`)
These prompts handle the master knowledge tree system that categorizes all emails and business intelligence.

- `build_initial_tree.txt` - Creates the master knowledge tree from scratch
- `refine_existing_tree.txt` - Updates existing tree with new email data
- `assign_email_to_tree.txt` - Categorizes individual emails using the existing tree

### 📧 Email Intelligence Prompts (`email_intelligence/`)
These prompts extract business intelligence, people, tasks, and insights from emails.

- `email_analysis_system.txt` - Main email analysis system prompt

### ✅ Task Extraction Prompts (`task_extraction/`)
These prompts identify and extract actionable tasks from email communications.

- `360_task_extraction.txt` - Advanced tactical task extraction with business intelligence context and high confidence thresholds

### 💬 Intelligence Chat Prompts (`intelligence_chat/`)
These prompts power the AI assistant chat functionality.

- `enhanced_chat_system.txt` - Knowledge tree aware chat assistant (REQUIRED)

## Knowledge Tree First Architecture

**ALL PROMPTS REQUIRE KNOWLEDGE TREE CONTEXT**

This system enforces a "Knowledge Tree First" approach where users must complete Step 2 (Build Knowledge Tree) before accessing any AI functionality. This ensures:

- **Consistent categorization** across all AI interactions
- **Rich business context** for all responses  
- **Strategic intelligence** rather than generic assistance
- **Cumulative learning** that builds over time

**NO FALLBACK PROMPTS** - The system enforces knowledge tree requirements rather than degrading to basic functionality.

## Usage in Code

To use these prompts in your code:

```python
def load_prompt(category, prompt_name, **variables):
    """Load and format a prompt with variables"""
    prompt_path = f"prompts/{category}/{prompt_name}.txt"
    with open(prompt_path, 'r') as f:
        prompt_template = f.read()
    
    # Replace variables in the prompt
    return prompt_template.format(**variables)

# Example usage - ALL prompts require knowledge tree context:
system_prompt = load_prompt(
    'intelligence_chat', 
    'enhanced_chat_system',  # ONLY chat option
    user_email='user@example.com',
    business_context='Knowledge tree context with topics, people, projects'
)
```

## Editing Prompts

When editing prompts:

1. **Test thoroughly** - Changes to prompts can significantly impact AI behavior
2. **Maintain variable placeholders** - Keep `{variable_name}` format for dynamic content
3. **Update documentation** - Modify the goal/context sections when changing prompt behavior
4. **Version control** - Track prompt changes as they affect system behavior
5. **Preserve knowledge tree requirements** - All prompts should leverage the master knowledge tree

## Prompt Engineering Best Practices

- **Be specific** - Clear instructions produce better results
- **Provide examples** - Show the AI what good output looks like
- **Use structured output** - Request JSON or specific formats for parsing
- **Set boundaries** - Define what the AI should and shouldn't do
- **Include knowledge tree context** - Always leverage the established business vocabulary
- **Build on existing categories** - Reference topics, people, and projects from the master tree 