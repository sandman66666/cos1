# AI Chief of Staff - Enhanced Intelligence Platform

🤖 **Your intelligent business intelligence assistant powered by Claude 4 Sonnet and React**

The AI Chief of Staff is a comprehensive platform that transforms your Gmail and Calendar into a proactive business intelligence system with real-time insights, relationship management, and AI-powered assistance.

## 🌟 Core Features

### **📊 React Intelligence Dashboard**
- **Real-time Intelligence Metrics**: Live tracking of business insights and entity relationships
- **Proactive Business Insights**: AI-generated strategic recommendations with filtering and confidence scoring
- **Entity Network Visualization**: Interactive Topics Brain and Relationship Intelligence panels
- **Intelligence Assistant**: Context-aware AI chat with access to your complete business knowledge

### **🧠 Advanced AI Processing**
- **Claude 4 Sonnet Integration**: Comprehensive email analysis with business context understanding
- **Comprehensive Context Stories**: Rich narratives explaining the full business context of each email and task
- **Strategic Importance Scoring**: AI-calculated priority levels with confidence metrics
- **Real-time Processing**: Continuous intelligence generation as new data arrives

### **📅 Meeting Intelligence & Preparation**
- **Automated Meeting Preparation**: AI-generated prep tasks with attendee intelligence
- **Meeting Context Stories**: Rich background information for every calendar event
- **Attendee Analysis**: Strategic value assessment and communication history
- **Proactive Scheduling**: Meeting recommendations based on relationship intelligence

### **👥 Professional Network Management**
- **Relationship Intelligence**: Comprehensive tracking of professional relationships
- **Engagement Scoring**: Quantified relationship strength with trend analysis
- **Communication Pattern Analysis**: Understanding of interaction styles and frequencies
- **Relationship Decay Prediction**: Proactive suggestions for relationship maintenance

### **🔄 Real-time Intelligence System**
- **Continuous Processing**: Background analysis of emails and calendar events
- **Proactive Insight Generation**: Strategic business recommendations
- **Pattern Detection**: Relationship trends, topic momentum, and opportunity identification
- **Entity-Centric Architecture**: Everything connected through intelligent relationship mapping

## 🚀 Quick Start

### Prerequisites
- **Node.js 16+** for React frontend
- **Python 3.10+** for backend services
- **Google Cloud Project** with Gmail and Calendar API access
- **Anthropic API key** for Claude 4 Sonnet

### Installation

1. **Clone and Setup Backend**:
   ```bash
   git clone <repository-url>
   cd chief_of_staff_ai
   pip install -r requirements.txt
   ```

2. **Environment Configuration**:
   Create `.env` file in project root:
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
   
   # Intelligence Settings
   EMAIL_FETCH_LIMIT=50
   EMAIL_DAYS_BACK=30
   ENABLE_REAL_TIME_PROCESSING=true
   ENABLE_PREDICTIVE_ANALYTICS=true
   ```

3. **React Frontend Setup**:
   ```bash
   cd frontend
   npm install
   npm run build
   ```

4. **Database Initialization**:
   ```bash
   python migrate_intelligence.py
   ```

5. **Start the Application**:
   ```bash
   python ../main.py
   ```

6. **Access Intelligence Dashboard**:
   Open http://localhost:5000

## ⚙️ Architecture

### **Backend System (Flask + SQLAlchemy)**
```
chief_of_staff_ai/
├── models/
│   ├── database.py              # Core entity models
│   └── enhanced_models.py       # Intelligence-enhanced models
├── processors/
│   ├── email_intelligence.py    # Email AI processing
│   ├── intelligence_engine.py   # Core intelligence engine
│   ├── realtime_processor.py    # Real-time processing
│   ├── unified_entity_engine.py # Entity management
│   └── analytics/
│       └── predictive_analytics.py # Business predictions
├── ingest/
│   ├── gmail_fetcher.py         # Gmail API integration
│   └── calendar_fetcher.py      # Calendar API integration
├── api/
│   └── enhanced_endpoints.py    # Intelligence APIs
└── auth/
    └── gmail_auth.py            # OAuth authentication
