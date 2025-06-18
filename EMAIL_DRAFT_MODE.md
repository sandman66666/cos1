# Email Draft Mode Guide

## Overview

The AI Chief of Staff now supports **Email Draft Mode** - a safer approach where the system creates intelligent email drafts for your review instead of automatically sending emails.

## ✅ What Draft Mode Does

- **Analyzes incoming emails** using Claude 4 Opus with extended thinking
- **Creates intelligent drafts** that match your communication style
- **Provides confidence scores** and strategic impact analysis
- **Queues drafts for your review** before sending
- **Allows editing** before sending
- **Never auto-sends** emails without your approval

## 🚀 Quick Setup

### 1. Configure Draft Mode
```bash
# Copy the configuration file
cp draft_mode_config.env .env

# Edit .env with your API keys
nano .env
```

### 2. Required API Keys
```bash
ANTHROPIC_API_KEY=your_claude_api_key
GOOGLE_CLIENT_ID=your_google_oauth_id  
GOOGLE_CLIENT_SECRET=your_google_oauth_secret
```

### 3. Start the Application
```bash
python main.py
```

## 📧 Draft Workflow

### Step 1: Email Analysis
When you receive an email, the AI:
- Analyzes the content and context
- Assesses strategic importance
- Determines optimal response approach
- Generates confidence score (0-100%)

### Step 2: Draft Creation
The system creates a draft with:
- **Subject line** optimized for the conversation
- **Response body** in your communication style  
- **Strategic reasoning** for the approach
- **Confidence assessment** and quality rating

### Step 3: Review & Send
You can:
- ✅ **Send as-is** if the draft looks good
- ✏️ **Edit** the draft before sending
- ❌ **Reject** the draft if not needed
- 📋 **Save** for later review

## 🔧 API Endpoints

### Get All Drafts
```bash
GET /api/agents/email/drafts
```

### Send a Draft
```bash
POST /api/agents/email/drafts/{draft_id}/send
```

### Edit a Draft
```bash
PUT /api/agents/email/drafts/{draft_id}/edit
{
  "edits": {
    "subject": "Updated subject",
    "body": "Updated email body..."
  }
}
```

### Reject a Draft
```bash
DELETE /api/agents/email/drafts/{draft_id}/reject
{
  "reason": "Not needed"
}
```

## 🎯 Draft Quality Indicators

### High Quality (85%+ confidence)
- ✅ Ready to send immediately
- 🎯 Strategic alignment confirmed
- 🤖 AI highly confident in approach

### Good Quality (70-85% confidence)
- ✏️ Minor edits might improve
- 📝 Review recommended
- 🤖 AI moderately confident

### Needs Review (<70% confidence)
- ⚠️ Requires careful review
- ✏️ Likely needs editing
- 👤 Manual input valuable

## ⚙️ Configuration Options

### Draft Settings
```bash
GET /api/agents/email/draft-settings
PUT /api/agents/email/draft-settings
```

Available settings:
- `draft_mode_enabled`: Always create drafts
- `auto_send_enabled`: Allow auto-sending (disabled in draft mode)
- `confidence_threshold_for_auto_approval`: Threshold for auto-approval
- `draft_retention_days`: How long to keep drafts

### Safety Features
- **No auto-sending** by default
- **Rate limiting** on draft creation
- **Confidence thresholds** for quality control
- **User approval required** for all sends

## 📊 Draft Analytics

Each draft includes:
- **Confidence Score**: AI's confidence in the response
- **Strategic Impact**: Business importance (low/medium/high)
- **Risk Assessment**: Potential risks of the response
- **Quality Rating**: Overall draft quality
- **Ready to Send**: Whether it's ready without edits

## 🔒 Security Features

- **No credentials stored** in drafts
- **Sensitive data filtering** with DLP
- **Audit logging** of all actions
- **Rate limiting** to prevent abuse
- **User authentication** required

## 🚀 Advanced Features

### Style Learning
The AI learns your communication patterns:
- Tone and formality preferences
- Common phrases and expressions
- Response timing patterns
- Strategic approach preferences

### Context Awareness
Drafts consider:
- Relationship history with sender
- Strategic business context
- Current goals and priorities
- Market timing factors

### Workflow Integration
Drafts can trigger:
- Follow-up task creation
- Calendar scheduling
- CRM updates
- Strategic alerts

## 📈 Benefits

✅ **Safety First**: Review before sending
✅ **Time Saving**: AI handles initial drafting
✅ **Quality Assurance**: Confidence scoring
✅ **Style Consistency**: Matches your voice
✅ **Strategic Alignment**: Business context aware
✅ **Learning System**: Improves over time

## 🔄 Migration from Auto-Send

If you previously had auto-send enabled:

1. **Existing drafts** will be preserved
2. **New emails** will create drafts instead
3. **No interruption** to current workflows
4. **Gradual transition** to draft review

## 🆘 Troubleshooting

### Drafts Not Creating
- Check `ENABLE_EMAIL_DRAFT_MODE=true` in .env
- Verify Claude API key is valid
- Check logs for error messages

### Poor Draft Quality
- System learns from your edits
- Provide feedback on draft quality
- Check strategic context is up to date

### Performance Issues
- Drafts process asynchronously
- Check system resources
- Review rate limiting settings

## 🎓 Best Practices

1. **Review High-Confidence Drafts** quickly - they're usually ready
2. **Edit Medium-Confidence Drafts** for better results  
3. **Provide Feedback** to improve AI learning
4. **Set Clear Preferences** in draft settings
5. **Regular Review** of pending drafts

---

## Next Steps

Once you're comfortable with draft mode, you can gradually enable more autonomous features:
- Partnership workflow automation
- Investor relationship nurturing  
- Goal achievement optimization
- Strategic business intelligence

The draft mode provides a safe foundation for exploring advanced AI capabilities! 