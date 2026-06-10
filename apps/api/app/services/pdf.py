"""PDF rendering for prescriptions.

Uses WeasyPrint with Jinja2 templates. Templates are stored per-clinic in
``prescription_templates`` so each clinic can customise header/footer/branding.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from jinja2 import Environment, StrictUndefined
from jinja2.sandbox import SandboxedEnvironment

_jinja: Environment = SandboxedEnvironment(
    autoescape=True,
    undefined=StrictUndefined,
)

DEFAULT_PRESCRIPTION_TEMPLATE_HTML = """
<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><title>Prescription</title></head>
<body>
  <header><h1>{{ clinic.name }}</h1><small>{{ clinic.address or '' }}</small></header>
  <hr/>
  <section>
    <p>Patient: <strong>{{ patient.full_name }}</strong> ({{ patient.patient_code }})</p>
    <p>Date: {{ visit_date }}</p>
  </section>
  <ol>
    {% for item in items %}
    <li>{{ item.medication }} — {{ item.dose }} ({{ item.frequency }}) for {{ item.duration }}</li>
    {% endfor %}
  </ol>
  {% if notes %}
  <p><strong>Notes:</strong> {{ notes }}</p>
  {% endif %}
  <footer><p>Dr. {{ dentist.full_name }}</p></footer>
</body>
</html>
"""


def render_html(template_source: str, *, context: dict[str, Any]) -> str:
    template = _jinja.from_string(template_source)
    return template.render(**context)


def render_pdf(
    template_source: str,
    *,
    context: dict[str, Any],
    css: str | None = None,
    watermark: str | None = None,
) -> bytes:
    """Return a PDF-encoded byte string."""
    from weasyprint import CSS, HTML  # local import keeps module import cheap

    html = render_html(template_source, context=context)
    stylesheets = [CSS(string=css)] if css else None

    if watermark:
        watermark_css = (
            f"@page {{ size: A4; margin: 18mm; "
            f'@bottom-center {{ content: "{watermark}"; font-size: 9pt; color: #999; }} }}'
            f".cc-watermark {{ position: fixed; top: 30%; left: 20%; opacity: 0.06; "
            f"font-size: 92pt; transform: rotate(-30deg); }}"
        )
        stylesheets = [*(stylesheets or []), CSS(string=watermark_css)]
        html = html + f'<div class="cc-watermark" aria-hidden="true">{watermark}</div>'

    return HTML(string=html, base_url=".").write_pdf(stylesheets=stylesheets) or b""


def utc_now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