```

### **Frontend System (React + TypeScript)**
```
frontend/
├── src/
│   ├── App.tsx                  # Main intelligence dashboard
│   ├── components/              # React components
│   ├── types/                   # TypeScript interfaces
│   ├── hooks/                   # Custom React hooks
│   └── utils/                   # Utility functions
├── public/                      # Static assets
└── package.json                # Dependencies
```

### **Intelligence Pipeline**
```
📧 Gmail/Calendar APIs → 🔄 Real-time Processor → 🧠 Claude 4 Analysis → 
📊 Intelligence Engine → 💾 Entity Database → ⚡ React Dashboard
```

## 📋 Detailed Usage

### **Intelligence Dashboard Workflows**

#### **1. Initial Setup & Sync**
1. **Authentication**: Sign in with Google and authorize access
2. **Intelligence Sync**: Click "Sync Intelligence" to process emails and calendar
3. **Dashboard Overview**: View real-time intelligence metrics and insights

#### **2. Meeting Preparation**
1. **Generate Meeting Intelligence**: AI analyzes upcoming meetings
2. **Attendee Intelligence**: Review relationship context and strategic importance
3. **Preparation Tasks**: Access AI-generated prep tasks and talking points
4. **Meeting Context**: Understand business context and historical interactions

#### **3. Business Insights Management**
1. **Proactive Insights**: Filter by type (relationship, meeting, opportunity, urgent)
2. **Insight Analysis**: Click insights for detailed analysis and recommendations
3. **Confidence Scoring**: Understand AI confidence levels (0-100%)
4. **Action Tracking**: Follow up on insight recommendations

#### **4. Relationship Intelligence**
1. **Professional Network**: Navigate people with engagement scoring
2. **Communication Patterns**: Understand interaction frequency and style
3. **Relationship Maintenance**: Receive proactive outreach suggestions
4. **Strategic Value**: Assess business value of relationships

#### **5. AI Assistant Interaction**
1. **Context-Aware Chat**: Ask questions about your business intelligence
2. **Knowledge Access**: AI has access to your complete email and calendar context
3. **Strategic Recommendations**: Get business advice based on your data
4. **Insight Explanations**: Understand how AI generated specific insights

### **Advanced Features**

#### **Real-time Intelligence Processing**
- **Continuous Analysis**: Background processing of new emails and events
- **Proactive Notifications**: AI alerts for important business opportunities
- **Pattern Detection**: Automatic identification of business trends
- **Relationship Monitoring**: Tracking of communication patterns and decay

#### **Entity-Centric Intelligence**
- **Topic Intelligence**: Business themes with momentum tracking
- **Person Intelligence**: Comprehensive relationship analysis
- **Task Intelligence**: Context-aware action items with business rationale
- **Calendar Intelligence**: Meeting preparation and strategic importance

## 🔧 Advanced Configuration

### **Google Cloud Setup**

1. **Create Google Cloud Project**:
   - Enable Gmail API and Google Calendar API
   - Create OAuth 2.0 credentials for web application
   - Add authorized redirect URI: `http://localhost:5000/auth/google/callback`

2. **Required OAuth Scopes**:
   ```
   https://www.googleapis.com/auth/gmail.readonly
   https://www.googleapis.com/auth/calendar.readonly
   https://www.googleapis.com/auth/userinfo.profile
   https://www.googleapis.com/auth/userinfo.email
   ```

### **Anthropic API Setup**

