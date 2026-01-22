import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TARGET_URL = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/joblist.aspx"
SALARY_THRESHOLD = 35000
SEEN_JOBS_FILE = "seen_jobs.txt"

def check_salary(text):
    """Extracts numbers from text like '£35,000 - £40,000' and checks against threshold."""
    nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', text)
    if not nums:
        return False, 0
    # Remove commas and convert to integers
    actual_nums = [int(n.replace(',', '')) for n in nums]
    max_salary = max(actual_nums)
    return max_salary >= SALARY_THRESHOLD, max_salary

def main():
    match_output = []
    log_output = []
    found_count = 0
    
    # 1. Load seen jobs from the file
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            seen_jobs = set(f.read().splitlines())
    else:
        seen_jobs = set()

    new_seen_list = list(seen_jobs)

    # 2. Start the Browser with Stealth Settings
    with sync_playwright() as p:
        log_output.append("Connecting to British Museum portal...")
        browser = p.chromium.launch(headless=True)
        
        # We add a desktop window size and a real User-Agent
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        page = context.new_page()

        try:
            # wait_until="networkidle" waits for all background data to finish loading
            page.goto(TARGET_URL, wait_until="networkidle", timeout=60000)
            
            # A 3-second 'human' pause to let the job table render
            page.wait_for_timeout(3000)
            
            # Now we look for the job rows
            page.wait_for_selector(".vacancy-row", timeout=20000)
            
            soup = BeautifulSoup(page.content(), "html.parser")
            rows = soup.select(".vacancy-row")

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
                        # Format the Match Block
                        match_output.append(f"--- FOUND MATCH {found_count} ---")
                        match_output.append(f"INSTITUTION: British Museum")
                        match_output.append(f"TITLE: {title}")
                        match_output.append(f"SALARY: {salary_text}")
                        match_output.append(f"DUE: {due_date}")
                        match_output.append(f"LINK: {link}\n")
                        
                        new_seen_list.append(link)
                        log_output.append(f"  [!!] MATCH FOUND: {max_val}")
                    else:
                        log_output.append(f"  SKIPPED: {salary_text}")

        except Exception as e:
            log_output.append(f"CRITICAL ERROR: {str(e)}")
        
        browser.close()

    # --- FINAL OUTPUT PRINTING ---
    
    # Matches first
    if match_output:
        print("\n".join(match_output))
        print(f"--- TOTAL NEW MATCHES: {found_count} ---")
    else:
        print("No new matches found today.")

    # Logs second
    print("\n" + "="*35)
    print("DETAILED SCAN LOGS (FOR REFERENCE)")
    print("="*35)
    print("\n".join(log_output))

    # 3. Save the new list of seen jobs back to the file
    with open(SEEN_JOBS_FILE, "w") as f:
        f.write("\n".join(new_seen_list))

if __name__ == "__main__":
    main()
