#!/usr/bin/env python3
"""
🔬 API Key and Model Verification Script
Test if your Gemini API key works with the new v1 endpoint and gemini-1.5-pro model
"""

import sys
import requests

def test_gemini_api(api_key: str) -> dict:
    """Test if the API key works with the new endpoint and model."""
    
    print("\n" + "=" * 80)
    print("🔬 GEMINI API VERIFICATION TEST")
    print("=" * 80)
    
    # 1. Check API key format
    print("\n[1] API Key Format Check")
    print("-" * 80)
    if not api_key:
        print("❌ No API key provided")
        return {"success": False, "error": "Empty API key"}
    
    if not api_key.startswith("AIza"):
        print(f"⚠️  Key doesn't start with 'AIza': {api_key[:10]}...")
        print("    (This might still work, but format is unexpected)")
    else:
        print(f"✅ Key format looks correct: {api_key[:10]}...")
    
    # 2. Test v1 endpoint with gemini-1.5-pro
    print("\n[2] Testing v1 API Endpoint (Stable)")
    print("-" * 80)
    
    url = "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent"
    payload = {
        "contents": [{"parts": [{"text": "Say 'Hello' in one word only"}]}],
        "generationConfig": {"maxOutputTokens": 10}
    }
    
    try:
        resp = requests.post(
            url,
            params={"key": api_key},
            json=payload,
            timeout=10
        )
        
        print(f"HTTP Status: {resp.status_code}")
        
        if resp.status_code == 200:
            print("✅ API call successful!")
            result = resp.json()
            if "candidates" in result and result["candidates"]:
                text = result["candidates"][0]["content"]["parts"][0]["text"]
                print(f"   Model response: '{text}'")
            return {"success": True, "endpoint": "v1", "model": "gemini-1.5-pro"}
        
        elif resp.status_code == 401:
            print("❌ Authentication failed - Invalid or expired API key")
            try:
                print(f"   Error: {resp.json()['error']['message']}")
            except:
                pass
            return {"success": False, "error": "Invalid API key"}
        
        elif resp.status_code == 403:
            print("❌ Permission denied - Check Google Cloud Console settings")
            try:
                print(f"   Error: {resp.json()['error']['message']}")
            except:
                pass
            return {"success": False, "error": "Permission denied"}
        
        elif resp.status_code == 404:
            print("⚠️  Model not found with v1 endpoint")
            print("   Trying v1beta endpoint as fallback...")
            
            # Try v1beta as fallback
            url_beta = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent"
            resp_beta = requests.post(
                url_beta,
                params={"key": api_key},
                json=payload,
                timeout=10
            )
            
            if resp_beta.status_code == 200:
                print("✅ v1beta endpoint works!")
                return {"success": True, "endpoint": "v1beta", "model": "gemini-1.5-pro", "note": "Using fallback v1beta"}
            else:
                print(f"❌ v1beta also failed: {resp_beta.status_code}")
                return {"success": False, "error": "Model not available on either endpoint"}
        
        else:
            print(f"❌ Unexpected error: {resp.status_code}")
            try:
                error_msg = resp.json().get('error', {}).get('message', resp.text[:100])
                print(f"   {error_msg}")
            except:
                print(f"   {resp.text[:100]}")
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    
    except requests.exceptions.Timeout:
        print("❌ Request timeout - Check your internet connection")
        return {"success": False, "error": "Timeout"}
    except Exception as e:
        print(f"❌ Error: {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    if len(sys.argv) < 2:
        print("\n" + "=" * 80)
        print("❌ USAGE: python verify_api_key.py <YOUR_API_KEY>")
        print("=" * 80)
        print("\nExample:")
        print("  python verify_api_key.py AIzaSyDYVT...")
        print("\nOR")
        print(f"  export GEMINI_KEY='AIzaSyDYVT...'")
        print(f"  python verify_api_key.py")
        print("\n" + "=" * 80)
        sys.exit(1)
    
    api_key = sys.argv[1] if sys.argv[1] != "from_env" else None
    if not api_key:
        import os
        api_key = os.getenv("GEMINI_KEY")
    
    result = test_gemini_api(api_key)
    
    print("\n" + "=" * 80)
    print("📋 SUMMARY")
    print("=" * 80)
    
    if result["success"]:
        print("✅ SUCCESS - Your API key works!")
        print(f"   Endpoint: {result['endpoint']}")
        print(f"   Model: {result['model']}")
        if "note" in result:
            print(f"   Note: {result['note']}")
        print("\n   You can now:")
        print("   1. Refresh your browser")
        print("   2. Enter the API key in the sidebar")
        print("   3. Go to 🤖 AI Advisor tab")
        print("   4. Start asking questions!")
    else:
        print(f"❌ FAILED - {result['error']}")
        print("\n   Solutions:")
        print("   1. Verify your API key is correct (starts with 'AIza')")
        print("   2. Check https://aistudio.google.com - regenerate if needed")
        print("   3. Ensure it's a Gemini API key, not a different service")
        print("   4. Check Google Cloud Console for API enablement")
    
    print("\n" + "=" * 80)
    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
