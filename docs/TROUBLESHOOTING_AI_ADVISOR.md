# 🔧 Troubleshooting: AI Advisor Not Working

## 📌 Problem Summary

You're seeing one of these issues:
1. **"Activate AI Advisor with a free Gemini API key"** message persists
2. **Error: Gemini API error 404**: models/gemini-1.5-flash is not found

## ✅ Solution

The issue has been fixed! The app was using an older API endpoint. Here's what changed:

### **What We Fixed**

| Issue | Before | After |
|-------|--------|-------|
| API Endpoint | `v1beta` | `v1` (stable) |
| Model | `gemini-1.5-flash` | `gemini-1.5-pro` |
| API Validation | Format only (`AIza...`) | Actual key test |

---

## 🚀 How to Verify Your API Key

### **Method 1: Automatic Test (Recommended)**

```bash
cd /workspaces/crowagent-platform
python3 verify_gemini_key.py "AIzaSy_YOUR_KEY_HERE"
```

**Expected output:**
```
✅ SUCCESS - Your API key works!
   Endpoint: v1
   Model: gemini-1.5-pro
```

### **Method 2: Via Environment Variable**

```bash
export GEMINI_KEY="AIzaSy_YOUR_KEY_HERE"
python3 verify_gemini_key.py
```

---

## 🔑 Getting a New API Key

If your key doesn't work, get a fresh one:

1. **Go to**: https://aistudio.google.com
2. **Sign in** with your Google account (any account works - doesn't need to be your organization's)
3. **Click**: "Get API key"
4. **Click**: "Create API key in new project"
5. **Copy** the key (starts with `AIza...`)

### ⚠️ Important Notes

- ✅ The API key is completely **free** for personal use
- ✅ **No credit card required**
- ✅ You get **1,500 requests/day** free
- ✅ The key only works for Gemini API, not other Google services
- ⏰ If you created your key a while ago, you might need to create a new one

---

## 🔄 In the App: How to Enter Your Key

### **On First Visit**
1. Open the app in your browser
2. Look at the **left sidebar**
3. Click **"🔑 API Keys (optional)"** to expand
4. You'll see a password field labeled **"Gemini API key (for AI Advisor)"**
5. Paste your API key there
6. You should see: **✅ Gemini AI Advisor ready**

### **What the Validation Messages Mean**

| Message | Meaning | Next Step |
|---------|---------|-----------|
| ✓ Gemini AI Advisor ready | ✅ Key is valid | Go to 🤖 AI Advisor tab |
| ⚠ Gemini key should start with 'AIza' | ⚠️ Format might be wrong | Check you copied the full key |
| ❌ Invalid API key | ❌ Key is rejected | Get a new one from aistudio.google.com |
| ❌ API key blocked (check permissions) | ❌ Permissions issue | Check Google Cloud Console |

### **Then Navigate to AI Advisor**

1. Click on the **"🤖 AI Advisor"** tab at the top
2. The "Activate AI Advisor" message should **disappear**
3. You should see **"✨ Click a question to start..."**
4. Click any question or type your own

---

## 🐛 If It Still Doesn't Work

### **Error: "404: models/gemini-1.5-pro is not found"**

This means your API key doesn't have access to Gemini models. Try:

```bash
# Test your key
python3 verify_gemini_key.py "YOUR_KEY"
```

**Common causes:**
- ❌ Using a **Cloud API key** instead of **Gemini Studio key**
- ❌ Key is from an old Google Cloud project
- ❌ Key has been **revoked** or **deleted**
- ❌ API not **enabled** for your project

**Solution:**
1. Go to https://aistudio.google.com (NOT console.cloud.google.com)
2. Delete your old key
3. Click "Get API key"
4. Click "Create API key in **new project**"
5. Copy and use the new key

### **Error: "401 Unauthorized"**

Your API key is invalid or expired.

**Solution:**
1. Go to https://aistudio.google.com
2. Delete the key
3. Create a new one
4. Try again

### **Activation message still shows**

Check:
- [ ] Did you **paste** the key into the sidebar input field?
- [ ] Is it showing **✓ or ❌** validation message?
- [ ] Did you **press Enter** or click outside the field?
- [ ] Try **refreshing** the page (F5)
- [ ] Try **clearing cache** (Ctrl+Shift+Delete)

---

## 🔬 Technical Details

### **What Changed in the Code**

**Before (broken):**
```python
GEMINI_MODEL = "gemini-1.5-flash"
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"
```

**After (fixed):**
```python
GEMINI_MODEL = "gemini-1.5-pro"
GEMINI_API_VERSION = "v1"  # Stable endpoint
GEMINI_URL = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
```

### **Why This Fixes It**

1. **`v1beta` → `v1`**: The beta endpoint had unstable model support. `v1` is more reliable.
2. **`gemini-1.5-flash` → `gemini-1.5-pro`**: Flash is being deprecated. Pro is the current standard.
3. **Better validation**: Now actually tests your key instead of just checking format.
4. **Better error messages**: Tells you exactly what went wrong.

---

## 📞 Need Help?

Try these in order:

1. **Run the verification script**: `python3 verify_gemini_key.py "YOUR_KEY"`
2. **Check the error message** - it tells you what's wrong
3. **Regenerate your API key** at https://aistudio.google.com
4. **Refresh your browser** (Ctrl+Shift+R)
5. **Check your internet connection**

---

## ✨ Once It Works

You'll see:

1. Sidebar shows: **✓ Gemini AI Advisor ready**
2. AI Advisor tab shows: **"✨ Click a question to start..."**
3. Click any question and the AI will:
   - 🏢 Analyze buildings
   - 📊 Run physics simulations
   - 💡 Generate recommendations
   - 💰 Calculate costs and payback periods

---

## 🚀 Quick Restart

To restart fresh:

```bash
# 1. Stop the app (if running)
# Ctrl+C in the terminal

# 2. Clear browser cache
# F12 → Application → Clear Storage

# 3. Get a fresh API key
# https://aistudio.google.com → Get API key → Create new

# 4. Restart the app
streamlit run app/main.py

# 5. Paste new key in sidebar

# 6. Go to AI Advisor tab
```

---

**Status**: ✅ Fixed  
**Tested**: Feb 21, 2026  
**Last Updated**: Feb 21, 2026
