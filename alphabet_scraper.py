import os
import time
import requests
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# List of investor pages
PAGES = [
    "https://abc.xyz/investor/"
]

DOWNLOAD_DIR = "pdf_downloads"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def sanitize_filename(name):
    return name.replace("/", "_").replace(" ", "_").replace("__", "_")

def download_pdf(url, download_dir, suggested_name=None):
    filename = suggested_name or url.split("/")[-1].split("?")[0]
    filename = sanitize_filename(filename)
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    local_path = os.path.join(download_dir, filename)

    if os.path.exists(local_path):
        print(f"Already downloaded: {local_path}")
        return
    try:
        r = requests.get(url, stream=True, timeout=30)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"Downloaded: {local_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def scrape_all_pdfs():
    ensure_dir(DOWNLOAD_DIR)

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    for base_url in PAGES:
        print(f"\nScraping {base_url}")
        try:
            driver.get(base_url)
            time.sleep(6)  # Wait for dynamic content to load

            links = driver.find_elements("tag name", "a")
            pdf_links = []

            for link in links:
                href = link.get_attribute("href")
                label = link.get_attribute("aria-label") or link.text or "document"
                if href and ".pdf" in href.lower():
                    full_url = urljoin(base_url, href)
                    pdf_links.append((full_url, label))

            if not pdf_links:
                print(f"No PDF links found on {base_url}")
            else:
                print(f"Found {len(pdf_links)} PDF links on {base_url}")
                for href, label in pdf_links:
                    download_pdf(href, DOWNLOAD_DIR, suggested_name=label)

        except Exception as e:
            print(f"Error scraping {base_url}: {e}")

    driver.quit()

if __name__ == "__main__":
    scrape_all_pdfs()
