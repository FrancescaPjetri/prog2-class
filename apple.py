
import os
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

DOWNLOAD_DIR = "pdf_downloads_apple"

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def download_pdf(url, download_dir):
    filename = os.path.join(download_dir, url.split("/")[-1].split("?")[0])
    if os.path.exists(filename):
        print(f"Already downloaded: {filename}")
        return
    try:
        r = requests.get(url, stream=True, timeout=20)
        r.raise_for_status()
        with open(filename, 'wb') as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        print(f"Downloaded: {filename}")
    except Exception as e:
        print(f"Failed to download {url}: {e}")

def scrape_apple():
    ensure_dir(DOWNLOAD_DIR)

    # Remove headless to see the browser (useful for debugging)
    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    # Do NOT add headless to see the browser
    chrome_options.add_argument("--window-size=1200,1000")

    print("Scraping https://investor.apple.com/")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    try:
        driver.get("https://investor.apple.com/")
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "module_links")))

        all_links = driver.find_elements(By.TAG_NAME, "a")
        pdf_links = [link.get_attribute("href") for link in all_links if link.get_attribute("href") and ".pdf" in link.get_attribute("href").lower()]

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
    scrape_apple()
