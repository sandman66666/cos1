# AI Chief of Staff - Intelligence Dashboard

A comprehensive AI-powered business intelligence platform that transforms your Gmail and Calendar into a proactive Chief of Staff experience. Built with React, Flask, and Claude 4 Sonnet.

## 🌟 Key Features

### 🧠 **Intelligence Dashboard**
- **Real-time Intelligence Metrics**: Live tracking of business insights, entity relationships, and topic momentum
- **Proactive Business Insights**: AI-generated strategic recommendations with confidence scoring
- **Entity Network Visualization**: Interactive relationship mapping between people, topics, and projects
- **Intelligence Assistant**: Context-aware AI chat with access to your complete business intelligence

### 📧 **Advanced Email Intelligence**
- **Claude 4 Sonnet Processing**: Deep email analysis with comprehensive context understanding
- **Comprehensive Context Stories**: Rich narratives explaining the full business context of each email
- **Strategic Importance Scoring**: AI-calculated priority levels for all communications
- **Relationship Intelligence**: Automatic tracking of professional relationships and communication patterns

### 📅 **Meeting Intelligence & Preparation**
- **Automated Meeting Preparation**: AI-generated prep tasks and attendee intelligence
- **Context-Aware Scheduling**: Meeting recommendations based on relationship intelligence
- **Attendee Analysis**: Strategic value assessment and communication history for all participants
- **Meeting Context Stories**: Rich background information for every calendar event

### 👥 **Professional Network Management**
- **Relationship Decay Prediction**: Proactive suggestions for relationship maintenance
- **Engagement Scoring**: Quantified relationship strength with trend analysis
- **Communication Pattern Analysis**: Understanding of how you interact with your network
- **Strategic Contact Recommendations**: AI-suggested networking opportunities

### 📊 **Business Intelligence & Analytics**
- **Topic Momentum Tracking**: Monitor emerging business themes and opportunities
- **Predictive Analytics**: Relationship predictions, opportunity detection, decision timing
- **Real-time Processing**: Continuous intelligence updates as new data arrives
- **Entity-Centric Architecture**: Everything connected through intelligent relationship mapping

## 🚀 Quick Start

### Prerequisites
- **Node.js 16+** (for React frontend)
- **Python 3.10+** (for Flask backend)
- **Gmail account** with API access
- **Anthropic Claude API key**
- **Google Calendar API access**

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/your-repo/ai-chief-of-staff.git
cd ai-chief-of-staff
```

2. **Backend Setup**
```bash
# Install Python dependencies
pip install -r requirements.txt

# Environment setup
cp .env.example .env
# Edit .env with your API keys (see Configuration section)
```

3. **Frontend Setup**
```bash
# Install React dependencies
cd frontend
npm install

# Build for production
npm run build
```

4. **Database Setup**
```bash
# Run database migrations
python migrate_intelligence.py
```

5. **Start the Application**
```bash
# Start Flask backend (serves React build)
python main.py

# For development with hot reload
cd frontend && npm start  # React dev server on :3000
python main.py            # Flask API on :5000
```

6. **Access the Intelligence Dashboard**
Open http://localhost:5000 in your browser

## ⚙️ Configuration

Create a `.env` file with the following variables:

```env
# Google OAuth (Required)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:5000/auth/google/callback

# Claude AI (Required)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Application Settings
SECRET_KEY=your_secret_key
DEBUG=True
PORT=5000

# Intelligence Settings (Optional)
EMAIL_FETCH_LIMIT=50
EMAIL_DAYS_BACK=30
CALENDAR_DAYS_FORWARD=14
ENABLE_REAL_TIME_PROCESSING=true
ENABLE_PREDICTIVE_ANALYTICS=true
```

### Google Cloud Setup

1. **Create Google Cloud Project** and enable:
   - Gmail API
   - Google Calendar API
   - Google OAuth 2.0

2. **OAuth 2.0 Configuration**:
   - Authorized redirect URI: `http://localhost:5000/auth/google/callback`
   - Required scopes:
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/calendar.readonly`
     - `https://www.googleapis.com/auth/userinfo.profile`

## 📋 Usage

### Intelligence Dashboard

1. **Sign in with Google** and authorize Gmail/Calendar access
2. **Intelligence Sync**: Click "Sync Intelligence" to process emails and calendar
3. **Explore Insights**: View proactive business insights with priority filtering
4. **Entity Networks**: Navigate topic and relationship intelligence
5. **AI Assistant**: Ask questions about your business intelligence

### Key Workflows

#### **Meeting Preparation**
1. Click "Generate Meeting Intelligence" 
2. AI analyzes upcoming meetings and creates preparation tasks
3. View attendee intelligence and relationship context
4. Access meeting context stories and strategic importance

