# Prompt Management Migration Guide

This guide shows how to migrate existing code from embedded prompts to the new centralized prompt management system.

## Benefits of External Prompt Management

1. **Easy Editing**: Modify prompts without touching code
2. **Version Control**: Track prompt changes separately from code
3. **Consistency**: Centralized prompt templates prevent duplication
4. **Testing**: Test prompt changes without code deployment
5. **Documentation**: Each prompt includes goal and context documentation

## Migration Steps

### Step 1: Identify Embedded Prompts

Look for patterns like:
```python
# OLD - Embedded prompt
prompt = f"""You are an AI assistant that does {task}.

Input data: {data}

Please analyze this and return JSON."""
```

### Step 2: Create External Prompt File

Create a `.txt` file in the appropriate prompts category:

```text
# prompts/category/prompt_name.txt

# GOAL: Brief description of what this prompt does
# CONTEXT: When and how this prompt is used
# INPUT VARIABLES: {variable1}, {variable2}
# EXPECTED OUTPUT: Description of expected response format

You are an AI assistant that does {task}.

Input data: {data}

Please analyze this and return JSON.
```

### Step 3: Update Code to Use Prompt Loader

```python
# NEW - Using prompt loader
from prompts.prompt_loader import load_prompt, PromptCategories

prompt = load_prompt(
    PromptCategories.CATEGORY_NAME,
    'prompt_name',
    task=task,
    data=data
)
```

## Example Migrations

### Before: Embedded Knowledge Tree Prompt

```python
def build_initial_knowledge_tree(emails_data, user_email):
    prompt = f"""
You are analyzing emails for {user_email} to build a MASTER knowledge tree...

EMAILS TO ANALYZE:
{json.dumps(emails_data, indent=2)}

Create a comprehensive, hierarchical knowledge structure...
"""
    
    response = claude_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
```

### After: Using Prompt Loader

```python
def build_initial_knowledge_tree(emails_data, user_email):
    from prompts.prompt_loader import load_prompt, PromptCategories
    
    prompt = load_prompt(
        PromptCategories.KNOWLEDGE_TREE,
        PromptCategories.BUILD_INITIAL_TREE,
        user_email=user_email,
        emails_data=json.dumps(emails_data, indent=2)
    )
    
    response = claude_client.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}]
    )
```

## Files to Update

The following files contain embedded prompts that should be migrated:

### ✅ Migrated Files
- `api/routes/email_routes.py` - Knowledge tree functions ✅
- `api/routes/intelligence_routes.py` - Chat endpoints ✅

### 🔄 Files to Migrate

1. **`chief_of_staff_ai/processors/email_intelligence.py`**
   - Main email analysis system prompt
   - Replace with: `load_prompt(PromptCategories.EMAIL_INTELLIGENCE, PromptCategories.EMAIL_ANALYSIS_SYSTEM)`

2. **`chief_of_staff_ai/processors/task_extractor.py`**
   - Basic task extraction prompt
   - 360-degree task extraction prompt
   - Replace with: `load_prompt(PromptCategories.TASK_EXTRACTION, PromptCategories.BASIC_TASK_EXTRACTION)`

3. **Other processor files**
   - Search for `f"""` patterns with AI prompts
   - Look for `system_prompt =` assignments

## Finding Embedded Prompts

Use this command to find embedded prompts:

```bash
# Find f-string prompts
grep -r "prompt.*=.*f\"\"\"" . --include="*.py"

# Find regular string prompts  
grep -r "prompt.*=.*\"\"\"" . --include="*.py"

# Find system prompts
grep -r "system_prompt.*=" . --include="*.py"
```

## Testing After Migration

1. **Verify prompts load correctly**:
```python
from prompts.prompt_loader import get_available_prompts
print(get_available_prompts())
```

2. **Test prompt formatting**:
```python
from prompts.prompt_loader import load_prompt
prompt = load_prompt('category', 'prompt_name', test_var='test')
print(prompt)
```

3. **Run existing functionality** to ensure behavior is unchanged

## Adding New Prompts

When adding new AI functionality:

1. Create prompt file first: `prompts/category/new_prompt.txt`
2. Add constants to `PromptCategories` class
3. Use prompt loader in code
4. Add convenience function if needed

## Best Practices

- **Keep prompts focused** - One purpose per prompt file
- **Document thoroughly** - Include goal, context, variables, and expected output
- **Use consistent naming** - Follow existing naming conventions
- **Test thoroughly** - Prompt changes can significantly impact AI behavior
- **Version control** - Track prompt changes in git
- **Review changes** - Have other developers review prompt modifications

## Troubleshooting

### Missing Variable Error
```
KeyError: 'variable_name'
```
**Solution**: Add the missing variable to the `load_prompt()` call or update the prompt template.

### File Not Found Error
```
FileNotFoundError: Prompt file not found: prompts/category/prompt.txt
```
**Solution**: Check the file path and ensure the prompt file exists.

### Import Error
```
ImportError: No module named 'prompts.prompt_loader'
```
**Solution**: Ensure the prompts directory is in your Python path or use relative imports.

## Next Steps

1. **Complete migration** of remaining files
2. **Add new prompt categories** as needed  
3. **Create prompt versioning** system if needed
4. **Add prompt testing** framework
5. **Document prompt engineering** guidelines 