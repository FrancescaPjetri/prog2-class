import os
import glob
import re
from PyPDF2 import PdfReader
# Quivr is not used in this core logic, can be removed if not needed elsewhere
# from quivr_core import Brain 
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import yaml
from collections import defaultdict


# --- Configuration ---
CONTEXT_DIR = "contexts"
OUTPUT_DIR = "summaries"
CONTEXT_OUTPUT_FILE_TEMPLATE = os.path.join(CONTEXT_DIR, "{company_name}_latest_context.txt")
SUMMARY_OUTPUT_FILE_TEMPLATE = os.path.join(OUTPUT_DIR, "{company_name}_summary_latest_{year}.txt")
TABLE_OUTPUT_FILE_TEMPLATE = os.path.join(OUTPUT_DIR, "{company_name}_{year}_table.txt")
TARGET_START_YEAR = 2024
TARGET_END_YEAR = 2030 
SETTINGS_FILE = "settings.yaml"

# List of input folders to search for PDFs
INPUT_FOLDERS = [
    "pdf_downloads_airbnb",
    "pdf_downloads_alphabet",
    "pdf_downloads_apple",
    "pdf_downloads_nvidia",
    "pdf_downloads_tesla"
]


# --- NEW: FEW-SHOT PROMPT CONFIGURATION ---
# This dictionary holds the "gold standard" examples for each company.
# The AI will be instructed to copy the style of the relevant example.

