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
