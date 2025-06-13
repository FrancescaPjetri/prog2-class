import os
import glob
import yaml
import re
from flask import Flask, render_template_string, url_for, render_template, request, jsonify
from jinja2 import DictLoader
import markdown
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

app = Flask(__name__)

# --- Configuration ---
SETTINGS_FILE = "settings.yaml"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
# --- NEW --- Directory where full-text contexts are stored
CONTEXT_DIR = "contexts" 

def load_settings():
    """Loads settings from a YAML file."""
    try:
        with open(os.path.join(PROJECT_ROOT, SETTINGS_FILE), 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}
    except Exception as e:
        print(f"Error loading settings: {e}")
        return {}

settings = load_settings()
GOOGLE_API_KEY = settings.get('google_api_key')

if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
    print("WARNING: 'google_api_key' not found or is a placeholder in settings.yaml. The chat feature will not work.")


def call_google_ai(prompt_text, task_description="chat response"):
    """Calls the Google Gemini API with a specific prompt."""
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_GOOGLE_API_KEY":
        return "Error: The GOOGLE_API_KEY is not configured on the server."

    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        # Using 1.5 Pro because it has a very large context window, perfect for full reports
        model = genai.GenerativeModel("gemini-1.5-pro-latest")
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
        }
        
        response = model.generate_content(prompt_text, safety_settings=safety_settings)
        return response.text
    except Exception as e:
        print(f"Error during Google AI call: {e}")
        return f"An error occurred while contacting the AI model: {e}"


# --- HTML Templates (with modifications for new linking) ---

