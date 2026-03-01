# 🔒 Security Guide - CrowAgent™ Platform

## Overview

This document provides comprehensive security guidance for deploying CrowAgent™ publicly. Since you're sharing this application URL publicly on the internet, security is critical.

---

## ✅ Security Features Implemented

### 1. **No Hardcoded API Keys**
- ✅ `.env` file contains **only template comments**
- ✅ `.streamlit/secrets.toml` is in `.gitignore` (never committed)
- ✅ Dummy API key placeholders don't resemble real keys
- ✅ Git history cleaned of any real API keys

### 2. **Session-Only Storage**
- ✅ API keys stored in Streamlit session memory **only**
- ✅ Keys are **cleared automatically** when user closes browser
- ✅ No keys persisted to disk or database
- ✅ Each user manages their own keys independently

### 3. **Password Field Protection**
- ✅ API key input uses `type="password"` (masked in browser)
- ✅ Key is never displayed in UI (except masked validation)
- ✅ No logging or console output of keys
- ✅ Placeholder shows generic format, not real key

### 4. **Code-Level Security**
- ✅ No `print()` or `logging` statements dumping API keys
- ✅ API keys passed as function parameters (not global vars)
- ✅ Error messages don't include sensitive data
- ✅ Audit: All imports reviewed for secure handling

### 5. **Git Repository Protection**
- ✅ `.gitignore` includes:
  - `.env` files (any API keys in local dev)
  - `.streamlit/secrets.toml` (Streamlit secrets)
  - `__pycache__/` and Python bytecode
  - `.pytest_cache/` and test artifacts
- ✅ Remote origin: Public on GitHub (code, no secrets)

---

## ⚠️ What Users Must Know

### When Sharing This Link Publicly

**IMPORTANT**: Each person accessing this app must provide their own API key. Here's why:

1. **No shared key on server**: There is NO master API key stored on the server
2. **User authentication**: Each user enters their key independently in the sidebar
3. **Per-session**: API key is only valid for that user's session
4. **Automatic cleanup**: Key disappears when browser closes

### How It Works for Public Users

```
User 1                          User 2
   ↓                              ↓
Browser 1 session            Browser 2 session
   ↓                              ↓
Pastes Gemini key            Pastes Their OWN key
   ↓                              ↓
session_state.gemini_key     session_state.gemini_key
(User 1's key)               (User 2's key)
   ↓                              ↓
AI calls use User 1's key    AI calls use User 2's key
Charges against User 1's     Charges against User 2's
quota                        quota
```

---

## 🚀 Deployment Options by Security Level

### Option A: Local Development (Least Secure)
```bash
# Use .env file (OK for local dev only)
echo 'GEMINI_KEY=AIzaSy...' > .env
streamlit run app/main.py
```
✅ Good for: Personal testing
❌ Bad for: Production, shared servers, or public URLs

---

### Option B: Sidebar Input (Recommended for Public Sharing)
```
1. Run: streamlit run app/main.py
2. In sidebar, expand "🔑 API Keys (optional)"
3. Each user pastes their own Gemini API key
4. Key exists only in their session
5. Browser close = key cleared
```
✅ Good for: Public URLs, shared Codespaces
✅ Good for: No backend setup needed
✅ Good for: Each user bills to themselves
⚠️ Caveat: Users must know to get their own key

---

### Option C: Streamlit Secrets (For Staging/Testing on Shared Server)
```toml
# .streamlit/secrets.toml (NOT COMMITTED)
GEMINI_KEY = "AIzaSy..."
```
✅ Good for: Staging servers with controlled access
✅ Good for: .gitignore prevents accidental commits
⚠️ Warning: Only ONE key; shared cost
⚠️ Warning: Must manually manage file on server

---

### Option D: Environment Variables (Production Best Practice)
```bash
# Set in CI/CD or deployment platform
export GEMINI_KEY="AIzaSy..."

# Or in docker/container:
# ENV GEMINI_KEY="AIzaSy..."

# Or in Vercel/Heroku/Railway:
# GEMINI_KEY=AIzaSy... (set via dashboard)
```
✅ Good for: Production deployments
✅ Good for: Never exposes keys in code
✅ Good for: Managed by DevOps/deployment platform
✅ Good for: Easy rotation of keys
🎯 Recommended for: Public production apps

