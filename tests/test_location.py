import os
import sys
import streamlit.components.v1 as components
import pytest

# ensure services package is importable
_services_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services"))
if _services_dir not in sys.path:
    sys.path.insert(0, _services_dir)

import location


def test_render_geo_detect_does_not_raise(monkeypatch):
    # monkeypatch components.html to just capture the src argument
    captured = {"html": None}

    def fake_html(srcdoc, height=None, **kwargs):
        captured["html"] = srcdoc
        return None

    monkeypatch.setattr(components, "html", fake_html)

    # should run without UnicodeEncodeError
    location.render_geo_detect()
    assert captured["html"] is not None
    # ensure there are no surrogate escape sequences left
    assert "\\ud83d" not in captured["html"]
