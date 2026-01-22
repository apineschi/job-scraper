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
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        print(f"Navigating to {TARGET_URL}...")
        page.goto(TARGET_URL, wait_until="networkidle")
        
        # Give the JavaScript 5 seconds to finish rendering the list
        time.sleep(5) 
        
        # Grab all the content and let BeautifulSoup find the patterns
        html_content = page.content()
        soup = BeautifulSoup(html_content, "html.parser")
        
        # Looking for 'jobdetail' based on your correct observation
        links = soup.find_all('a', href=re.compile(r'jobdetail'))
        
        for link_tag in links:
            # Finding the closest text container to grab the salary
            container = link_tag.find_parent('tr') or link_tag.find_parent('div')
            if not container:
                continue

            title = link_tag.get_text(strip=True)
            container_text = container.get_text(separator=' ')
            
            # Clean up the link (avoiding double slashes)
            href = link_tag['href'].lstrip('/')
            full_link = f"https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/{href}"

            is_high_pay, max_val = check_salary(container_text)

            if is_high_pay and full_link not in seen_jobs:
                print(f"MATCH FOUND: {title}")
                print(f"Salary Info: {container_text[:120]}...") 
                print(f"Link: {full_link}")
                print("-" * 20)
                
                new_seen_list.append(full_link)
                found_any_new = True

        browser.close()

    if not found_any_new:
        print("No new matches found today.")

    with open(SEEN_JOBS_FILE, "w") as f:
        f.write("\n".join(new_seen_list))

if __name__ == "__main__":
    main()