---

## 🔐 Security Checklist Before Going Public

- [ ] **No API keys in .env file** (should be comments only)
- [ ] **No API keys in .streamlit/secrets.toml** (should be comments only)
- [ ] **`.streamlit/secrets.toml` is in .gitignore**
- [ ] **Git history has no API keys** (check with: `git log --all -p | grep "AIza"`)
- [ ] **No `os.environ` writes for API keys** (prevents cross-session leaks)
- [ ] **README/docs tell users to bring their own keys**
- [ ] **Sidebar has security notice** ✓ (already added)
- [ ] **No plaintext keys in browser console** (check with F12 DevTools)
- [ ] **Session state clears on browser close** ✓ (Streamlit default)
- [ ] **No logging/print statements with keys** ✓ (already audited)
- [ ] **Placeholder keys don't look real** ✓ (changed to generic)

---

## 🛡️ What If Someone Gets Your API Key?

### If a key is accidentally exposed in code:

1. **Immediately rotate** the key in Google Cloud Console
2. **Delete the old key** to revoke access
3. **Remove from git history** (if committed):
   ```bash
   # Nuclear option: rewrite history
   git filter-branch --force --index-filter \
     'git rm --cached --ignore-unmatch .env' \
     --prune-empty --tag-name-filter cat -- --all
   
   git push origin --force --all --tags
   ```
4. **Force push to GitHub** to remove from history
5. **Generate new key** and use it

### With current setup:
❌ **Cannot accidentally expose keys** because:
- No hardcoded keys in code
- `.env` is ignored
- `secrets.toml` is ignored
- No file can have API keys that get committed

---

## 📊 Security Comparison: Before vs After

| Aspect | Before | After |
|--------|--------|-------|
| API key in .env | ❌ Yes (dummy) | ✅ Comments only |
| secrets.toml ignored | ❌ No | ✅ Yes |
| Placeholder looks real | ❌ Yes | ✅ No |
| Security notice in UI | ❌ No | ✅ Yes |
| Session-only storage | ✅ Yes | ✅ Yes |
| Password input field | ✅ Yes | ✅ Yes |
| Audit performed | ❌ No | ✅ Yes |

---

## 🔄 For Different Audiences

### For Individual Users (Local Dev)
```
You can use .env for convenience. Just:
1. Don't commit .env to git
2. Don't share your .env file
3. Everything else works automatically
```

### For Shared Codespace Instances
```
Use sidebar input:
1. Each person pastes their own key
2. Keys are never stored permanently
3. Perfect for public URLs
4. No backend setup needed
```

### For Production Deployment
```
Use environment variables:
1. Set GEMINI_KEY in deployment platform
2. Never in code or files
3. Rotate automatically
4. Manage via dashboard (Vercel, Heroku, etc.)
```

---

## 🔗 Related Documentation

- [API Key Activation Guide](API_KEY_ACTIVATION.md) - How to get and enter keys
- [Fix Summary](FIX_SUMMARY.md) - Technical details of recent fixes
- [Verification Checklist](VERIFICATION_CHECKLIST.md) - Testing procedures

---

## ❓ FAQ

**Q: Can users access other users' API keys?**
A: No. Each user has their own Streamlit session with isolated session state.

**Q: What happens if someone uses a public demonstration key?**
A: If it works, API calls charge **against that key's quota**. If it doesn't work (disabled/revoked), the AI Advisor won't function. This is why users must bring their own.

**Q: Is my source code safe to share on GitHub?**
A: Yes! With current setup, it's completely safe because:
- No API keys in code
- No API keys in committed files
- `.env` and `secrets.toml` are in `.gitignore`

**Q: Can I use a read-only API key?**
A: Yes! Consider creating a restricted key with only "generateContent" permission on Gemini if your platform supports it.

**Q: What if I deploy to Heroku/Vercel/Railway?**
A: Set `GEMINI_KEY` environment variable in their dashboard—never in code.

---

## 📞 Support

If you find a security issue:
1. **Don't post it publicly** in GitHub issues
2. Contact the author privately
3. Include steps to reproduce
4. Allow time for a fix before disclosure

---

**Status**: ✅ Security audit complete (Feb 21, 2026)  
**Last Updated**: Feb 21, 2026  
**Author**: CrowAgent™ Security Team
