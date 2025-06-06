# AI Chief of Staff - Gmail E2E v0.1

🤖 **Your intelligent email and task management assistant powered by Claude 4 Sonnet**

The AI Chief of Staff is a comprehensive system that connects to your Gmail, processes your emails intelligently, extracts actionable tasks, and provides AI-powered assistance for productivity and strategic planning.

## 🌟 Features

### Core Functionality
- **Gmail Integration**: Secure OAuth authentication with Gmail API access
- **Smart Email Processing**: Normalizes and cleans email content from various formats
- **AI-Powered Task Extraction**: Uses Claude 4 Sonnet to identify action items, deadlines, and follow-ups
- **Intelligent Classification**: Automatically categorizes emails (regular, meetings, newsletters, etc.)
- **Priority Scoring**: Calculates priority scores based on content, labels, and urgency keywords
- **Natural Language Processing**: Extracts entities (emails, phone numbers, dates, amounts)

### AI Assistant
- **Claude 4 Sonnet Integration**: Direct chat interface with state-of-the-art AI
- **Context-Aware Responses**: AI understands your email context and workflow
- **Task Management**: Get help with prioritization and planning
- **Email Summaries**: AI-generated summaries of your email communications

### Web Interface
- **Modern Dashboard**: Clean, responsive web interface
- **Real-time Processing**: Process emails and see results immediately
- **Task Visualization**: View extracted tasks with priorities and categories
- **Status Monitoring**: Track system health and authentication status

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- Google Cloud Project with Gmail API enabled
- Anthropic API key for Claude 4 Sonnet

### Installation

1. **Clone and navigate to the project**:
   ```bash
   cd chief_of_staff_ai
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the project root:
   ```env
   # Required Settings
   GOOGLE_CLIENT_ID=your_google_client_id
   GOOGLE_CLIENT_SECRET=your_google_client_secret
   ANTHROPIC_API_KEY=your_anthropic_api_key
   
   # Optional Settings
   SECRET_KEY=your_secret_key_for_flask
   PORT=5000
   DEBUG=False
   ```

4. **Run the application**:
   ```bash
   python ../main.py
   ```

5. **Access the web interface**:
   Open http://localhost:5000 in your browser

## ⚙️ Configuration

### Google Cloud Setup

1. **Create a Google Cloud Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one

2. **Enable Gmail API**:
   - Go to APIs & Services > Library
   - Search for "Gmail API" and enable it

3. **Create OAuth 2.0 Credentials**:
   - Go to APIs & Services > Credentials
   - Click "Create Credentials" > "OAuth 2.0 Client IDs"
   - Application type: Web application
   - Authorized redirect URIs: `http://localhost:5000/auth/google/callback`
   - Note down the Client ID and Client Secret

4. **Configure OAuth Consent Screen**:
   - Add your email as a test user
   - Add required scopes:
     - `openid`
     - `https://www.googleapis.com/auth/userinfo.email`
     - `https://www.googleapis.com/auth/userinfo.profile`
     - `https://www.googleapis.com/auth/gmail.readonly`

### Anthropic Setup

