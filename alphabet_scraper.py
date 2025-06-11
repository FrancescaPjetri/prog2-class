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
    "https://abc.xyz/investor/earnings/"
]

DOWNLOAD_DIR = "pdf_downloads_alphabet"

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
            time.sleep(10)  # Wait longer for dynamic content to load

            # Scroll to bottom to trigger lazy loading
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(3)

            pdf_links = []

            # Find all <a> tags with the specific class for PDF links
            pdf_anchors = driver.find_elements(
                "css selector", "a.EarningsCard-financialReportPDFLink-link"
            )
            print(f"Found {len(pdf_anchors)} PDF anchor tags with class EarningsCard-financialReportPDFLink-link.")

            for anchor in pdf_anchors:
                href = anchor.get_attribute("href")
                text = anchor.text.strip().lower()
                aria_label = anchor.get_attribute("aria-label") or "PDF"
                # Traverse up to find the year (from the closest previous h3.EarningsCards-title)
                year = None
                parent = anchor
                for _ in range(6):  # Traverse up to 6 levels up
                    parent = parent.find_element("xpath", "..")
                    siblings = parent.find_elements("xpath", "preceding-sibling::h3[contains(@class, 'EarningsCards-title')]")
                    if siblings:
                        year = siblings[-1].text.strip()
                        break
                # Try to get report type from aria-label or href
                report_type = ""
                if "10-q" in href.lower():
                    report_type = "10-Q"
                elif "10-k" in href.lower():
                    report_type = "10-K"
                elif aria_label:
                    report_type = aria_label.replace("PDF link for ", "").replace(" ", "_")
                else:
                    report_type = "PDF"
                # Try to get quarter from href or aria-label
                quarter = ""
                for q in ["Q1", "Q2", "Q3", "Q4"]:
                    if q.lower() in href.lower():
                        quarter = q
                        break
                # Build filename
                filename_parts = [year, quarter, report_type]
                filename = "_".join([p for p in filename_parts if p]) + ".pdf"
                filename = sanitize_filename(filename)
                if href and href.lower().endswith(".pdf"):
                    full_url = urljoin(base_url, href)
                    print(f"PDF Link: {full_url} | Filename: {filename}")
                    pdf_links.append((full_url, filename))

            if not pdf_links:
                print(f"No PDF links found on {base_url}")
            else:
                print(f"Found {len(pdf_links)} PDF links on {base_url}")
                for href, filename in pdf_links:
                    download_pdf(href, DOWNLOAD_DIR, suggested_name=filename)

        except Exception as e:
            print(f"Error scraping {base_url}: {e}")

    driver.quit()

if __name__ == "__main__":
    scrape_all_pdfs()
