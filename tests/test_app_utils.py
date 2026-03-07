"""
Tests for app/utils.py — updated to match the revised validate_gemini_key API:
  * returns (bool, str, bool_warn) — 3-tuple
  * uses requests.post for live validation
  * timeout/connection errors are provisional passes (warn=True)
"""
import pytest
from unittest.mock import patch, Mock
import requests

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.utils import validate_gemini_key

# A correctly-formatted fake API key (starts with required "AIza" prefix)
VALID_FORMAT_KEY = "AIza" + "a" * 35


class TestValidateGeminiKey:
    """Tests for the validate_gemini_key function."""

    def test_valid_key_and_api_call(self):
        """Key that receives 200 from the API is valid, no warning."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            is_valid, message, warn = validate_gemini_key(VALID_FORMAT_KEY)
            assert is_valid is True
            assert "ready" in message
            assert warn is False

    def test_invalid_key_401_response(self):
        """Key rejected by the API (401) is invalid."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 401
            mock_post.return_value = mock_response

            is_valid, message, warn = validate_gemini_key(VALID_FORMAT_KEY)
            assert is_valid is False
            assert "Invalid API key" in message

    def test_api_error_other_status_code(self):
        """Non-200/401 status results in invalid with status code in message."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 500
            mock_post.return_value = mock_response

            is_valid, message, warn = validate_gemini_key(VALID_FORMAT_KEY)
            assert is_valid is False
            assert "500" in message

    def test_request_timeout(self):
        """Timeout is treated as a provisional pass (warn=True)."""
        with patch('requests.post', side_effect=requests.exceptions.Timeout):
            is_valid, message, warn = validate_gemini_key(VALID_FORMAT_KEY)
            assert is_valid is True
            assert warn is True
            assert "timed out" in message

    def test_request_exception(self):
        """Generic network error is treated as a provisional pass (warn=True)."""
        with patch('requests.post', side_effect=requests.exceptions.RequestException("err")):
            is_valid, message, warn = validate_gemini_key(VALID_FORMAT_KEY)
            assert is_valid is True
            assert warn is True

    def test_key_with_whitespace(self):
        """Leading/trailing whitespace is stripped before validation."""
        with patch('requests.post') as mock_post:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_post.return_value = mock_response

            is_valid, message, warn = validate_gemini_key(f"  {VALID_FORMAT_KEY}  ")
            assert is_valid is True

    def test_key_wrong_prefix(self):
        """Key without 'AIza' prefix fails format check immediately."""
        is_valid, message, warn = validate_gemini_key("Aiza" + "a" * 35)
        assert is_valid is False
        assert "Invalid key format" in message
        assert warn is False

    def test_empty_key(self):
        """Empty string fails format check."""
        is_valid, message, warn = validate_gemini_key("")
        assert is_valid is False
        assert warn is False

    def test_none_key(self):
        """None input fails type check."""
        is_valid, message, warn = validate_gemini_key(None)
        assert is_valid is False
        assert "Invalid input" in message
        assert warn is False
