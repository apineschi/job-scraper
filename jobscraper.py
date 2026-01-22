import os
import re
import time
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
TARGET_URL = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/job_list.aspx"
SALARY_THRESHOLD = 35000
SEEN_JOBS_FILE = "seen_jobs.txt"

def check_salary(text):
    nums = re.findall(r'(\d{1,3}(?:,\d{3})*)', text)
    if not nums:
        return False, 0
    actual_nums = [int(n.replace(',', '')) for n in nums]
    max_salary = max(actual_nums)
    return max_salary >= SALARY_THRESHOLD, max_salary

def main():
    if os.path.exists(SEEN_JOBS_FILE):
        with open(SEEN_JOBS_FILE, "r") as f:
            seen_jobs = set(f.read().splitlines())
    else:
        seen_jobs = set()

    new_seen_list = list(seen_jobs)
    found_any_new = False

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # We add a user_agent here just to be safe, as it's standard for simple scrapers
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        print(f"Navigating to {TARGET_URL}...")
        page.goto(TARGET_URL, wait_until="domcontentloaded")
        
        # --- THE FIX ---
        # Wait 5 seconds for the JavaScript to load the job table
        time.sleep(5) 
        
        # Now try to find the rows
        page.wait_for_selector(".vacancy-row", timeout=15000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        rows = soup.select(".vacancy-row")

        for row in rows:
            title_tag = row.select_one(".vacancy-title a")
            salary_tag = row.select_one(".salary")
            
            if title_tag and salary_tag:
                title = title_tag.get_text(strip=True)
                salary_text = salary_tag.get_text(strip=True)
                link = "https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/" + title_tag['href']

                is_high_pay, max_val = check_salary(salary_text)

                if is_high_pay and link not in seen_jobs:
                    print(f"MATCH FOUND: {title}")
                    print(f"Salary: {salary_text}")
                    print(f"Link: {link}")
                    print("-" * 20)
                    
                    new_seen_list.append(link)
                    found_any_new = True
                else:
                    print(f"Skipping: {title} ({salary_text})")

        browser.close()

    if not found_any_new:
        print("No new matches found today.")

    with open(SEEN_JOBS_FILE, "w") as f:
        f.write("\n".join(new_seen_list))

if __name__ == "__main__":
    main()
