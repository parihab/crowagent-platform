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
    # monkeypatch components.html to capture the HTML and return a fake value
    captured = {"html": None, "ret": {"lat":"51.5","lon":"-0.1"}}

    def fake_html(srcdoc, height=None, **kwargs):
        captured["html"] = srcdoc
        # mimic a component returning a dict as value
        return captured["ret"]

    monkeypatch.setattr(components, "html", fake_html)

    # should run without UnicodeEncodeError and return the fake dict
    result = location.render_geo_detect()
    assert captured["html"] is not None
    assert result == captured["ret"]
    # ensure there are no surrogate escape sequences left
    assert "\\ud83d" not in captured["html"]
    # ensure Streamlit API call is referenced in the markup
    assert "setComponentValue" in captured["html"]