#### **Business Insights**
1. Navigate to "Proactive Intelligence" panel
2. Filter insights by type (relationship, meeting, opportunity)
3. Click insights for detailed analysis and recommended actions
4. Provide feedback to improve AI recommendations

#### **Relationship Management**
1. Access "People & Relationships" view
2. Review engagement scores and communication patterns
3. Get proactive relationship maintenance suggestions
4. Explore relationship intelligence and strategic value

## 🏗️ Architecture

### Frontend (React + TypeScript)
```
frontend/
├── src/
│   ├── App.tsx              # Main intelligence dashboard
│   ├── components/          # React components
│   ├── types/              # TypeScript interfaces
│   └── utils/              # Utility functions
├── public/                 # Static assets
└── package.json           # Dependencies & scripts
```

### Backend (Flask + SQLAlchemy)
```
chief_of_staff_ai/
├── models/
│   ├── database.py         # Core database models
│   └── enhanced_models.py  # Intelligence-enhanced models
├── processors/
│   ├── email_intelligence.py      # Email AI processing
│   ├── intelligence_engine.py     # Core intelligence engine
│   ├── realtime_processor.py      # Real-time processing
│   └── analytics/
│       └── predictive_analytics.py # Business predictions
├── ingest/
│   ├── gmail_fetcher.py    # Gmail API integration
│   └── calendar_fetcher.py # Calendar API integration
└── api/
    └── enhanced_endpoints.py # REST API endpoints
```

### Intelligence Pipeline
```
📧 Gmail/Calendar APIs → 🔄 Real-time Processor → 🧠 Claude 4 Analysis → 
📊 Intelligence Engine → 💾 Entity Database → ⚡ React Dashboard
```

## 🔧 API Endpoints

### Core Intelligence
- `GET /api/intelligence-metrics` - Real-time intelligence quality metrics
- `GET /api/intelligence-insights` - Proactive business insights
- `POST /api/proactive-insights/generate` - Generate new insights

### Entity Management
- `GET /api/tasks` - Enhanced tasks with context stories
- `GET /api/people` - Relationship intelligence
- `GET /api/topics` - Topic momentum and intelligence
- `GET /api/enhanced-calendar-events` - Meeting intelligence

### Real-time Features
- `POST /api/trigger-email-sync` - Unified intelligence sync
- `POST /api/calendar/generate-meeting-intelligence` - Meeting preparation
- `POST /api/chat-with-knowledge` - AI assistant with business context

## 🧪 Development

### React Development
```bash
cd frontend
npm start          # Development server with hot reload
npm run build      # Production build
npm test           # Run tests
```

### Backend Development
```bash
python main.py --debug    # Debug mode with auto-reload
python migrate_intelligence.py  # Run database migrations
```

### Testing
```bash
# Backend tests
python -m pytest tests/

# Frontend tests  
cd frontend && npm test

# Integration tests
python test_integration.py
```

## 🚀 Production Deployment

### Heroku Deployment
```bash
# Configure buildpacks
heroku buildpacks:add heroku/nodejs
heroku buildpacks:add heroku/python

# Set environment variables
heroku config:set GOOGLE_CLIENT_ID=...
heroku config:set ANTHROPIC_API_KEY=...

# Deploy
git push heroku main
```

### Docker Deployment
```bash
# Build and run
docker build -t ai-chief-of-staff .
docker run -p 5000:5000 --env-file .env ai-chief-of-staff
```

## 🔒 Security & Privacy

- **Read-only Access**: Only reads emails and calendar events
- **Local Processing**: Intelligence analysis happens on your server
- **No Data Sharing**: Your business intelligence stays private
- **Encrypted Storage**: All sensitive data encrypted at rest
- **OAuth 2.0**: Secure Google authentication with minimal scopes

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Common Issues

**No Intelligence Data Showing**:
- Ensure Google OAuth is properly configured
- Check that Gmail/Calendar APIs are enabled
- Verify Anthropic API key is valid
- Run database migration: `python migrate_intelligence.py`

**Real-time Updates Not Working**:
- Check that real-time processing is enabled in settings
- Verify WebSocket connections in browser developer tools
- Ensure Flask app is running in production mode

**AI Assistant Not Responding**:
- Verify Anthropic API key and usage limits
- Check that business intelligence data has been processed
- Ensure Claude model access (claude-4-sonnet-20250514)

### Getting Help

- Review the [Documentation](chief_of_staff_ai/README.md)
- Check [Migration Log](chief_of_staff_ai/MIGRATION_LOG.md) for system status
- Create an issue for bugs or feature requests

---

**Powered by Claude 4 Sonnet, React, and Advanced AI** - Transforming business communication into intelligent action.

**🎯 Your AI Chief of Staff**: Proactive intelligence, relationship management, and business insights at your fingertips. 