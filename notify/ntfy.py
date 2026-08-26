import os
import sys

import requests

NTFY_BASE_URL = "https://ntfy.sh"


def send_push(jobs: list) -> None:
    """Push one ntfy.sh notification per matched job. Silently no-ops if NTFY_TOPIC
    isn't set (e.g. local dry runs) so this never blocks the rest of the scan.

    All logging here goes to stderr: the workflow captures stdout verbatim into the
    user-facing email body, and push diagnostics don't belong in that email.
    """
    topic = os.environ.get("NTFY_TOPIC")
    if not topic:
        print("NTFY_TOPIC not set — skipping push notifications.", file=sys.stderr)
        return

    for job in jobs:
        message = (
            f"{job.institution}\n"
            f"Salary: {job.salary_text}\n"
            f"Location: {job.location_text}\n"
            f"Closes: {job.closing_date}"
        )
        try:
            resp = requests.post(
                f"{NTFY_BASE_URL}/{topic}",
                data=message.encode("utf-8"),
                headers={
                    "Title": job.title.encode("utf-8"),
                    "Click": job.url.encode("utf-8"),
                    "Priority": "default",
                },
                timeout=15,
            )
            if resp.ok:
                print(f"ntfy push OK for {job.title!r} (status {resp.status_code})", file=sys.stderr)
            else:
                print(
                    f"ntfy push REJECTED for {job.title!r}: status {resp.status_code} — {resp.text[:300]}",
                    file=sys.stderr,
                )
        except requests.RequestException as e:
            print(f"ntfy push failed for {job.title!r}: {e}", file=sys.stderr)
