#!/usr/bin/env python3
"""
Verify that the API key is being loaded correctly in the Streamlit app.
This test simulates what happens during app initialization.
"""
import os
import sys

# make sure prints support Unicode characters (emojis etc.)
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add project root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from dotenv import load_dotenv

# Load .env exactly as the app does
_env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
load_dotenv(_env_path)

print("=" * 70)
print("🔐 API KEY INITIALIZATION VERIFICATION")
print("=" * 70)

# Test 1: .env file exists
env_file_exists = os.path.isfile(_env_path)
print(f"\n1. .env file exists: {'✅ Yes' if env_file_exists else '❌ No'}")
print(f"   Path: {_env_path}")

# Test 2: GEMINI_KEY environment variable
gemini_key = os.getenv("GEMINI_KEY")
if gemini_key:
    masked = gemini_key[:10] + "..." + gemini_key[-4:]
    print(f"\n2. GEMINI_KEY loaded from environment:")
    print(f"   ✅ Key found: {masked}")
    print(f"   ✅ Valid format (starts with 'AIza'): {gemini_key.startswith('AIza')}")
else:
    print(f"\n2. GEMINI_KEY loaded: ❌ Not found")

# Test 3: Simulate _get_secret function
def _get_secret(key: str, default: str = "") -> str:
    try:
        # In real app, this checks st.secrets first
        # For now, we skip that and go directly to os.getenv
        return os.getenv(key, default)
    except Exception:
        return default

loaded_key = _get_secret("GEMINI_KEY", "")
print(f"\n3. _get_secret() function result:")
if loaded_key:
    print(f"   ✅ Key loaded via _get_secret(): {loaded_key[:10]}...{loaded_key[-4:]}")
    print(f"   ✅ Session state would be: st.session_state.gemini_key = '{loaded_key[:10]}...'")
else:
    print(f"   ❌ Key not loaded")

# Test 4: Check what the activation check would see
_akey = loaded_key  # This is what `_akey = st.session_state.get("gemini_key", "")` does
print(f"\n4. Activation message check:")
print(f"   Current key in session: {repr(_akey) if _akey else '(empty)'}")
if not _akey:
    print(f"   ❌ Would show activation message")
else:
    print(f"   ✅ Would hide activation message (key present)")

print("\n" + "=" * 70)
print("✅ EXPECTED BEHAVIOR:")
print("=" * 70)
print("""
When you run: streamlit run app/main.py

1. .env file is loaded (with your GEMINI_KEY)
2. Environment variable GEMINI_KEY is set
3. Session state initializes with: gemini_key = (your key value)
4. In AI Advisor tab:
   - Check: if not _akey → False (key exists)
   - Result: Activation message is HIDDEN ✅
   - Chat interface is VISIBLE and ready ✅
5. Sidebar shows: ✓ Gemini AI Advisor ready
""")
print("=" * 70)
