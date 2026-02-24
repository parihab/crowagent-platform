import importlib
import os
import sys

# ensure the package root is discoverable when pytest adjusts sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import pytest

from app import main


def test_footer_includes_centered_logo(monkeypatch):
    """Reload the app and inspect markdown calls for the footer.

    We monkeypatch ``st.markdown`` to capture HTML fragments and then
    look for the footer block. It should use the ``ent-footer`` class and
    render either an <img> (when a logo URI is available) or branded text.
    """
    captured = []

    def fake_markdown(html, unsafe_allow_html=False):
        captured.append(html)

    monkeypatch.setattr(main.st, "markdown", fake_markdown)

    # reload to force module-level code to execute again
    importlib.reload(main)

    # find the footer call that contains the legal text or the class
    footer_call = None
    for c in captured:
        if "All rights reserved" in c:
            footer_call = c
            break

    assert footer_call is not None, "Footer markup was not emitted"
    assert "class='ent-footer'" in footer_call or 'class="ent-footer"' in footer_call
    # ensure we are actually rendering the image asset when the URI exists
    if main.LOGO_URI:
        assert "<img" in footer_call, "Expected <img> logo in footer when LOGO_URI is set"
    else:
        assert "font-family" in footer_call or "🌿" in footer_call
