# AI Chief of Staff - Quick Start (Port 8080)

## 🚀 Quick Setup for Port 8080

### 1. **Configure Environment**
```bash
# Copy the configuration file
cp draft_mode_config.env .env

# Edit with your API keys
nano .env
```

### 2. **Required API Keys in .env**
```bash
# Claude 4 Opus API
ANTHROPIC_API_KEY=your_actual_claude_api_key

# Google OAuth (Port 8080)
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback

# Security
SECRET_KEY=your_random_secret_key_here
```

### 3. **Google Cloud OAuth Setup**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Edit your OAuth 2.0 Client ID
4. **Add Authorized Redirect URI**: `http://localhost:8080/auth/callback`
5. **Save changes**

### 4. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 5. **Run the Application**
```bash
python3 main.py
```

### 6. **Access the Application**
- **API Server**: http://localhost:8080
- **React Frontend**: http://localhost:3000 (if running separately)
- **Login**: Visit http://localhost:8080/login

## 📧 Draft Mode Features

✅ **Email Analysis**: AI analyzes incoming emails  
✅ **Draft Creation**: Creates intelligent responses  
✅ **Confidence Scoring**: 0-100% confidence levels  
✅ **Style Matching**: Matches your communication style  
✅ **Review Required**: Never auto-sends emails  
✅ **Edit Capability**: Edit drafts before sending  

## 🔧 API Endpoints (Port 8080)

```bash
# Get email drafts
GET http://localhost:8080/api/agents/email/drafts

# Send a draft
POST http://localhost:8080/api/agents/email/drafts/{draft_id}/send

# Edit a draft
PUT http://localhost:8080/api/agents/email/drafts/{draft_id}/edit

# System status
GET http://localhost:8080/api/enhanced-agent-system/status
```

## 🛡️ Security Configuration

The application runs with these safe defaults:
- **Draft Mode Enabled**: `ENABLE_EMAIL_DRAFT_MODE=true`
- **Auto-Send Disabled**: `ENABLE_AUTONOMOUS_EMAIL_RESPONSES=false`
- **High Send Threshold**: `AUTO_SEND_THRESHOLD=0.99`
- **Rate Limited**: Conservative limits on actions

## 📊 Monitoring

Check system health:
```bash
curl http://localhost:8080/api/enhanced-system/overview
```

## 🆘 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8080
lsof -i :8080

# Kill process if needed
kill -9 <PID>
```

### OAuth Errors
- Verify `GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback` in .env
- Ensure the same URI is added in Google Cloud Console
- Check that Google Client ID and Secret are correct

### API Key Issues
- Verify Claude API key is valid and has credits
- Test API key: https://console.anthropic.com/

## 🎯 Next Steps

1. **Test Draft Creation**: Send yourself a test email
2. **Review Drafts**: Check `/api/agents/email/drafts`
3. **Send a Draft**: Approve and send a draft
4. **Explore Features**: Try other AI capabilities

---

**Ready to Start!** 🚀

```bash
python3 main.py
```

Server will start on: **http://localhost:8080** 