import os
import glob
import yaml
from flask import Flask, render_template_string, url_for, render_template
from jinja2 import DictLoader, Environment
import markdown # Added for Markdown parsing

app = Flask(__name__)

SETTINGS_FILE = "settings.yaml"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def load_company_name():
    try:
        with open(os.path.join(PROJECT_ROOT, SETTINGS_FILE), 'r', encoding='utf-8') as f:
            settings = yaml.safe_load(f)
            return settings.get('company_name', 'DefaultCompany')
    except Exception:
        return 'DefaultCompany'

COMPANY_NAME = load_company_name()

# --- HTML Templates ---
HTML_BASE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - {{ company_name }} Earnings Viewer</title>
    <style>
        :root {
            --primary-color: #007bff; /* Blue accent */
            --primary-hover-color: #0056b3;
            --text-color: #212529; /* Darker text for better contrast */
            --text-light-color: #495057; /* Slightly darker light text */
            --background-color: #f8f9fa; /* Light grey background */
            --card-background-color: #ffffff;
            --border-color: #dee2e6;
            --header-bg-color: #343a40; /* Dark grey header */
            --header-text-color: #ffffff;
            --nav-link-color: #007bff;
            --nav-active-bg: #007bff;
            --nav-active-text: #ffffff;
            --code-bg-color: #f1f3f5; /* Lighter code background */
            --table-border-color: #ced4da;
            --table-header-bg: #e9ecef;
        }
        body { 
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0; 
            background-color: var(--background-color); 
            color: var(--text-color); 
            line-height: 1.7; /* Increased line height for readability */
        }
        .main-wrapper {
            display: flex;
            flex-direction: column;
            min-height: 100vh;
        }
        header { 
            background-color: var(--header-bg-color); 
            color: var(--header-text-color); 
            padding: 1.5em 1em; /* Slightly more padding */
            text-align: center; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        header h1 { 
            margin: 0; 
            font-size: 2em; /* Larger header text */
            font-weight: 500;
        }
        nav { 
            background-color: var(--card-background-color);
            padding: 1em 0;
            text-align: center; 
            margin-bottom: 30px; /* Increased margin */
            border-bottom: 1px solid var(--border-color);
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }
        nav a { 
            margin: 0 15px; /* More spacing for nav links */
            text-decoration: none; 
            color: var(--nav-link-color); 
            font-weight: 500; 
            padding: 0.7em 1.2em; /* Larger padding for nav links */
            border-radius: 0.3em; 
            transition: background-color 0.2s ease-in-out, color 0.2s ease-in-out; 
        }
        nav a:hover { 
            background-color: var(--primary-color);
            color: var(--nav-active-text);
        }
        nav a.active { 
            background-color: var(--nav-active-bg); 
            color: var(--nav-active-text); 
        }
        .container { 
            flex: 1;
            width: 90%; /* Use percentage for fluidity */
            max-width: 1400px; /* Increased max-width for wider container on large screens */
            margin-left: auto; /* Center the container */
            margin-right: auto; /* Center the container */
            margin-bottom: 40px; /* Bottom margin */
            padding: 30px; 
            background-color: var(--card-background-color); 
            border-radius: 10px; 
            box-shadow: 0 4px 20px rgba(0,0,0,0.08); 
        }
        h2 { 
            color: var(--text-color); 
            border-bottom: 2px solid var(--primary-color); 
            padding-bottom: 0.6em; 
            margin-top: 0;
            margin-bottom: 1.5em; 
            font-size: 1.8em; 
            font-weight: 500;
        }
        h3 {
            font-size: 1.4em; 
            font-weight: 500;
            margin-bottom: 1em;
            color: var(--text-light-color);
        }
        ul { list-style-type: none; padding: 0; }
        li { margin-bottom: 1em; } 
        li a { 
            text-decoration: none; 
            color: var(--primary-color); 
            font-weight: 500;
            font-size: 1.1em; 
            transition: color 0.2s;
        }
        li a:hover { color: var(--primary-hover-color); text-decoration: underline;}
        
        .file-content-markdown { 
            background-color: var(--card-background-color);
            padding: 0; 
            border-radius: 5px; 
            margin-top: 1em; 
        }
        .file-content-markdown h1, .file-content-markdown h2, .file-content-markdown h3, .file-content-markdown h4 {
            margin-top: 1.5em;
            margin-bottom: 0.8em;
            font-weight: 600;
            color: var(--text-color);
        }
        .file-content-markdown h1 { font-size: 1.8em; border-bottom: 1px solid var(--border-color); padding-bottom: 0.3em;}
        .file-content-markdown h2 { font-size: 1.5em; }
        .file-content-markdown h3 { font-size: 1.25em; }
        .file-content-markdown p { margin-bottom: 1.2em; color: var(--text-light-color); } 
        .file-content-markdown ul, .file-content-markdown ol { margin-left: 1.5em; margin-bottom: 1em; }
        .file-content-markdown li { margin-bottom: 0.5em; }
        .file-content-markdown table { 
            border-collapse: collapse; 
            width: 100%; 
            margin-bottom: 1.5em; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
            border: 1px solid var(--table-border-color);
        }
        .file-content-markdown th, .file-content-markdown td { 
            border: 1px solid var(--table-border-color); 
            padding: 0.8em 1em; 
            text-align: left; 
        }
        .file-content-markdown th { 
            background-color: var(--table-header-bg); 
            font-weight: 600;
        }
        .file-content-markdown tr:nth-child(even) { background-color: #fdfdfe; } 
        .file-content-markdown pre { 
            background-color: var(--code-bg-color); 
            padding: 1.2em; 
            border-radius: 6px; 
            overflow-x: auto; 
            border: 1px solid var(--border-color);
            margin-bottom: 1.2em;
        }
        .file-content-markdown code { 
            font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, Courier, monospace;
            font-size: 0.9em;
            background-color: var(--code-bg-color);
            padding: 0.2em 0.4em;
            border-radius: 3px;
        }
        .file-content-markdown pre code { background-color: transparent; padding: 0; }
        .file-content-markdown blockquote {
            border-left: 5px solid var(--primary-color); 
            padding-left: 1.5em; 
            margin-left: 0;
            margin-bottom: 1.2em;
            color: var(--text-light-color);
            font-style: italic;
        }
        .back-link {
            display: inline-block;
            margin-top: 2em; 
            padding: 0.7em 1.2em;
            background-color: var(--primary-color);
            color: var(--nav-active-text);
            text-decoration: none;
            border-radius: 0.3em;
            transition: background-color 0.2s;
            font-weight: 500;
        }
        .back-link:hover {
            background-color: var(--primary-hover-color);
        }

        footer { 
            text-align: center; 
            margin-top: auto; 
            padding: 2em; 
            font-size: 0.9em; 
            color: #6c757d; 
            background-color: var(--card-background-color);
            border-top: 1px solid var(--border-color);
        }
        /* Responsive adjustments for container width */
        @media (max-width: 1440px) { /* Matches max-width + some padding */
            .container { width: 95%; padding: 25px; }
        }
        @media (max-width: 768px) {
            header h1 { font-size: 1.7em; }
            nav a { margin: 0 8px; padding: 0.6em 1em; font-size: 0.9em;}
            .container { width: auto; margin-left: 20px; margin-right: 20px; padding: 20px; } /* Full width on smaller screens with padding */
            h2 { font-size: 1.5em; }
        }
        @media (max-width: 576px) {
            nav { flex-direction: column; }
            nav a { display: block; margin: 0.6em auto; width: 80%; }
            header h1 { font-size: 1.5em; }
            .container { margin-left: 15px; margin-right: 15px; padding: 15px; }
            h2 { font-size: 1.4em; }
        }
    </style>
</head>
<body>
    <div class="main-wrapper">
        <header>
            <h1>{{ company_name }} Earnings Viewer</h1>
        </header>
        <nav>
            <a href="{{ url_for('list_summaries') }}" class="{{ 'active' if active_page == 'summaries' else '' }}">Summaries</a>
            <a href="{{ url_for('list_tables') }}" class="{{ 'active' if active_page == 'tables' else '' }}">Tables</a>
        </nav>
        <div class="container">
            <h2>{{ title }}</h2>
            {% block content %}{% endblock %}
        </div>
        <footer>
            <p>Earnings Data Viewer &copy; 2025</p>
        </footer>
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
            <li><a href="{{ url_for('view_file', type=active_page, filename=file.name) }}">{{ file.display_name }}</a></li>
        {% endfor %}
        </ul>
    {% else %}
        <p>No {{ active_page }} found for {{ company_name }}. Please run the summarization script.</p>
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
        <p>Could not read file content, file is empty, or content is not valid Markdown.</p>
    {% endif %}
    <a href="{{ url_for('list_' + type) }}" class="back-link">&larr; Back to {{ type }} list</a>
{% endblock %}
"""

# Setup Jinja2 environment with DictLoader
app.jinja_loader = DictLoader({
    'base.html': HTML_BASE,
    'list_page.html': HTML_LIST_PAGE,
    'view_file_page.html': HTML_VIEW_FILE_PAGE
})

def get_files(pattern_suffix):
    """Get all summary or table files from summaries/ folder, for all companies."""
    pattern = os.path.join("summaries", pattern_suffix)
    files_found = []
    matched_files = glob.glob(os.path.join(PROJECT_ROOT, pattern))
    print(f"[DEBUG] get_files: pattern={pattern}, found {len(matched_files)} files.")
    for filepath in matched_files:
        filename = os.path.basename(filepath)
        # Extract company name from filename (before first underscore)
        company_prefix = filename.split('_')[0]
        display_name = filename.replace(".txt", "").replace("_", " ").title()
        files_found.append({"name": filename, "display_name": display_name, "company": company_prefix})
    print(f"[DEBUG] get_files: returning {len(files_found)} files for display.")
    return sorted(files_found, key=lambda x: x['display_name'], reverse=True)

@app.route('/')
def index():
    return render_template('list_page.html', title="Summaries", files=get_files("*_summary_*.txt"), active_page="summaries", company_name="All Companies")

@app.route('/summaries')
def list_summaries():
    return render_template('list_page.html', title="Summaries", files=get_files("*_summary_*.txt"), active_page="summaries", company_name="All Companies")

@app.route('/tables')
def list_tables():
    return render_template('list_page.html', title="Tables", files=get_files("*_table.txt"), active_page="tables", company_name="All Companies")

@app.route('/view/<type>/<filename>')
def view_file(type, filename):
    if ".." in filename or not filename.endswith(".txt"):
        return "Invalid filename.", 400
    filepath = os.path.join(PROJECT_ROOT, "summaries", filename)
    html_output = None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            raw_content = f.read()
            if raw_content.strip():
                html_output = markdown.markdown(raw_content, extensions=['tables', 'fenced_code', 'nl2br'])
            else:
                html_output = "<p>File is empty.</p>"
    except Exception as e:
        print(f"Error reading or parsing file {filepath}: {e}")
        html_output = f"<p>Error reading or parsing file: {e}</p>"
    title_prefix = "Summary" if type == "summaries" else "Table"
    return render_template('view_file_page.html', title=f"{title_prefix}: {filename}", filename=filename, html_content=html_output, active_page=type, type=type, company_name="All Companies")

if __name__ == '__main__':
    print(f"Serving webapp for {COMPANY_NAME}...")
    print(f"Expected summary files pattern: {COMPANY_NAME}_summary_*.txt")
    print(f"Expected table files pattern: {COMPANY_NAME}_*_table.txt")
    app.run(debug=True, host='0.0.0.0', port=5001)

