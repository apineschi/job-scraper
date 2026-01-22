import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TARGET_URL = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/joblist.aspx"
SALARY_THRESHOLD = 35000
SEEN_JOBS_FILE = "seen_jobs.txt"

def check_salary(text):
    """Extracts the highest number from salary text and checks if it's >= threshold."""
    nums = re.findall(r'£?(\d{2,3}),(\d{3})', text)
    if not nums:
        return False, 0
    
    actual_nums = [int(n[0] + n[1]) for n in nums]
    max_salary = max(actual_nums)
    return max_salary >= SALARY_THRESHOLD, max_salary

def main():
    # Lists to hold our output sections
    match_output = []
    log_output = []
    
    # Load seen jobs
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            seen_jobs = set(f.read().splitlines())
    else:
        seen_jobs = set()

    new_seen_list = list(seen_jobs)

    with sync_playwright() as p:
        log_output.append("Opening British Museum portal...")
        browser = p.chromium.launch(headless=True)
        page = browser.new_context().new_page()
        page.goto(TARGET_URL)
        
        # Wait for the table to load
        page.wait_for_selector(".vacancy-row")
        soup = BeautifulSoup(page.content(), "html.parser")
        rows = soup.select(".vacancy-row")

        found_count = 0

        for row in rows:
            title_tag = row.select_one(".vacancy-title a")
            salary_tag = row.select_one(".salary")
            due_tag = row.select_one(".closing-date")
            
            if title_tag and salary_tag:
                title = title_tag.get_text(strip=True)
                salary_text = salary_tag.get_text(strip=True)
                due_date = due_tag.get_text(strip=True) if due_tag else "N/A"
                link = "https://bmrecruit.ciphr-irecruit.com/" + title_tag['href']

                log_output.append(f"Scanning: {title}...")

                is_high_pay, max_val = check_salary(salary_text)

                if is_high_pay and link not in seen_jobs:
                    found_count += 1
                    log_output.append(f"  MATCH: {salary_text} | DUE: {due_date}")
                    
                    # Create the formatted match block
                    match_output.append(f"--- FOUND MATCH {found_count} ---")
                    match_output.append(f"INSTITUTION: British Museum")
                    match_output.append(f"TITLE: {title}")
                    match_output.append(f"SALARY: {salary_text}")
                    match_output.append(f"DUE: {due_date}")
                    match_output.append(f"LINK: {link}")
                    match_output.append("") # Empty line for spacing
                    
                    new_seen_list.append(link)
                else:
                    log_output.append(f"  SKIPPED: {salary_text}")

        browser.close()

    # --- FINAL OUTPUT PRINTING ---
    # Everything printed here is caught by the GitHub Action for the email body

    if match_output:
        print("\n".join(match_output))
        print(f"--- TOTAL MATCHES: {found_count} ---")
    else:
        print("No new high-paying jobs found today.")

    print("\n" + "="*30)
    print("DETAILED SCAN LOGS:")
    print("="*30)
    print("\n".join(log_output))

    # Save updated seen jobs
    with open(SEEN_JOBS_FILE, "w") as f:
        f.write("\n".join(new_seen_list))

if __name__ == "__main__":
    main()