1. **Get API Key**:
   - Sign up at [Anthropic](https://console.anthropic.com/)
   - Generate an API key
   - Add it to your `.env` file

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CLIENT_ID` | ✅ | - | Google OAuth client ID |
| `GOOGLE_CLIENT_SECRET` | ✅ | - | Google OAuth client secret |
| `ANTHROPIC_API_KEY` | ✅ | - | Anthropic API key for Claude |
| `SECRET_KEY` | ⚠️ | `dev-key-change-in-production` | Flask session secret |
| `PORT` | ❌ | `5000` | Web server port |
| `DEBUG` | ❌ | `False` | Enable debug mode |
| `EMAIL_FETCH_LIMIT` | ❌ | `50` | Max emails to fetch per request |
| `EMAIL_DAYS_BACK` | ❌ | `30` | Days back to fetch emails |
| `CLAUDE_MODEL` | ❌ | `claude-4-sonnet-20250514` | Claude model to use |

## 📋 Usage

### Web Interface

1. **Authentication**:
   - Click "Sign in with Google"
   - Grant Gmail access permissions
   - You'll be redirected to the dashboard

2. **Process Emails**:
   - Set number of emails to process (1-50)
   - Set days back to fetch (1-30)
   - Click "Process Emails & Extract Tasks"
   - View results in real-time

3. **AI Chat**:
   - Use the chat interface to ask questions
   - Get help with email summaries
   - Ask for task prioritization advice
   - General productivity assistance

### Command Line Interface

For advanced users and testing:

```bash
# Test authentication
python run.py --email your@email.com --test-auth

# Process emails via CLI
python run.py --email your@email.com --max-emails 10 --days-back 7

# Verbose output
python run.py --email your@email.com --verbose
```

### API Endpoints

The system provides REST API endpoints:

- `POST /api/process-emails`: Process emails and extract tasks
- `POST /api/chat`: Chat with Claude AI
- `GET /api/status`: Get system status
- `POST /api/fetch-emails`: Fetch emails only

## 🏗️ Architecture

### System Components

```
📧 Gmail API ──► 🔄 Gmail Fetcher ──► 📝 Email Normalizer ──► 🤖 Task Extractor ──► 💾 Results
                                                                     ▲
                                                              🧠 Claude 4 Sonnet
```

### Module Structure

```
chief_of_staff_ai/
├── config/
│   └── settings.py          # Configuration management
├── auth/
│   └── gmail_auth.py        # Gmail OAuth handling
├── ingest/
│   └── gmail_fetcher.py     # Email fetching from Gmail API
├── processors/
│   ├── email_normalizer.py  # Email content normalization
│   └── task_extractor.py    # AI-powered task extraction
├── interface/
│   └── prompt_console.py    # CLI interface (future)
├── storage/
│   └── vector_store.py      # Vector database (future)
├── embeddings/
│   └── embedder.py          # Text embeddings (future)
└── utils/
    └── datetime_utils.py    # Date/time utilities (future)
```

## 🔍 Task Extraction

The AI system identifies and extracts:

### Task Types
- **Action Items**: Explicit tasks mentioned in emails
- **Follow-ups**: Implied follow-up actions
- **Deadlines**: Date-specific commitments
- **Meetings**: Scheduling requests
- **Research**: Information gathering tasks

### Task Attributes
- **Description**: Clear, actionable task description
- **Priority**: High, medium, or low
- **Category**: follow-up, deadline, meeting, research, administrative, other
- **Due Date**: Parsed from natural language
- **Assignee**: Person responsible
- **Confidence Score**: AI confidence in extraction (0-1)
- **Source**: Reference to original email

### Priority Calculation
Tasks are prioritized based on:
- Gmail labels (Important, Starred)
- Urgency keywords in subject
- Email type (direct vs. mass email)
- Message type classification

## 🧪 Testing

### Manual Testing

1. **Authentication Test**:
   ```bash
   python run.py --email your@email.com --test-auth
   ```

2. **Full E2E Test**:
   ```bash
   python run.py --email your@email.com --max-emails 5
   ```

3. **Web Interface Test**:
   - Start the server: `python ../main.py`
   - Navigate to http://localhost:5000
   - Complete OAuth flow
   - Process test emails

### Test Data

The system works best with emails containing:
- Clear action items ("Please send me the report by Friday")
- Meeting requests ("Let's schedule a call next week")
- Deadlines ("The proposal is due on March 15th")
- Follow-up requests ("Can you follow up with the client?")

## 🔒 Security & Privacy

### Data Handling
- **Gmail Access**: Read-only access with explicit user consent
- **Local Storage**: Credentials stored temporarily in memory
- **No Persistent Storage**: Raw emails are not permanently stored
- **Encryption**: All API communications use HTTPS/TLS

### Privacy Features
- **Minimal Scopes**: Only requests necessary Gmail permissions
- **User Control**: Users can revoke access at any time
- **No Data Sharing**: Email content is not shared with third parties
- **Local Processing**: Most processing happens locally

## 🚧 Future Enhancements

### Planned Features
- **Calendar Integration**: Google Calendar sync for meeting scheduling
- **Vector Database**: Persistent email embeddings for semantic search
- **Slack Integration**: Team communication processing
- **File Upload**: Process documents and PDFs
- **Task Management**: Complete task lifecycle management
- **Notification System**: Smart alerts and reminders
- **Mobile App**: Native mobile interface

### Technical Improvements
- **Database Storage**: Persistent task and email storage
- **Caching Layer**: Redis for improved performance
- **Background Processing**: Celery for async email processing
- **Multi-user Support**: Team collaboration features
- **Enterprise Auth**: SSO and enterprise authentication

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### Common Issues

1. **OAuth Errors**:
   - Verify Google Cloud setup
   - Check redirect URIs
   - Ensure Gmail API is enabled

2. **Claude API Errors**:
   - Verify API key is correct
   - Check API usage limits
   - Ensure model name is correct

3. **No Tasks Extracted**:
   - Check email content has actionable items
   - Verify Claude API is working
   - Try with different email types

### Getting Help

- Check the logs for detailed error messages
- Use verbose mode for debugging: `--verbose`
- Review the configuration settings
- Test authentication separately: `--test-auth`

### Contact

For issues and feature requests, please create an issue in the repository.

---

**Built with ❤️ using Claude 4 Sonnet, Gmail API, and modern Python**
