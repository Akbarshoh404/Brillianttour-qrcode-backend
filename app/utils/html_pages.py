"""Small, dependency-free HTML error pages served for direct browser hits
(e.g. someone scanning a QR code for a document that no longer exists).
Kept self-contained so it renders correctly with zero external assets.
"""
from fastapi.responses import HTMLResponse

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{title}</title>
<style>
  * {{ box-sizing: border-box; }}
  html, body {{ height: 100%; margin: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
    background: radial-gradient(circle at 20% 20%, #1f2937 0%, #0b0f19 55%, #05070c 100%);
    color: #f3f4f6;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
  }}
  .card {{
    max-width: 440px;
    width: 100%;
    text-align: center;
    padding: 48px 36px;
    border-radius: 28px;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    box-shadow: 0 24px 60px rgba(0, 0, 0, 0.45);
  }}
  .code {{
    font-size: 15px;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #8b93a7;
    margin-bottom: 18px;
  }}
  h1 {{
    font-size: 26px;
    font-weight: 700;
    margin: 0 0 12px;
    letter-spacing: -0.01em;
  }}
  p {{
    font-size: 15px;
    line-height: 1.6;
    color: #a3a9b7;
    margin: 0;
  }}
  .icon {{
    width: 64px;
    height: 64px;
    margin: 0 auto 24px;
    border-radius: 20px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
  }}
</style>
</head>
<body>
  <div class="card">
    <div class="icon">{emoji}</div>
    <div class="code">{code}</div>
    <h1>{heading}</h1>
    <p>{message}</p>
  </div>
</body>
</html>
"""


def render_error_page(*, code: str, heading: str, message: str, emoji: str = "!") -> HTMLResponse:
    status_code = int(code) if code.isdigit() else 500
    html = _TEMPLATE.format(title=heading, code=code, heading=heading, message=message, emoji=emoji)
    return HTMLResponse(content=html, status_code=status_code)
