import os
import glob
import re
from PyPDF2 import PdfReader
from quivr_core import Brain
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import yaml
from collections import defaultdict


# --- Configuration ---
EARNINGS_DIR = "earnings"
# Output files will be in the project root
OUTPUT_DIR = "summaries"
SUMMARY_OUTPUT_FILE_TEMPLATE = os.path.join(OUTPUT_DIR, "{company_name}_summary_{start_year}-{end_year}.txt")
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
OPENAI_API_KEY = None
COMPANY_NAME = "DefaultCompany"


if settings:
    GOOGLE_API_KEY = settings.get('google_api_key')
    OPENAI_API_KEY = settings.get('openai_api_key')
    COMPANY_NAME = settings.get('company_name', COMPANY_NAME)
    if OPENAI_API_KEY and OPENAI_API_KEY != "YOUR_OPENAI_API_KEY":
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
        print("OPENAI_API_KEY set from settings.yaml for Quivr.")
    elif not OPENAI_API_KEY or OPENAI_API_KEY == "YOUR_OPENAI_API_KEY":
        print("Warning: 'openai_api_key' not found or is a placeholder in settings.yaml. Quivr might not function correctly if it relies on OpenAI.")

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
    print(f"Warning: 'google_api_key' not found or is a placeholder in '{SETTINGS_FILE}'. Google AI calls will fail.")


def get_pdf_files(directory):
    return glob.glob(os.path.join(directory, "*.pdf"))


def get_pdf_files_from_folders(folders):
    pdf_files = []
    for folder in folders:
        pdf_files.extend(glob.glob(os.path.join(folder, "**", "*.pdf"), recursive=True))
    return pdf_files


def filter_pdfs_by_year_range(pdf_files, start_year, end_year):
    filtered_files_by_year = {}
    # Enhanced regex: match 4-digit years, FYxx, Qxx, F1Qxx, etc.
    year_regex = re.compile(r'(19|20)\d{2}|FY(\d{2})|F[1-4]Q(\d{2})|Q(\d{2})')
    actual_years_found = set()

    for pdf_path in pdf_files:
        filename = os.path.basename(pdf_path)
        match = year_regex.search(filename)
        year = None
        if match:
            if match.group(1):  # 4-digit year
                year = int(match.group(0))
            elif match.group(2):  # FYxx
                year = int('20' + match.group(2))
            elif match.group(3):  # F1Qxx, F2Qxx, etc.
                year = int('20' + match.group(3))
            elif match.group(4):  # Qxx
                year = int('20' + match.group(4))
        if year and start_year <= year <= end_year:
            if year not in filtered_files_by_year:
                filtered_files_by_year[year] = []
            filtered_files_by_year[year].append(pdf_path)
            actual_years_found.add(year)
    
    if not actual_years_found:
        print(f"No PDFs found within the year range {start_year}-{end_year} based on filename patterns.")
        return {}, None, None
        
    min_year_in_filtered = min(actual_years_found) if actual_years_found else start_year
    max_year_in_filtered = max(actual_years_found) if actual_years_found else end_year
    
    for year in filtered_files_by_year:
        filtered_files_by_year[year].sort()
        
    return filtered_files_by_year, min_year_in_filtered, max_year_in_filtered


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


def create_quivr_brain(pdf_files, brain_name="earnings_reports_brain"):
    if not pdf_files:
        print("No PDF files provided to create Quivr brain.")
        return None
    if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "YOUR_OPENAI_API_KEY":
        print("Quivr Brain creation skipped: OPENAI_API_KEY not set or is a placeholder.")
        print("If Quivr is configured to use a different LLM/embedding provider that doesn't need OpenAI, this might be okay.")
        return None
        
    print(f"Creating Quivr Brain '{brain_name}' with {len(pdf_files)} PDF(s)...")
    try:
        brain = Brain.from_files(name=brain_name, file_paths=pdf_files)
        print(f"Quivr Brain '{brain.name}' created successfully.")
        return brain
    except Exception as e:
        print(f"Error creating Quivr Brain: {e}")
        return None


def call_google_ai(prompt_text, task_description="task", model_name="gemini-1.5-flash-latest"):
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
        msg = f"Error: GOOGLE_API_KEY is not properly set for {task_description}. Please check '{SETTINGS_FILE}'."
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
            candidate_count=1, max_output_tokens=8192, temperature=0.7
        )
        response = model.generate_content(
            prompt_text, generation_config=generation_config, safety_settings=safety_settings
        )
        
        if response.candidates and response.candidates[0].finish_reason == 1:
            print(f"{task_description.capitalize()} completed successfully.")
            return response.text
        else:
            reason_map = {1: "STOP", 2: "MAX_TOKENS", 3: "SAFETY", 4: "RECITATION", 5: "OTHER"}
            reason_str = "UNKNOWN"
            block_reason_str = "N/A"
            if response.candidates:
                 reason_str = reason_map.get(response.candidates[0].finish_reason, "UNKNOWN")
            if response.prompt_feedback:
                block_reason_str = response.prompt_feedback.block_reason or "N/A"

            err_msg = f"{task_description.capitalize()} failed or was incomplete. Finish Reason: {reason_str}. Block Reason: {block_reason_str}."
            print(err_msg)
            if response.text: return response.text + f"\n\n[Note: {task_description} may be incomplete due to finish reason: {reason_str}]"
            return err_msg

    except Exception as e:
        print(f"Error during Google AI {task_description}: {e}")
        return f"Error during {task_description}: {e}"


