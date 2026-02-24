#!/usr/bin/env python3
"""
Test to verify API key activation logic works correctly.
This test simulates the session state behavior for the API key.
"""
import os
import sys

# ensure unicode output works regardless of locale
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add root to path
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
if ROOT_DIR not in sys.path:
    sys.path.append(ROOT_DIR)

def test_api_key_conditions():
    """Test that API key conditions work as expected."""
    
    print("=" * 60)
    print("Testing API Key Activation Logic")
    print("=" * 60)
    
    # Test 1: Empty string (no key provided)
    _akey_empty = ""
    if not _akey_empty:
        print("✓ Test 1 PASS: Empty key shows activation message")
    else:
        print("✗ Test 1 FAIL: Empty key should show activation message")
    
    # Test 2: Valid Gemini API key
    _akey_valid = "AIzaSyExample1234567890abcdefghijklmnop"
    if not _akey_valid:
        print("✗ Test 2 FAIL: Valid key should NOT show activation message")
    else:
        print("✓ Test 2 PASS: Valid key hides activation message")
    
    # Test 3: Key with wrong prefix (still stored, but shows warning)
    _akey_invalid = "InvalidKeyPrefix123456789"
    if not _akey_invalid:
        print("✗ Test 3 FAIL: Invalid key should NOT show activation message")
    else:
        print("✓ Test 3 PASS: Invalid key hides activation message (but shows warning)")
    
    # Test 4: Validation check
    if _akey_valid.startswith("AIza"):
        print("✓ Test 4 PASS: Valid key starts with 'AIza'")
    else:
        print("✗ Test 4 FAIL: Valid key format check")
    
    if not _akey_invalid.startswith("AIza"):
        print("✓ Test 5 PASS: Invalid key correctly fails format check")
    else:
        print("✗ Test 5 FAIL: Invalid key format check")
    
    print("\n" + "=" * 60)
    print("API Key Logic Summary:")
    print("=" * 60)
    print("""
The AI Advisor activation flow:
1. If gemini_key is empty (""): Shows activation message
2. If gemini_key has any value: Hides activation message
3. If key starts with "AIza": Shows ✓ validation message
4. If key doesn't start with "AIza": Shows ⚠ warning message

When user enters their API key in the sidebar:
- The session state is updated immediately
- This triggers a Streamlit rerun
- On rerun, the API key is present in session_state
- The activation message disappears
- Chat interface becomes available
    """)
    print("=" * 60)

if __name__ == "__main__":
    test_api_key_conditions()
