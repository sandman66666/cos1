# AI Chief of Staff

An intelligent email management and business intelligence system powered by Claude 4 Sonnet that transforms your Gmail into a comprehensive business insights platform.

## 🌟 Features

### Enhanced AI Intelligence
- **Deep Email Analysis**: Claude 4 Sonnet processes emails for comprehensive understanding
- **Business Intelligence**: Automatically extracts decisions, opportunities, challenges, and trends
- **People Network Analysis**: Maps relationships and communication patterns
- **Project Classification**: Organizes emails by business initiatives
- **Sentiment & Urgency Scoring**: AI-powered email prioritization

### 4-Section Dashboard
1. **Business Knowledge**: Overview metrics, key topics, opportunities, and challenges
2. **Email Insights**: AI-analyzed emails with summaries and categorization
3. **Tasks**: Enhanced actionable items with context and confidence scores
4. **People**: Professional network with relationship mapping and insights

### Smart Processing
- **Intelligent Filtering**: Only processes unreplied emails
- **Force Refresh**: Re-analyze existing emails with updated AI insights
- **Multi-tenant**: Secure per-user data isolation
- **Enhanced Task Extraction**: Context-aware actionable items

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Gmail account with API access
- Anthropic Claude API key

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/sandman66666/cos1.git
cd cos1
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Setup**
Create a `.env` file with:
```env
# Google OAuth (required)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/google/callback

# Claude API (required)
ANTHROPIC_API_KEY=your_anthropic_api_key

# Optional configurations
SECRET_KEY=your_secret_key
DEBUG=True
PORT=8080
```

4. **Run the application**
```bash
python3 main.py
```

5. **Access the dashboard**
Open http://localhost:8080 in your browser

## 📋 Usage

1. **Sign in with Google** and grant Gmail permissions
2. **Click "Process Emails"** to fetch and analyze recent emails
3. **Explore the 4 tabs**:
   - View business insights and metrics
   - Read AI-summarized emails
   - Manage extracted tasks
   - Explore your professional network

### Advanced Features
- **Force Refresh**: Use the checkbox to re-analyze existing emails
- **Flush Database**: Clean slate for testing (button in dashboard)
- **Intelligent Filtering**: System automatically focuses on actionable emails

## 🏗️ Architecture

- **Frontend**: Modern HTML/CSS/JavaScript with responsive design
- **Backend**: Flask web application
- **AI Engine**: Claude 4 Sonnet for email intelligence
- **Database**: SQLAlchemy with SQLite (development) / PostgreSQL (production)
- **Authentication**: Google OAuth with Gmail API integration

## 🔧 Configuration

The system supports both local development and cloud deployment (Heroku ready).

Key components:
- `chief_of_staff_ai/`: Core AI processing modules
- `templates/`: Web interface templates
- `Spec_and_architecture/`: Project specifications and rules

## 🤝 Contributing

This project follows the specifications in `Spec_and_architecture/rules.txt` for development guidelines.

## 📄 License

Private project - All rights reserved.

---

**Powered by Claude 4 Sonnet** - Transforming email chaos into business intelligence. 