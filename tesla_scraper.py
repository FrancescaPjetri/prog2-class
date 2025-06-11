from bs4 import BeautifulSoup
import os
import requests
import csv

# Path to your downloaded HTML file
HTML_FILE = "Tesla Investor Relations.html"

# Read the HTML file
with open(HTML_FILE, "r", encoding="utf-8") as f:
    soup = BeautifulSoup(f, "lxml")

# Find all download links (commonly PDFs, Excel, etc.)
download_links = []
for a in soup.find_all("a", href=True):
    if a.get_text(strip=True) == "Download":
        href = a["href"]
        # If the link is relative, prepend the base URL
        if href.startswith("/"):
            href = "https://ir.tesla.com" + href
        download_links.append({
            "text": a.get_text(strip=True),
            "url": href
        })

# Print the results
for link in download_links:
    print(f"{link['text']}: {link['url']}")

# Optionally, save to a CSV
with open("tesla_download_links.csv", "w", newline='', encoding="utf-8") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=["text", "url"])
    writer.writeheader()
    writer.writerows(download_links)

# Download the files to pdf_downloads_tesla directory
download_dir = "pdf_downloads_tesla"
os.makedirs(download_dir, exist_ok=True)

for link in download_links:
    url = link["url"]
    filename = os.path.basename(url.split("?")[0])  # Remove query params if any
    # Add .pdf if no extension is present
    if not os.path.splitext(filename)[1]:
        filename += ".pdf"
    dest_path = os.path.join(download_dir, filename)
    try:
        print(f"Downloading {url} -> {dest_path}")
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(response.content)
    except Exception as e:
        print(f"Failed to download {url}: {e}")