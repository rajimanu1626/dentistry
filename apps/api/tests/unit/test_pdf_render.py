"""Unit tests for the prescription HTML/PDF renderer."""

from __future__ import annotations

import pytest
from app.services.pdf import DEFAULT_PRESCRIPTION_TEMPLATE_HTML, render_html, utc_now_iso


def test_render_html_substitutes_context() -> None:
    template = """
    <html><body>
    <h1>{{ clinic.name }}</h1>
    <p>{{ patient.full_name }}</p>
    <ul>
    {% for it in items %}<li>{{ it.medication }} - {{ it.dose }}</li>{% endfor %}
    </ul>
    </body></html>
    """
    html = render_html(
        template,
        context={
            "clinic": {"name": "Demo Dental"},
            "patient": {"full_name": "Alice"},
            "items": [{"medication": "Amoxicillin", "dose": "500mg"}],
        },
    )
    assert "Demo Dental" in html
    assert "Alice" in html
    assert "Amoxicillin" in html
    assert "500mg" in html


def test_render_html_escapes_user_content() -> None:
    template = "<p>{{ note }}</p>"
    html = render_html(template, context={"note": "<script>alert(1)</script>"})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_render_html_raises_on_undefined_variable() -> None:
    from jinja2 import UndefinedError

    with pytest.raises(UndefinedError):
        render_html("{{ missing }}", context={})


def test_default_prescription_template_renders_items() -> None:
    html = render_html(
        DEFAULT_PRESCRIPTION_TEMPLATE_HTML,
        context={
            "clinic": {"name": "Demo Dental", "address": "1 Main St"},
            "patient": {"full_name": "Alice", "patient_code": "P001"},
            "dentist": {"full_name": "Dr. Smith"},
            "items": [
                {
                    "medication": "Amoxicillin",
                    "dose": "500mg",
                    "frequency": "twice daily",
                    "duration": "5 days",
                }
            ],
            "notes": "Take with food",
            "visit_date": "2026-01-03",
        },
    )
    assert "Demo Dental" in html
    assert "Amoxicillin" in html
    assert "Take with food" in html


def test_utc_now_iso_format() -> None:
    s = utc_now_iso()
    assert "UTC" in s
    assert s[:4].isdigit()