PROMPT_CONFIG = {
    "APPLE": """
You are a financial analyst who emulates writing styles perfectly.
Your task is to summarize the new earnings report provided below so that it matches the style, tone, and structure of the example summary.

--- EXAMPLE SUMMARY ---

### Q2 Key Metrics
* **EPS:** $1.65
* **Revenue:** $95.4B
* **iPhone Revenue:** $46.84B
* **Services Revenue:** $26.65B
* **Gross Margin:** 47.1%

### Business Performance and Q3 Guidance
Apple's net income grew to $24.78 billion from $23.64 billion a year ago. The key iPhone product line topped estimates with sales up nearly 2% annually. While Services revenue grew 11.65% to $26.65B, this represented a deceleration from the 14.2% growth seen in the prior year's quarter. For Q3, the company expects "low to mid-single digits" revenue growth and a gross margin of 46% at the midpoint.

### Strategic Focus: Tariffs and Supply Chain
CEO Tim Cook stated tariffs had a "limited impact" in the quarter due to supply chain optimization. However, they are expected to add **$900 million to costs** in the current quarter. To mitigate this, Cook confirmed Apple is sourcing about half of its iPhones for the U.S. from **India** and most other products from **Vietnam**, while still making the "vast majority" of products for other countries in China.

### Segment Deep Dive: Hardware and Regional Sales
Mac sales rose nearly 7% to just under $8 billion, and iPad sales surged 15% to $6.4 billion following new model releases. The Wearables division was a weak spot, declining 5% to $7.52 billion, which Cook partly attributed to a tough comparison against the Vision Pro launch in the year-ago quarter. Sales in Greater China were down slightly, but would have been flat excluding foreign exchange rates, while sales in the Americas grew nearly 8%.

### AI Updates and Shareholder Returns
The company announced it would delay some of its anticipated AI features for Siri to the "coming year" to meet its "high quality bar." On the capital return front, the board authorized up to **$100 billion in share repurchases** and increased the dividend by 4% to 26 cents per share.

--- END EXAMPLE SUMMARY ---

Now, using the new report text provided below, generate a new summary that is similair in the style of the example. Also include information that could be important for retail investors. Also inlclude and dedicate a big part of the summary on the guidance of the company. 

--- NEW REPORT TEXT ---
{text_to_summarize}
--- END NEW REPORT TEXT ---

New Summary:
""",
    "AIRBNB": """
You are a financial analyst who emulates writing styles perfectly.
Your task is to summarize the new earnings report provided below so that it matches the style, tone, and structure of the example summary.

--- EXAMPLE SUMMARY ---

### Q1 Key Metrics vs. Expectations
* **Earnings per share (EPS):** 24 cents
* **Revenue:** $2.27 billion
* **Gross Booking Value (GBV):** $24.5 billion, up 7% YoY .
* **Nights & Experiences Booked:** 143.1 million

### Financial Performance and Q2 Guidance
Revenue increased 6% year-over-year, but net income saw a significant drop to $154 million from $264 million in the prior-year period. For Q2, the company projects revenue between $2.99 billion and $3.05 billion, with the midpoint slightly missing analyst forecasts of $3.04 billion. This guidance includes an expected two-percentage-point benefit from the timing of Easter.

### Regional Performance: A Tale of Two Markets
The company reported "relatively softer results" in the U.S., attributing the weakness to "broader economic uncertainties." In contrast, international markets showed strength, with nights and experiences booked (excluding North America) growing 11% YoY. Latin America was highlighted as the fastest-growing region, and bookings from Canada to Mexico saw a 27% jump in March.

### Platform and Operational Updates
Airbnb teased upcoming updates to its platform that will expand beyond accommodations. On the operational front, the company has removed 450,000 listings since updating its host quality system in 2023 to improve user experience.

--- END EXAMPLE SUMMARY ---

Now, using the new report text provided below, generate a new summary that is similair in the style of the example. Also include information that could be important for retail investors. Also inlclude and dedicate a big part of the summary on the guidance of the company.

--- NEW REPORT TEXT ---
{text_to_summarize}
--- END NEW REPORT TEXT ---

New Summary:
""",
    "NVIDIA": """
You are a financial analyst who emulates writing styles perfectly.
Your task is to summarize the new earnings report provided below so that it matches the style, tone, and structure of the example summary.

--- EXAMPLE SUMMARY ---

### Q1 Key Metrics vs. Expectations
* **Earnings per share (EPS):** 96 cents adjusted
* **Revenue:** $44.06 billion
* **Net Income:** $18.8 billion, an increase of 26% year-over-year.

### The China Impact: H20 Export Ban
The company's guidance and gross margin were significantly impacted by a U.S. government export restriction on its China-bound H20 processor. Nvidia incurred **$4.5 billion in charges** related to excess inventory for the chip. The company's guidance of $45 billion for the next quarter would have been about **$8 billion higher** without the restriction. CEO Jensen Huang stated the $50 billion AI chip market in China is now "effectively closed to U.S. industry."

### Core Business Performance: Data Center Growth
Despite the China headwinds, overall revenue grew an impressive 69% YoY. The **Data Center division** was the primary driver, with sales surging 73% annually to **$39.1 billion**, now accounting for 88% of total revenue. Large cloud providers made up just under half of the data center revenue, and a notable $5 billion in sales came from networking products. As a sign of strong future demand, CFO Colette Kress noted that Microsoft has "deployed tens of thousands of Blackwell GPUs."

### Other Segment Highlights
* **Gaming:** Grew 42% annually to $3.8 billion, with its chips still powering the upcoming Nintendo Switch 2.
* **Automotive & Robotics:** Grew 72% to $567 million, driven by sales for self-driving car systems.
* **Professional Visualization:** Grew 19% to $509 million.

### Shareholder Returns
The company was active in returning capital to shareholders, spending **$14.1 billion on share repurchases** and paying $244 million in dividends during the quarter.

--- END EXAMPLE SUMMARY ---

Now, using the new report text provided below, generate a new summary that is similair in the style of the example. Also include information that could be important for retail investors. Also inlclude and dedicate a big part of the summary on the guidance of the company.

--- NEW REPORT TEXT ---
{text_to_summarize}
--- END NEW REPORT TEXT ---

New Summary:
""",
    "ALPHABET": """
You are a financial analyst who emulates writing styles perfectly.
Your task is to summarize the new earnings report provided below so that it matches the style, tone, and structure of the example summary.

--- EXAMPLE SUMMARY ---

### Q4 Key Metrics vs. Expectations
* **Revenue:** $96.47B 
* **Earnings per share (EPS):** $2.15 
* **YouTube advertising revenue:** $10.47B 
* **Google Cloud revenue:** $11.96B 
* **Traffic acquisition costs (TAC):** $14.89B

### Business Performance & Growth
Alphabet's overall revenue grew nearly 12% year-over-year, a slight deceleration from the 13% growth in the prior year's quarter. The company's fourth-quarter net income increased over 28% to $26.54 billion from $20.69 billion a year prior. While Google Cloud revenue missed analyst estimates, it still grew a robust 30% from the year prior.

### Strategic Focus: Aggressive AI Capital Expenditures
A key announcement was the plan to invest **$75 billion in capital expenditures in 2025** to expand its AI strategy, significantly above the $58.84 billion Wall Street expected. The CFO confirmed this investment is primarily for technical infrastructure, with servers and data centers being the largest components to support growth across all Google divisions.

### Segment Analysis: Cloud and Other Bets
The Cloud unit faced a "tight supply-demand situation," with the CFO noting that the company "exited the year with more demand than we had available capacity." The 'Other Bets' segment, including Waymo, reported revenue of $400 million, down 39% YoY and missing expectations. However, Waymo is expanding its robotaxi service, launching in Austin and internationally in Tokyo in 2025.

--- END EXAMPLE SUMMARY ---

Now, using the new report text provided below, generate a new summary that is similair in the style of the example. Also include information that could be important for retail investors. Also inlclude and dedicate a big part of the summary on the guidance of the company.

--- NEW REPORT TEXT ---
{text_to_summarize}
--- END NEW REPORT TEXT ---

New Summary:
""",
    # The DEFAULT prompt is a "zero-shot" instruction, for companies without an example.
    "DEFAULT": """
You are a financial analyst. Your task is to provide a comprehensive summary of the following earnings report.
Format the output in Markdown. Use headings for different sections (e.g., Key Financial Highlights, Business Segment Performance, Trends, Outlook).
Use bullet points for lists of items. Bold key terms or figures.

Report Text:
{text_to_summarize}
"""
}