def generate_summary_with_google_ai(text_to_summarize):
    if not text_to_summarize: return "No content available for summarization."
    prompt = (
        f"Please provide a comprehensive summary of the following earnings reports. "
        f"Format the output in Markdown. Use headings for different sections (e.g., Key Financial Highlights, Trends, Outlook). "
        f"Use bullet points for lists of items. Bold key terms or figures.\n\n"
        f"Reports Text:\n{text_to_summarize}"
    )
    return call_google_ai(prompt, "Markdown summary generation")


def generate_yearly_table_with_google_ai(year, yearly_text):
    if not yearly_text: return f"No content available for year {year} to create a table."
    prompt = (
        f"From the following financial text for the year {year}, extract key data points and present them in a Markdown table. "
        f"The table should have two columns: 'Metric' and 'Value'. "
        f"Include items like: Revenue, Net Income, EPS (Earnings Per Share), Gross Margin (%), Operating Income, Operating Expenses, Cash Flow from Operations, Capital Expenditures, and any key guidance or outlook figures if available. "
        f"If a specific figure isn't present for a common item, you can note 'N/A' or omit the row. "
        f"Ensure the output is only the Markdown table.\n\n"
        f"Text for {year}:\n{yearly_text}"
    )
    return call_google_ai(prompt, f"Markdown table generation for {year}")


def group_pdfs_by_company_and_year(pdf_files, start_year, end_year):
    """Group PDFs by company (parent folder) and year."""
    grouped = defaultdict(lambda: defaultdict(list))  # {company: {year: [pdfs]}}
    year_regex = re.compile(r'(19|20)\d{2}|FY(\d{2})|F[1-4]Q(\d{2})|Q(\d{2})')
    for pdf_path in pdf_files:
        # Get company from parent folder
        company = os.path.basename(os.path.dirname(pdf_path)).replace('pdf_downloads_', '').upper()
        filename = os.path.basename(pdf_path)
        match = year_regex.search(filename)
        year = None
        if match:
            if match.group(1):
                year = int(match.group(0))
            elif match.group(2):
                year = int('20' + match.group(2))
            elif match.group(3):
                year = int('20' + match.group(3))
            elif match.group(4):
                year = int('20' + match.group(4))
        if year and start_year <= year <= end_year:
            grouped[company][year].append(pdf_path)
    return grouped


def main():
    print("Starting earnings report processing...")
    ensure_dir(OUTPUT_DIR)
    for folder in INPUT_FOLDERS:
        ensure_dir(folder)

    all_pdf_files = get_pdf_files_from_folders(INPUT_FOLDERS)
    if not all_pdf_files:
        print(f"No PDF files found in input folders: {INPUT_FOLDERS}.")
        return
    print(f"Found {len(all_pdf_files)} PDF(s) in input folders: {INPUT_FOLDERS}.")

    # Group PDFs by company and year
    grouped = group_pdfs_by_company_and_year(all_pdf_files, TARGET_START_YEAR, TARGET_END_YEAR)
    if not grouped:
        print(f"No PDF files found matching the year range {TARGET_START_YEAR}-{TARGET_END_YEAR}.")
        return

    for company, years_dict in grouped.items():
        print(f"\nProcessing company: {company}")
        overall_combined_text_for_summary = ""
        min_year = min(years_dict.keys())
        max_year = max(years_dict.keys())
        for year in sorted(years_dict.keys()):
            print(f"\nProcessing year: {year}")
            yearly_text_parts = []
            for pdf_path in years_dict[year]:
                text = extract_text_from_pdf(pdf_path)
                if text:
                    yearly_text_parts.append(f"\n--- Report: {os.path.basename(pdf_path)} ---\n{text}")
            if not yearly_text_parts:
                print(f"No text could be extracted for year {year}.")
                continue
            current_year_combined_text = "".join(yearly_text_parts)
            overall_combined_text_for_summary += current_year_combined_text
            table_content = generate_yearly_table_with_google_ai(year, current_year_combined_text.strip())
            table_filename = TABLE_OUTPUT_FILE_TEMPLATE.format(company_name=company, year=year)
            try:
                with open(table_filename, "w", encoding="utf-8") as f:
                    f.write(table_content)
                print(f"Table for year {year} saved to: {table_filename}")
            except IOError as e:
                print(f"Error saving table file for year {year}: {e}")
        if not overall_combined_text_for_summary.strip():
            print(f"No text could be extracted from any filtered PDFs for {company}. Cannot generate overall summary.")
            continue
        summary_content = generate_summary_with_google_ai(overall_combined_text_for_summary.strip())
        summary_filename = SUMMARY_OUTPUT_FILE_TEMPLATE.format(company_name=company, start_year=min_year, end_year=max_year)
        try:
            with open(summary_filename, "w", encoding="utf-8") as f:
                f.write(summary_content)
            print(f"\nOverall summary saved to: {summary_filename}")
        except IOError as e:
            print(f"Error saving overall summary file: {e}")
    print_final_messages()


def print_final_messages():
    print("\nProcess completed.")
    req_path = os.path.join(os.path.dirname(__file__), 'requirements.txt')
    print(f"To install dependencies, run: pip install -r {req_path}")
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
         print(f"WARNING: GOOGLE_API_KEY is not properly set. Please update it in '{SETTINGS_FILE}'.")
    if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "YOUR_OPENAI_API_KEY":
         print(f"WARNING: OPENAI_API_KEY is not properly set in '{SETTINGS_FILE}' or environment. Quivr functionality might be affected.")
    print(f"Make sure '{COMPANY_NAME}' in '{SETTINGS_FILE}' is set to your desired company name for output files.")


def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)


if __name__ == "__main__":
    main()

