# 🔑 API Key Activation Guide - CrowAgent™ Platform

## ✅ What Was Fixed

The API key initialization had a conflict that prevented environment variables from being loaded properly:

### The Problem
1. **Duplicate Initialization**: Session state was being initialized twice with conflicting logic
   - First initialization at line 575: Set all keys to empty strings
   - Second initialization at line 1821: Tried to load from environment (but never executed)

2. **Execution Issue**: The second initialization checked `if "gemini_key" not in st.session_state`, but since it was already added in the first initialization, this condition was always `False`, causing the environment variable loading to never run

3. **Result**: Gemini API keys provided via environment variables or secrets were not being loaded

### The Solution
- **Consolidated Initialization**: Moved `_get_secret()` function before session state initialization
- **Unified Logic**: Now there's only ONE place where each key is initialized, checking environment variables first
- **Removed Dead Code**: Eliminated the duplicate initialization attempt that never executed

## 🚀 How to Use the AI Advisor

### Option 1: Via Sidebar Text Input (Recommended)
1. Run the app: `streamlit run app/main.py`
2. Look for the collapsible **"🔑 API Keys (optional)"** section in the left sidebar
3. Click to expand it
4. Paste your Gemini API key into the text field labeled **"Gemini API key (for AI Advisor)"**
5. The app will validate your key:
   - ✓ Green checkmark = Valid key starting with "AIza"
   - ⚠ Orange warning = Key doesn't start with "AIza" (double-check your key)
6. Navigate to the **"🤖 AI Advisor"** tab
7. The activation message should now be **gone** and the chat interface should be visible

### Option 2: Via Environment Variables (For Production)
1. Create a `.env` file in the project root:
   ```
   GEMINI_KEY=AIzaSyExample1234567890abcdefghijklmnop
   MET_OFFICE_KEY=your-met-office-key-here
   ```
2. Run the app:
   ```
   streamlit run app/main.py
   ```
3. The keys will be loaded automatically on startup
4. The AI Advisor will be ready to use without manual input

### Option 3: Via Streamlit Secrets (Production)
1. Create `.streamlit/secrets.toml`:
   ```toml
   GEMINI_KEY = "AIzaSyExample1234567890abcdefghijklmnop"
   MET_OFFICE_KEY = "your-met-office-key-here"
   ```
2. Run the app:
   ```
   streamlit run app/main.py
   ```
3. Keys load automatically without being stored in memory only

## 🔄 How the Activation Flow Works

### Initial Load
```
1. App starts
2. Session state initialized with empty strings
3. _get_secret() checks environment variables
4. If found, session_state.gemini_key = environment value
5. If not found, session_state.gemini_key = ""
6. Sidebar renders (user can override via text input)
```

### User Provides Key via Sidebar
```
1. User expands "🔑 API Keys" in sidebar
2. User pastes Gemini API key into password field
3. Sidebar validates key:
   - Checks if key is non-empty: ✓
   - Checks if starts with "AIza": ✓ (valid) or ⚠ (invalid format)
4. Session state updated: session_state.gemini_key = "AIzaSy..."
5. Streamlit reruns the entire script
6. On rerun, AI Advisor tab checks: if not _akey → False (key exists!)
7. Activation message hidden, chat interface shown
```

### Checking the Status
- **In Sidebar**: Validation message shows:
  - ✓ "Gemini AI Advisor ready" = Key accepted
  - ⚠ "Gemini key should start with 'AIza'" = Invalid format
  - (nothing) = No key provided yet

- **In AI Advisor Tab**:
  - **Activation Message visible** → No API key in session state (enter it in sidebar)
  - **"✨ Click a question to start..."** → API key is active, ready to use
  - **"Ask the AI Advisor:"** → Chat interface ready for input

## 🔍 Troubleshooting

### Issue: Activation message still shows after entering key
**Solution**: 
1. Verify you copied the COMPLETE API key (usually starts with "AIza")
2. Check the sidebar shows ✓ or ⚠ validation message
3. Switch to another tab and back to AI Advisor tab
4. If still not working, restart the app: press Ctrl+C and run again

### Issue: Getting "⚠ Gemini key should start with 'AIza'"
**Solution**:
1. Double-check your API key format
2. Make sure you didn't accidentally copy extra spaces
3. Get a new key from https://aistudio.google.com
4. Keys always start with "AIza"

### Issue: "ModuleNotFoundError" or import errors
**Solution**:
1. Ensure all dependencies are installed: `pip install -r requirements.txt`
2. Verify Python environment: `python --version` (should be 3.8+)
3. Check that you're running from the project root directory

## 📋 Code Changes Summary

**File: `/workspaces/crowagent-platform/app/main.py`**

- **Lines 568-591**: Consolidated session initialization with environment variable loading
- **Lines 1810 onwards**: Removed duplicate initialization code
- **Line 1168**: API key retrieval (unchanged): `_akey = st.session_state.get("gemini_key", "")`
- **Line 1184**: Activation check (unchanged): `if not _akey:` → shows activation message

The logic is now clean, efficient, and properly handles all three ways to provide the API key.

## ✨ Next Steps

Once the API Advisor is activated:
1. Click one of the suggested starter questions or type your own
2. The AI will run real physics simulations on your query
3. It will analyze different building scenarios
4. You'll get evidence-based recommendations with financial and environmental metrics

Enjoy your CrowAgent™ AI Advisor experience! 🌿
