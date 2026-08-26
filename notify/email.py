import html as html_lib

from .branding import style_for


def format_digest_html(jobs: list) -> str:
    """HTML digest with a background color per institution, for the email's html_body."""
    if not jobs:
        return "<p>No new matching jobs found.</p>"

    def esc(value: str) -> str:
        return html_lib.escape(str(value))

    cards = []
    for job in jobs:
        color = style_for(job.institution)["color"]
        cards.append(f"""
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
               style="background:{color}; border-radius:8px; margin-bottom:12px;">
          <tr><td style="padding:14px 18px; font-family:Arial,Helvetica,sans-serif; color:#222;">
            <div style="font-size:12px; text-transform:uppercase; letter-spacing:0.05em; opacity:0.75;">{esc(job.institution)}</div>
            <div style="font-size:16px; font-weight:bold; margin:4px 0 8px;">
              <a href="{esc(job.url)}" style="color:#111; text-decoration:none;">{esc(job.title)}</a>
            </div>
            <div style="font-size:13px; line-height:1.5;">
              Salary: {esc(job.salary_text)}<br>
              Location: {esc(job.location_text)}<br>
              Closes: {esc(job.closing_date)}
            </div>
          </td></tr>
        </table>""")

    return f"""
    <div style="font-family:Arial,Helvetica,sans-serif;">
      <p style="font-size:14px;"><strong>{len(jobs)} new match{"es" if len(jobs) != 1 else ""} found</strong></p>
      {"".join(cards)}
    </div>"""


def format_digest(jobs: list) -> str:
    """Plain-text digest of matched jobs, used both for the console/log output the
    GitHub Actions workflow captures and for the email body it sends.
    """
    if not jobs:
        return "No new matching jobs found."

    lines = [f"--- FOUND {len(jobs)} NEW MATCHES ---", ""]
    for job in jobs:
        lines.append(f"INSTITUTION: {job.institution}")
        lines.append(f"TITLE: {job.title}")
        lines.append(f"SALARY: {job.salary_text}")
        lines.append(f"LOCATION: {job.location_text}")
        lines.append(f"CLOSING DATE: {job.closing_date}")
        lines.append(f"LINK: {job.url}")
        lines.append("-" * 30)
    return "\n".join(lines)