1. **Get Claude API Access**:
   - Sign up at [Anthropic Console](https://console.anthropic.com/)
   - Generate API key for Claude 4 Sonnet
   - Configure usage limits and monitoring

### **Intelligence Configuration**

```env
# Processing Settings
EMAIL_FETCH_LIMIT=50              # Max emails per sync
EMAIL_DAYS_BACK=30               # Days to look back
CALENDAR_DAYS_FORWARD=14         # Days ahead for calendar
CALENDAR_DAYS_BACK=3             # Days back for calendar

# AI Settings
CLAUDE_MODEL=claude-4-sonnet-20250514
AI_ANALYSIS_DEPTH=comprehensive   # or basic, detailed
CONFIDENCE_THRESHOLD=0.7          # Minimum confidence for insights

# Real-time Settings
ENABLE_REAL_TIME_PROCESSING=true
REAL_TIME_INTERVAL=60            # Seconds between updates
ENABLE_PROACTIVE_INSIGHTS=true
```

## 🔍 API Reference

### **Core Intelligence Endpoints**
- `GET /api/intelligence-metrics` - Real-time intelligence quality metrics
- `GET /api/intelligence-insights` - Proactive business insights
- `POST /api/proactive-insights/generate` - Generate new insights

### **Entity Management**
- `GET /api/tasks` - Enhanced tasks with context stories
- `GET /api/people` - Relationship intelligence
- `GET /api/topics` - Topic momentum and intelligence
- `GET /api/enhanced-calendar-events` - Meeting intelligence

### **Intelligence Operations**
- `POST /api/trigger-email-sync` - Unified intelligence sync
- `POST /api/calendar/generate-meeting-intelligence` - Meeting preparation
- `POST /api/chat-with-knowledge` - AI assistant with business context

### **Real-time Features**
- `WebSocket /ws/intelligence` - Live intelligence updates
- `GET /api/status` - System health and processing status

## 🧪 Development & Testing

### **Development Setup**
```bash
# Backend development with auto-reload
python main.py --debug

# Frontend development with hot reload
cd frontend && npm start

# Database migrations
python migrate_intelligence.py
```

### **Testing**
```bash
# Backend API testing
python -m pytest tests/

# React component testing
cd frontend && npm test

# Integration testing
python test_integration.py

# End-to-end testing
npm run test:e2e
```

### **Debugging**
```bash
# Enable verbose logging
export DEBUG=True
export LOG_LEVEL=DEBUG

# Test authentication
python test_auth.py

# Test AI processing
python test_claude_integration.py
```

## 🚀 Production Deployment

### **Heroku Deployment**
```bash
# Configure buildpacks
heroku buildpacks:add heroku/nodejs
heroku buildpacks:add heroku/python

# Environment variables
heroku config:set GOOGLE_CLIENT_ID=...
heroku config:set ANTHROPIC_API_KEY=...
heroku config:set SECRET_KEY=...

# Deploy
git push heroku main
```

### **Docker Deployment**
```dockerfile
# Multi-stage build with React and Flask
FROM node:16 AS frontend
COPY frontend/ /app/frontend/
RUN cd /app/frontend && npm install && npm run build

FROM python:3.10
COPY . /app/
COPY --from=frontend /app/frontend/build /app/frontend/build
RUN pip install -r requirements.txt
CMD ["python", "main.py"]
```

## 🔒 Security & Privacy

### **Data Handling**
- **Read-only Access**: Only reads emails and calendar events
- **Local Processing**: All intelligence analysis happens on your server
- **No Data Sharing**: Your business intelligence stays completely private
- **Encrypted Storage**: Sensitive data encrypted at rest
- **Minimal Scopes**: Only requests necessary Google permissions

### **Privacy Features**
- **User Control**: Complete control over data processing and retention
- **Audit Trail**: Full logging of all AI processing and decisions
- **Data Deletion**: Easy cleanup and data removal capabilities
- **Transparent AI**: Clear explanations of how insights are generated

## 🤝 Contributing

### **Development Workflow**
1. Fork repository and create feature branch
2. Follow TypeScript/Python code standards
3. Add comprehensive tests for new features
4. Update documentation for API changes
5. Submit pull request with clear description

### **Code Standards**
- **Backend**: Python type hints, SQLAlchemy patterns, Flask best practices
- **Frontend**: TypeScript strict mode, React hooks, component patterns
- **Testing**: Unit tests, integration tests, E2E coverage
- **Documentation**: Clear API documentation and user guides

## 🆘 Troubleshooting

### **Common Issues**

**No Intelligence Data**:
- Verify Google OAuth configuration
- Check Gmail/Calendar API enablement
- Confirm Anthropic API key validity
- Run database migration

**Real-time Updates Not Working**:
- Check WebSocket connection in browser console
- Verify real-time processing is enabled
- Ensure Flask app is running in production mode

**AI Assistant Not Responding**:
- Verify Anthropic API key and usage limits
- Check that business intelligence data has been processed
- Ensure Claude model access

**React Build Issues**:
- Clear node_modules and reinstall dependencies
- Check Node.js version compatibility
- Verify Tailwind CSS configuration

### **Performance Optimization**
- **Database**: Use indexes for entity relationships
- **API**: Implement caching for frequent queries
- **React**: Code splitting and lazy loading
- **Processing**: Batch AI operations for efficiency

## 📄 License

This project is licensed under the MIT License - see LICENSE file for details.

---

**🎯 Your AI Chief of Staff**: Transforming business communication into intelligent action through advanced AI, real-time processing, and proactive insights.

**Built with Claude 4 Sonnet, React, TypeScript, and Modern Python** - Professional business intelligence for the modern workplace.
