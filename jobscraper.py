import os
import re
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

# --- CONFIGURATION ---
DB_FILE = "seen_jobs.txt"
SALARY_THRESHOLD = 35000

def load_seen_jobs():
    if not os.path.exists(DB_FILE): return set()
    with open(DB_FILE, "r") as f: return set(line.strip() for line in f)

def save_new_job(job_link):
    with open(DB_FILE, "a") as f: f.write(job_link + "\n")

def extract_salary_number(salary_text):
    """Extracts the first large number found to use for the threshold check."""
    numbers = re.findall(r'\d+', salary_text.replace(',', ''))
    for n in numbers:
        val = int(n)
        if val > 1000: return val
    return 0

def scan_job_details(page, url):
    """Scans for full Salary range and Application deadline line."""
    page.goto(url, wait_until="networkidle")
    page.wait_for_timeout(2000) 
    
    soup = BeautifulSoup(page.content(), 'html.parser')
    # Get text using newline as separator to keep lines distinct
    page_text = soup.get_text("\n", strip=True)
    
    salary = "Not listed"
    closing_date = "Not found"

    # 1. Capture Full Salary Range
    # Looks for "Salary" and grabs everything until the end of that line
    sal_match = re.search(r'Salary[:\s]*(.*)', page_text, re.IGNORECASE)
    if sal_match:
        salary = sal_match.group(1).strip()

    # 2. Capture Application Deadline Line
    deadline_match = re.search(r'Application deadline[:\s]*(.*)', page_text, re.IGNORECASE)
    if deadline_match:
        closing_date = deadline_match.group(1).strip()

    return salary, closing_date

def run_scraper():
    seen_jobs = load_seen_jobs()
    new_filtered_jobs = []

    with sync_playwright() as p:
        print("Opening British Museum portal...")
        browser = p.chromium.launch(headless=True)
        ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        context = browser.new_context(user_agent=ua)
        page = context.new_page()
        
        page.goto("https://bmrecruit.ciphr-irecruit.com/templates/CIPHR/job_list.aspx")
        
        try:
            page.get_by_role("button", name="Search").click()
            page.wait_for_timeout(3000)
        except:
            pass

        soup = BeautifulSoup(page.content(), 'html.parser')
        unique_links = {}
        for link in soup.find_all('a', href=True):
            href = link['href']
            title = link.get_text(strip=True)
            if "jobdetail" in href.lower() and title and title.lower() != "view":
                full_url = href if href.startswith("http") else f"https://bmrecruit.ciphr-irecruit.com/{href.lstrip('/')}"
                if full_url not in seen_jobs:
                    unique_links[full_url] = title

        for url, title in unique_links.items():
            print(f"Scanning: {title}...")
            salary_str, due_date = scan_job_details(page, url)
            salary_val = extract_salary_number(salary_str)

            if salary_val >= SALARY_THRESHOLD:
                print(f" ✅ MATCH: {salary_str} | DUE: {due_date}")
                new_filtered_jobs.append({
                    "title": title, 
                    "salary": salary_str, 
                    "due": due_date, 
                    "url": url
                })
            else:
                print(f" ❌ SKIPPED: {salary_str}")
            
            save_new_job(url)

        browser.close()

    if new_filtered_jobs:
        print(f"\n--- FOUND {len(new_filtered_jobs)} MATCHES ---")
        for job in new_filtered_jobs:
            print(f"TITLE: {job['title']}\nSALARY: {job['salary']}\nDUE: {job['due']}\nLINK: {job['url']}\n" + "-"*30)
    else:
        print("\nScan finished. No new high-salary jobs found.")

if __name__ == "__main__":
    run_scraper()
