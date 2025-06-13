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
# NEW: Directory to store the full extracted text for chat context
CONTEXT_DIR = "contexts"
OUTPUT_DIR = "summaries"
# NEW: Template for the full-text context file
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


def load_settings(settings_path):
    """Loads settings from a YAML file."""
    try:
        with open(settings_path, 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
            return settings
    except FileNotFoundError:
        print(f"Error: Settings file '{settings_path}' not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing YAML file '{settings_path}': {e}")
        return None


# Load settings
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
        
        # Increased token limit for potentially larger summaries
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


def generate_summary_with_google_ai(text_to_summarize):
    if not text_to_summarize: return "No content available for summarization."
    prompt = (
        f"Please provide a comprehensive summary of the following earnings report. "
        f"Format the output in Markdown. Use headings for different sections (e.g., Key Financial Highlights, Trends, Outlook). "
        f"Use bullet points for lists of items. Bold key terms or figures.\n\n"
        f"Reports Text:\n{text_to_summarize}"
    )
    return call_google_ai(prompt, "Markdown summary generation")


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
    # --- MODIFIED --- Ensure all needed directories exist
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

        # --- MODIFIED WORKFLOW ---
        # 1. Extract the FULL text from the newest PDF
        full_report_text = extract_text_from_pdf(newest_pdf_path)

        if not full_report_text.strip():
            print(f"No text could be extracted from {newest_pdf_path}. Skipping {company}.")
            continue

        # 2. NEW: Save the FULL extracted text to the `contexts` directory for the chat app
        context_filename = CONTEXT_OUTPUT_FILE_TEMPLATE.format(company_name=company)
        try:
            with open(context_filename, "w", encoding="utf-8") as f:
                f.write(full_report_text)
            print(f"Full text context saved to: {context_filename}")
        except IOError as e:
            print(f"Error saving context file for {company}: {e}")

        # 3. Generate a user-friendly summary from the full text for the main web page
        print(f"Generating summary for {company}...")
        summary_content = generate_summary_with_google_ai(full_report_text)
        summary_filename = SUMMARY_OUTPUT_FILE_TEMPLATE.format(company_name=company, year=latest_year)
        try:
            with open(summary_filename, "w", encoding="utf-8") as f:
                f.write(summary_content)
            print(f"Display summary saved to: {summary_filename}")
        except IOError as e:
            print(f"Error saving summary file: {e}")

        # 4. Generate the data table (optional, but nice to keep)
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

