# Fix OAuth Error 401: invalid_client

## 🚨 Current Error
```
Error 401: invalid_client
The OAuth client was not found.
```

## ✅ Solution Steps

### Step 1: Update Google Cloud Console

1. **Go to**: https://console.cloud.google.com/
2. **Navigate to**: APIs & Services → Credentials
3. **Find your OAuth 2.0 Client ID** (it should show your project name)
4. **Click Edit** (pencil icon)

### Step 2: Fix Redirect URIs

**In the OAuth client configuration:**

**✅ Add this URI:**
```
http://localhost:8080/auth/callback
```

**❌ Remove any old URIs like:**
```
http://localhost:5000/auth/callback
http://localhost:3000/auth/callback
```

### Step 3: Verify Client ID and Secret

**Copy from Google Cloud Console:**
- Client ID (looks like: `123456789-abcdef.apps.googleusercontent.com`)
- Client Secret (looks like: `GOCSPX-abcdef123456`)

### Step 4: Update .env File

```bash
# Your actual values from Google Cloud Console
GOOGLE_CLIENT_ID=your_actual_client_id_from_console
GOOGLE_CLIENT_SECRET=your_actual_client_secret_from_console
GOOGLE_REDIRECT_URI=http://localhost:8080/auth/callback
```

### Step 5: Test the Fix

1. **Save all changes** in Google Cloud Console
2. **Restart your application**:
   ```bash
   python3 main.py
   ```
3. **Visit**: http://localhost:8080/login
4. **Try OAuth again**

## 🔍 Common Issues

### Issue 1: Wrong Client ID
- Make sure you're copying the full Client ID from Google Cloud Console
- It should end with `.apps.googleusercontent.com`

### Issue 2: Wrong Project
- Ensure you're in the correct Google Cloud project
- The project should match where you created the OAuth client

### Issue 3: API Not Enabled
- In Google Cloud Console, go to APIs & Services → Library
- Enable these APIs:
  - Gmail API
  - Google Calendar API
  - Google+ API (if needed)

### Issue 4: Redirect URI Mismatch
- The URI in .env must EXACTLY match the one in Google Cloud Console
- Including `http://` and the exact port number

## 🎯 Quick Verification

After fixing, test with:
```bash
curl "http://localhost:8080/auth/google"
```

This should redirect to Google OAuth (not show an error).

## 🆘 Still Having Issues?

1. **Double-check** the Client ID and Secret are correct
2. **Wait 5-10 minutes** after saving changes in Google Cloud Console
3. **Clear browser cache** and try again
4. **Check Google Cloud Console** for any error messages 