def load_settings(settings_path):
    """Loads settings from a YAML file."""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
            return settings
    except (FileNotFoundError, yaml.YAMLError):
        print(f"Warning: Could not load settings from {settings_path}")
        return None

settings = load_settings(SETTINGS_FILE)
GOOGLE_API_KEY = None
if settings:
    GOOGLE_API_KEY = settings.get('google_api_key')

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
    print(f"Warning: 'google_api_key' not found or is a placeholder in '{SETTINGS_FILE}'. Google AI calls will fail.")


def get_pdf_files_from_folders(folders):
    pdf_files = []
    for folder in folders:
        pdf_files.extend(glob.glob(os.path.join(folder, "**", "*.pdf"), recursive=True))
    return pdf_files


def extract_text_from_pdf(pdf_path):
    print(f"Extracting text from: {pdf_path}")
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page_num, page in enumerate(reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception as e_page:
                print(f"Error extracting text from page {page_num + 1} of {pdf_path}: {e_page}")
                continue
        return text
    except Exception as e_file:
        print(f"Error reading or processing PDF file {pdf_path}: {e_file}")
        return ""


def call_google_ai(prompt_text, task_description="task", model_name="gemini-1.5-flash-latest"):
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
        msg = f"Error: GOOGLE_API_KEY is not properly set for {task_description}."
        print(msg)
        return msg

    print(f"Performing {task_description} with Google AI model: {model_name}...")
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        model = genai.GenerativeModel(model_name)
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        generation_config = genai.types.GenerationConfig(
            candidate_count=1, max_output_tokens=8192, temperature=0.5 
        )
        response = model.generate_content(
            prompt_text, generation_config=generation_config, safety_settings=safety_settings
        )
        return response.text

    except Exception as e:
        print(f"Error during Google AI {task_description}: {e}")
        return f"Error during {task_description}: {e}"


# --- MODIFIED: This function now uses the PROMPT_CONFIG dictionary ---
def generate_summary_with_google_ai(text_to_summarize, company_name):
    """
    Generates a summary using a company-specific few-shot prompt.
    """
    if not text_to_summarize: 
        return "No content available for summarization."

    # Get the correct prompt template, which now includes the example summary.
    # Fall back to the 'DEFAULT' instruction-based prompt if no example exists.
    prompt_template = PROMPT_CONFIG.get(company_name.upper(), PROMPT_CONFIG['DEFAULT'])
    
    # Fill the placeholder with the new report text
    final_prompt = prompt_template.format(text_to_summarize=text_to_summarize)
    
    return call_google_ai(final_prompt, f"Few-shot summary generation for {company_name}")


def generate_yearly_table_with_google_ai(year, yearly_text):
    if not yearly_text: return f"No content available for year {year} to create a table."
    prompt = (
        f"From the following financial text for the year {year}, extract key data points and present them in a Markdown table. The table should have two columns: 'Metric' and 'Value'. "
        f"Include items like: Revenue, Net Income, EPS, Gross Margin, Operating Income, etc. Ensure the output is only the Markdown table.\n\n"
        f"Text for {year}:\n{yearly_text}"
    )
    return call_google_ai(prompt, f"Markdown table generation for {year}")


def group_pdfs_by_company_and_year(pdf_files, start_year, end_year):
    """Group PDFs by company (parent folder) and year."""
    grouped = defaultdict(lambda: defaultdict(list))
    year_regex = re.compile(r'(19|20)\d{2}|FY(\d{2})|F[1-4]Q(\d{2})|Q(\d{2})')
    for pdf_path in pdf_files:
        try:
            company = os.path.basename(os.path.dirname(pdf_path)).replace('pdf_downloads_', '').upper()
            filename = os.path.basename(pdf_path)
            match = year_regex.search(filename)
            year = None
            if match:
                if match.group(1): year = int(match.group(0))
                elif match.group(2): year = int('20' + match.group(2))
                elif match.group(3): year = int('20' + match.group(3))
                elif match.group(4): year = int('20' + match.group(4))
            
            if company and year and start_year <= year <= end_year:
                grouped[company][year].append(pdf_path)
        except Exception as e:
            print(f"Could not process path {pdf_path}: {e}")

    for company in grouped:
        for year in grouped[company]:
            grouped[company][year].sort()
            
    return grouped


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


def main():
    print("Starting earnings report processing...")
    ensure_dir(OUTPUT_DIR)
    ensure_dir(CONTEXT_DIR) 
    for folder in INPUT_FOLDERS:
        ensure_dir(folder)

    all_pdf_files = get_pdf_files_from_folders(INPUT_FOLDERS)
    if not all_pdf_files:
        print(f"No PDF files found in input folders: {INPUT_FOLDERS}.")
        return

    grouped = group_pdfs_by_company_and_year(all_pdf_files, TARGET_START_YEAR, TARGET_END_YEAR)
    if not grouped:
        print(f"No PDF files found matching the year range {TARGET_START_YEAR}-{TARGET_END_YEAR}.")
        return

    for company, years_dict in grouped.items():
        print(f"\n--- Processing company: {company} ---")

        if not years_dict:
            print(f"No reports found for {company} in the specified year range.")
            continue

        latest_year = max(years_dict.keys())
        newest_pdf_path = years_dict[latest_year][-1]
        
        print(f"Identified newest report: {os.path.basename(newest_pdf_path)}")

        full_report_text = extract_text_from_pdf(newest_pdf_path)

        if not full_report_text.strip():
            print(f"No text could be extracted from {newest_pdf_path}. Skipping {company}.")
            continue

        context_filename = CONTEXT_OUTPUT_FILE_TEMPLATE.format(company_name=company)
        try:
            with open(context_filename, "w", encoding="utf-8") as f:
                f.write(full_report_text)
            print(f"Full text context saved to: {context_filename}")
        except IOError as e:
            print(f"Error saving context file for {company}: {e}")

        # --- MODIFIED: Pass the company name to the summary generator ---
        print(f"Generating style-matched summary for {company}...")
        summary_content = generate_summary_with_google_ai(full_report_text, company)
        
        summary_filename = SUMMARY_OUTPUT_FILE_TEMPLATE.format(company_name=company, year=latest_year)
        try:
            with open(summary_filename, "w", encoding="utf-8") as f:
                f.write(summary_content)
            print(f"Display summary saved to: {summary_filename}")
        except IOError as e:
            print(f"Error saving summary file: {e}")

        print(f"Generating data table for {company}...")
        table_content = generate_yearly_table_with_google_ai(latest_year, full_report_text)
        table_filename = TABLE_OUTPUT_FILE_TEMPLATE.format(company_name=company, year=latest_year)
        try:
            with open(table_filename, "w", encoding="utf-8") as f:
                f.write(table_content)
            print(f"Data table saved to: {table_filename}")
        except IOError as e:
            print(f"Error saving table file: {e}")

    print("\nProcess completed.")


if __name__ == "__main__":
    main()

#check this is the final version 
