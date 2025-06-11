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

def download_pdf(url, download_dir):
    local_filename = os.path.join(download_dir, url.split("/")[-1])
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
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    driver.get(BASE_URL)
    time.sleep(5)  # Attendi che i PDF vengano caricati

    links = driver.find_elements("tag name", "a")
    pdf_links = [
        urljoin(BASE_URL, link.get_attribute("href"))
        for link in links
        if link.get_attribute("href") and link.get_attribute("href").lower().endswith(".pdf")
    ]

    if not pdf_links:
        print("No PDF links found.")
    else:
        print(f"Found {len(pdf_links)} PDF links.")
        for link in pdf_links:
            download_pdf(link, DOWNLOAD_DIR)

    driver.quit()

if __name__ == "__main__":
    scrape_airbnb_pdfs()
