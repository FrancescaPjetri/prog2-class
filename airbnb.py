import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from urllib.parse import urljoin
import requests

BASE_URL = "https://investors.airbnb.com/financials/default.aspx#quarterly"
DOWNLOAD_DIR = "airbnb_pdfs"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_pdf(url, download_dir, filename):
    local_filename = os.path.join(download_dir, filename)
    if os.path.exists(local_filename):
        print(f"Already downloaded: {local_filename}")
        return
    try:
        r = requests.get(url, stream=True, timeout=20)
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"Downloaded: {local_filename}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def scrape_airbnb_pdfs():
    ensure_dir(DOWNLOAD_DIR)

    chrome_options = Options()
    #chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(BASE_URL)
    time.sleep(5)  # Wait for the page to load

    # Find the financials table
    table = driver.find_element("xpath", "//div[contains(@class, 'module-financial-table_header')]/following-sibling::table")
    # Get year headers from the table
    year_headers = table.find_elements("xpath", ".//tr[1]/td | .//tr[1]/th | .//thead/tr/th | .//thead/tr/td")
    years = []
    for header in year_headers:
        text = header.text.strip()
        if text.isdigit():
            years.append(text)
    if not years:
        # Fallback: try to get years from visible year header divs
        years = [y.text.strip() for y in driver.find_elements("xpath", "//div[contains(@class, 'module-financial-table_header-year')]") if y.text.strip().isdigit()]
    if not years:
        print("Could not find year headers.")
        driver.quit()
        return

    # Iterate over table rows (each row is a document type)
    rows = table.find_elements("xpath", ".//tr[contains(@class, 'module-financial-table_track')]")
    for row in rows:
        try:
            doc_type = row.find_element("xpath", ".//th").text.strip().replace(' ', '_')
        except Exception:
            continue
        cells = row.find_elements("xpath", ".//td")
        for i, cell in enumerate(cells):
            year = years[i] if i < len(years) else 'unknown'
            links = cell.find_elements("xpath", ".//a[contains(@href, '.pdf')]")
            for link in links:
                href = link.get_attribute("href")
                quarter = link.text.strip().replace(' ', '')
                if not quarter:
                    # Try to get from aria-label
                    quarter = link.get_attribute('aria-label')
                    if quarter:
                        quarter = quarter.split()[0]
                if not quarter:
                    quarter = 'Q?'
                filename = f"{year}_{quarter}_{doc_type}.pdf"
                download_pdf(href, DOWNLOAD_DIR, filename)
    driver.quit()

if __name__ == "__main__":
    scrape_airbnb_pdfs()
