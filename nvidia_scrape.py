import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

NVIDIA_URL = "https://investor.nvidia.com/financial-info/financial-reports/"
DOWNLOAD_DIR = "pdf_downloads_nvidia"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def sanitize_filename(name):
    return "".join(c if c.isalnum() or c in (' ', '.', '_', '-') else "_" for c in name).strip()

def download_pdf(url, download_dir):
    filename = sanitize_filename(url.split("/")[-1].split("?")[0])
    if not filename.lower().endswith(".pdf"):
        filename += ".pdf"
    local_path = os.path.join(download_dir, filename)
    if os.path.exists(local_path):
        print(f"Already downloaded: {local_path}")
        return
    try:
        r = requests.get(url, stream=True, timeout=20)
        r.raise_for_status()
        with open(local_path, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"Downloaded: {local_path}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def scrape_nvidia():
    ensure_dir(DOWNLOAD_DIR)

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1200,1000")

    print(f"Scraping {NVIDIA_URL}")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get(NVIDIA_URL)
        time.sleep(5)

        # Wait for the table to load
        time.sleep(2)

        # Find all <a> tags with .pdf in href
        all_links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
        pdf_links = [link.get_attribute("href") for link in all_links if link.get_attribute("href")]

        if not pdf_links:
            print("No PDF links found.")
        else:
            print(f"Found {len(pdf_links)} PDF links.")
            for link in pdf_links:
                download_pdf(link, DOWNLOAD_DIR)

    except Exception as e:
        print(f"Error during scraping: {e}")
    finally:
        driver.quit()

if __name__ == "__main__":
    scrape_nvidia()
