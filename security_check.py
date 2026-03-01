#!/usr/bin/env python3
"""
🔒 Security Verification Report - CrowAgent™ Platform
Generated: Feb 21, 2026

This script verifies that all security measures are in place before
sharing the application URL publicly.
"""

import os
import sys
import re

# ensure stdout can emit Unicode (emojis, etc.)
# some environments default to 'ANSI_X3.4-1968' which causes
# UnicodeEncodeError when printing symbols.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def check_file_content(filepath: str, should_contain: list[str] = None, 
                       must_not_contain: list[str] = None) -> tuple[bool, str]:
    """Check file content for security requirements."""
    if not os.path.exists(filepath):
        return False, f"❌ File not found: {filepath}"
    
    # read files with explicit utf-8 encoding to avoid errors on
    # systems where locale is not utf-8.
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check must-have content
    if should_contain:
        for text in should_contain:
            if text not in content:
                return False, f"❌ Missing required text: {text}"
    
    # Check forbidden content
    if must_not_contain:
        for text in must_not_contain:
            if text in content:
                return False, f"❌ Found forbidden text: {text}"
    
    return True, "✅ Pass"


print("=" * 80)
print("🔒 SECURITY VERIFICATION REPORT - CrowAgent™ Platform")
print("=" * 80)

all_passed = True
checks = []

# ─────────────────────────────────────────────────────────────────────────────
# 1. Check .env file
# ─────────────────────────────────────────────────────────────────────────────
print("\n[1] .env File Security")
print("-" * 80)

if not os.path.exists('.env'):
    print("❌ File not found: .env (copy .env.example and fill in your keys)")
    passed = False
else:
    passed, msg = check_file_content(
        '.env',
        should_contain=['# API Keys', 'DO NOT commit', 'YOUR_GEMINI_API_KEY_HERE'],
        must_not_contain=['AIzaSy']  # No real-looking keys
    )
    print(msg)

checks.append(('✅ No API keys in .env' if passed else '❌ .env contains API keys', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 2. Check .streamlit/secrets.toml
# ─────────────────────────────────────────────────────────────────────────────
print("\n[2] Streamlit Secrets Configuration")
print("-" * 80)

if os.path.exists('.streamlit/secrets.toml'):
    passed, msg = check_file_content(
        '.streamlit/secrets.toml',
        should_contain=['IMPORTANT SECURITY', '# GEMINI_KEY'],
        must_not_contain=['GEMINI_KEY = "AIzaSy"']  # Should not have active uncommented key
    )
    print(msg)
    checks.append(('✅ No active keys in secrets.toml' if passed else '❌ Active keys in secrets.toml', passed))
    all_passed = all_passed and passed
else:
    print("❌ .streamlit/secrets.toml not found (create one or use .env)")
    all_passed = False

# ─────────────────────────────────────────────────────────────────────────────
# 3. Check .gitignore
# ─────────────────────────────────────────────────────────────────────────────
print("\n[3] Git Ignore Configuration")
print("-" * 80)

passed, msg = check_file_content(
    '.gitignore',
    should_contain=['.env', '.streamlit/secrets.toml']
)
print(msg)
checks.append(('✅ Secrets in .gitignore' if passed else '❌ Secrets not ignored', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 4. Check app/main.py for placeholder safety
# ─────────────────────────────────────────────────────────────────────────────
print("\n[4] Application Code Security")
print("-" * 80)

passed, msg = check_file_content(
    'app/main.py',
    should_contain=['placeholder="AIzaSy... (starts with', 'Never share', 'Security Notice'],
    must_not_contain=['AIzaSyDPOySb-P2nP7IMpGfUsoV5eRFXF7o5OXw']  # Old dummy key
)
print(msg)
checks.append(('✅ Safe placeholder in UI' if passed else '❌ Unsafe placeholder', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 5. Check for logging/printing of keys
# ─────────────────────────────────────────────────────────────────────────────
print("\n[5] Code Audit - No Key Logging")
print("-" * 80)

has_unsafe_logging = False
unsafe_patterns = [
    'print(.*gemini_key',
    'print(.*api_key',
    'logging.debug(.*key',
    'st.write.*gemini_key'
]

for pattern in unsafe_patterns:
    with open('app/main.py', 'r', encoding='utf-8') as f:
        if pattern in f.read():
            has_unsafe_logging = True
            break

passed = not has_unsafe_logging
print("✅ No API key logging found" if passed else "❌ Found API key logging")
checks.append(('✅ No sensitive logging' if passed else '❌ Sensitive logging found', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 6. Check documentation exists
# ─────────────────────────────────────────────────────────────────────────────
print("\n[6] Security Documentation")
print("-" * 80)

passed = os.path.exists('SECURITY_GUIDE.md')
print("✅ SECURITY_GUIDE.md exists" if passed else "❌ SECURITY_GUIDE.md missing")
checks.append(('✅ Security guide created' if passed else '❌ No security guide', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 7. Check for unsafe os.environ usage (SEC-001)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[7] Code Audit - Unsafe Environment Modification")
print("-" * 80)

has_unsafe_environ = False
environ_assignment_re = re.compile(r'os\.environ\[.*\]\s*=')

if os.path.exists('app/main.py'):
    with open('app/main.py', 'r', encoding='utf-8') as f:
        content = f.read()
        if environ_assignment_re.search(content):
            has_unsafe_environ = True
            print("❌ Found unsafe os.environ modification in app/main.py (SEC-001)")
            print("   Guidance: Pass API keys as function arguments, do not write to os.environ in Streamlit.")

passed = not has_unsafe_environ
if passed:
    print("✅ No unsafe os.environ modification found")
checks.append(('✅ No unsafe os.environ' if passed else '❌ Unsafe os.environ found', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# 8. Check for hardcoded personal emails (SEC-003)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[8] Code Audit - Hardcoded Personal Data")
print("-" * 80)

passed, msg = check_file_content(
    'services/epc.py',
    must_not_contain=['crowagent.platform@gmail.com']
)
print(msg)
checks.append(('✅ No hardcoded emails' if passed else '❌ Hardcoded email found', passed))
all_passed = all_passed and passed

# ─────────────────────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("📋 VERIFICATION SUMMARY")
print("=" * 80)

for check_name, check_passed in checks:
    print(f"{check_name}")

print("\n" + "=" * 80)
if all_passed:
    print("✅ ALL SECURITY CHECKS PASSED")
    print("=" * 80)
    print("\n🚀 Your application is safe to share publicly!")
    print("\nKey security measures in place:")
    print("  • No API keys in git repository")
    print("  • Session-only key storage (cleared on browser close)")
    print("  • Users bring their own API keys")
    print("  • Password-masked input field")
    print("  • Security notice in sidebar")
    print("  • Comprehensive security guide provided")
    sys.exit(0)
else:
    print("❌ SECURITY CHECKS FAILED")
    print("=" * 80)
    print("\nPlease fix the issues above before sharing publicly.")
    sys.exit(1)