HTML_BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Earnings Viewer</title>
    <style>
        :root { --primary-color: #007bff; --primary-hover-color: #0056b3; --text-color: #212529; --text-light-color: #495057; --background-color: #f8f9fa; --card-background-color: #ffffff; --border-color: #dee2e6; --header-bg-color: #343a40; --header-text-color: #ffffff; --nav-link-color: #007bff; --nav-active-bg: #007bff; --nav-active-text: #ffffff; --table-border-color: #ced4da; --table-header-bg: #e9ecef; }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; margin: 0; background-color: var(--background-color); color: var(--text-color); line-height: 1.7; }
        .main-wrapper { display: flex; flex-direction: column; min-height: 100vh; }
        header { background-color: var(--header-bg-color); color: var(--header-text-color); padding: 1.5em 1em; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
        header h1 { margin: 0; font-size: 2em; font-weight: 500; }
        nav { background-color: var(--card-background-color); padding: 1em 0; text-align: center; margin-bottom: 30px; border-bottom: 1px solid var(--border-color); box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        nav a { margin: 0 15px; text-decoration: none; color: var(--nav-link-color); font-weight: 500; padding: 0.7em 1.2em; border-radius: 0.3em; transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out; }
        nav a:hover, nav a.active { background-color: var(--primary-color); color: var(--nav-active-text); }
        .container { flex: 1; width: 90%; max-width: 1400px; margin: 0 auto 40px; padding: 30px; background-color: var(--card-background-color); border-radius: 10px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
        h2 { color: var(--text-color); border-bottom: 2px solid var(--primary-color); padding-bottom: 0.6em; margin: 0 0 1.5em; font-size: 1.8em; font-weight: 500; }
        h3 { font-size: 1.4em; font-weight: 500; margin-bottom: 1em; color: var(--text-light-color); }
        ul { list-style-type: none; padding: 0; }
        li { margin-bottom: 1em; background: #fdfdfd; padding: 15px; border-radius: 5px; border: 1px solid #eee; display: flex; justify-content: space-between; align-items: center; }
        .file-link { text-decoration: none; color: var(--primary-color); font-weight: 500; font-size: 1.1em; transition: color 0.2s; }
        .file-link:hover { color: var(--primary-hover-color); text-decoration: underline;}
        .file-actions a { margin-left: 15px; text-decoration: none; background: #eee; padding: 5px 12px; border-radius: 5px; font-size: 0.9em; transition: background 0.2s;}
        .file-actions a:hover { background: #ddd; }
        .file-actions .chat-link { background-color: var(--primary-color); color: white; }
        .file-actions .chat-link:hover { background-color: var(--primary-hover-color); }
        .back-link { display: inline-block; margin-top: 2em; padding: 0.7em 1.2em; background-color: var(--primary-color); color: var(--nav-active-text); text-decoration: none; border-radius: 0.3em; }
        footer { text-align: center; margin-top: auto; padding: 2em; font-size: 0.9em; color: #6c757d; border-top: 1px solid var(--border-color); }
    </style>
    {% block extra_styles %}{% endblock %}
</head>
<body>
    <div class="main-wrapper">
        <header><h1>Earnings Viewer</h1></header>
        <nav>
            <a href="{{ url_for('list_summaries') }}" class="{{ 'active' if active_page == 'summaries' else '' }}">Summaries</a>
            <a href="{{ url_for('list_tables') }}" class="{{ 'active' if active_page == 'tables' else '' }}">Tables</a>
        </nav>
        <div class="container">
            <h2>{{ title }}</h2>
            {% block content %}{% endblock %}
        </div>
        <footer><p>Earnings Data Viewer &copy; 2025</p></footer>
    </div>
</body>
</html>
"""

HTML_LIST_PAGE = """
{% extends 'base.html' %}
{% block content %}
    {% if files %}
        <ul>
        {% for file in files %}
            <li>
                <a href="{{ url_for('view_file', type=active_page, filename=file.name) }}" class="file-link">{{ file.display_name }}</a>
                <span class="file-actions">
                    <a href="{{ url_for('view_file', type=active_page, filename=file.name) }}">View</a>
                    {# MODIFIED: Chat link now uses company name #}
                    {% if active_page == 'summaries' and file.company %}
                    <a href="{{ url_for('chat', company_name=file.company) }}" class="chat-link">Chat</a>
                    {% endif %}
                </span>
            </li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No {{ active_page }} found. Please run the data processing script.</p>
    {% endif %}
{% endblock %}
"""

HTML_VIEW_FILE_PAGE = """
{% extends 'base.html' %}
{% block content %}
    <h3>{{ filename }}</h3>
    {% if html_content %}
        <div class="file-content-markdown">{{ html_content|safe }}</div>
    {% else %}
        <p>Could not read file content.</p>
    {% endif %}
    <a href="{{ url_for('list_' + type) }}" class="back-link">&larr; Back to {{ type }} list</a>
{% endblock %}
"""

HTML_CHAT_PAGE = """
{% extends 'base.html' %}
{% block extra_styles %}
<style>
    .chat-container { display: flex; flex-direction: column; height: 65vh; }
    .chat-box { flex-grow: 1; overflow-y: auto; padding: 20px; border: 1px solid var(--border-color); border-radius: 8px 8px 0 0; background-color: #fff; }
    .chat-message { max-width: 80%; margin-bottom: 15px; padding: 12px 18px; border-radius: 18px; line-height: 1.5; word-wrap: break-word; }
    .chat-message.user { background-color: var(--primary-color); color: white; margin-left: auto; border-bottom-right-radius: 4px; }
    .chat-message.bot { background-color: #e9ecef; color: var(--text-color); margin-right: auto; border-bottom-left-radius: 4px; }
    .chat-message.error { background-color: #f8d7da; color: #721c24; }
    #chat-form { display: flex; border: 1px solid var(--border-color); border-top: none; }
    #chat-input { flex-grow: 1; border: none; padding: 15px; font-size: 1em; outline: none; }
    #send-btn { background-color: var(--primary-color); color: white; border: none; padding: 0 25px; cursor: pointer; }
    #send-btn:disabled { background-color: #a0c3e6; }
</style>
{% endblock %}
{% block content %}
    <h3>Chat about {{ company_name }}'s Latest Report</h3>
    <div class="chat-container">
        <div class="chat-box" id="chat-box">
             <div class="chat-message bot">Hello! Ask me any questions about the full text of the latest report for {{ company_name }}.</div>
        </div>
        <form id="chat-form" class="chat-input-form">
            <input type="text" id="chat-input" placeholder="Ask a detailed question..." autocomplete="off">
            <button type="submit" id="send-btn">Send</button>
        </form>
    </div>
    <a href="{{ url_for('list_summaries') }}" class="back-link">&larr; Back to Summaries</a>
    <script>
        document.addEventListener('DOMContentLoaded', () => {
            const chatForm = document.getElementById('chat-form');
            const chatInput = document.getElementById('chat-input');
            const chatBox = document.getElementById('chat-box');
            const sendBtn = document.getElementById('send-btn');
            // MODIFIED: We now use the company name to identify the context
            const companyName = "{{ company_name|safe }}";

            chatForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const question = chatInput.value.trim();
                if (!question) return;

                appendMessage(question, 'user');
                chatInput.value = '';
                sendBtn.disabled = true;
                sendBtn.innerText = '...';

                try {
                    const response = await fetch('/api/ask', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        // MODIFIED: Sending company_name instead of a filename
                        body: JSON.stringify({ question: question, company_name: companyName })
                    });
                    if (!response.ok) throw new Error(`Server error: ${response.statusText}`);
                    const data = await response.json();
                    // Using markdown-it in the future would be better, but for now, simple replace.
                    const formattedAnswer = data.answer.replace(/\\n/g, '<br>');
                    appendMessage(formattedAnswer, 'bot', true);
                } catch (error) {
                    appendMessage(`Error: ${error.message}`, 'error');
                } finally {
                    sendBtn.disabled = false;
                    sendBtn.innerText = 'Send';
                }
            });

            function appendMessage(text, type, isHTML = false) {
                const messageDiv = document.createElement('div');
                messageDiv.classList.add('chat-message', type);
                if (isHTML) {
                    messageDiv.innerHTML = text;
                } else {
                    messageDiv.textContent = text;
                }
                chatBox.appendChild(messageDiv);
                chatBox.scrollTop = chatBox.scrollHeight;
            }
        });
    </script>
{% endblock %}
"""

app.jinja_loader = DictLoader({
    'base.html': HTML_BASE,
    'list_page.html': HTML_LIST_PAGE,
    'view_file_page.html': HTML_VIEW_FILE_PAGE,
    'chat_page.html': HTML_CHAT_PAGE,
})

# --- MODIFIED: get_files now extracts the company name ---
def get_files(pattern_suffix):
    """Get all summary or table files and extract company name."""
    pattern = os.path.join("summaries", pattern_suffix)
    files_found = []
    for filepath in glob.glob(os.path.join(PROJECT_ROOT, pattern)):
        filename = os.path.basename(filepath)
        company_name_match = re.match(r'^([A-Z0-9]+)_', filename)
        company_name = company_name_match.group(1) if company_name_match else None
        
        display_name = filename.replace(".txt", "").replace("_", " ").title()
        files_found.append({"name": filename, "display_name": display_name, "company": company_name})
    return sorted(files_found, key=lambda x: x['display_name'], reverse=True)


@app.route('/')
def index():
    return list_summaries()

@app.route('/summaries')
def list_summaries():
    return render_template('list_page.html', title="Summaries", files=get_files("*_summary_*.txt"), active_page="summaries")

@app.route('/tables')
def list_tables():
    return render_template('list_page.html', title="Tables", files=get_files("*_table.txt"), active_page="tables")

@app.route('/view/<type>/<filename>')
def view_file(type, filename):
    filepath = os.path.join(PROJECT_ROOT, "summaries", filename)
    html_output = ""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            html_output = markdown.markdown(raw_content, extensions=['tables'])
    except Exception as e:
        html_output = f"<p>Error reading file: {e}</p>"
    title_prefix = "Summary" if type == "summaries" else "Table"
    return render_template('view_file_page.html', title=f"{title_prefix}: {filename}", filename=filename, html_content=html_output, active_page=type, type=type)

# --- MODIFIED: Chat route now uses company_name ---
@app.route('/chat/<company_name>')
def chat(company_name):
    """Renders the chat interface for a specific company."""
    # Check if the context file exists for this company
    context_filename = f"{company_name}_latest_context.txt"
    filepath = os.path.join(PROJECT_ROOT, CONTEXT_DIR, context_filename)
    if not os.path.exists(filepath):
        return "Chat context for this company has not been generated. Please run the processing script.", 404

    return render_template('chat_page.html', title=f"Chat with {company_name}", company_name=company_name, active_page="summaries")

# --- MODIFIED: API endpoint now uses company_name and reads from contexts/ dir ---
@app.route('/api/ask', methods=['POST'])
def api_ask():
    """Receives a question and a company name, gets an answer from Gemini using the full-text file as context."""
    data = request.get_json()
    if not data or 'question' not in data or 'company_name' not in data:
        return jsonify({'error': 'Invalid request: "question" and "company_name" are required.'}), 400

    question = data['question']
    company_name = data['company_name']

    # Find the full-text context file
    context_filename = f"{company_name.upper()}_latest_context.txt"
    filepath = os.path.join(PROJECT_ROOT, CONTEXT_DIR, context_filename)

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            report_text = f.read()
    except FileNotFoundError:
        return jsonify({'error': f'Context file not found for {company_name}.'}), 404
    except Exception as e:
        return jsonify({'error': f'Server error reading file: {e}'}), 500

    prompt = (
        "You are a precise financial analyst assistant. Your task is to answer questions based *only* "
        "on the text from the financial report provided below. Do not use any external knowledge, calculations, or assumptions. "
        "If the answer is not contained within the provided text, you must state: 'The answer to that question is not available in this report.'\n\n"
        "--- BEGIN REPORT TEXT ---\n"
        f"{report_text}\n"
        "--- END REPORT TEXT ---\n\n"
        f"Based only on the report text above, please answer the following question:\nQuestion: {question}"
    )
    answer = call_google_ai(prompt)
    return jsonify({'answer': answer})

if __name__ == '__main__':
    print("Starting Flask web app...")
    print(f"Make sure the '{CONTEXT_DIR}/' and 'summaries/' directories exist.")
    print("Run the `summarize_earnings.py` script first to generate context and summary files.")
    print("Navigate to http://127.0.0.1:5001 to begin.")
    app.run(debug=True, host='0.0.0.0', port=5001)

