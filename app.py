import os
#from PyPDF2 import PdfReader
import fitz
import re
import openai
from concurrent.futures import ThreadPoolExecutor
import tiktoken
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
import requests

UPLOAD_FOLDER = 'temp_pdfs'
ALLOWED_EXTENSIONS = {'pdf'}

openai.api_key = ''
ARXIV_API_URL = 'http://export.arxiv.org/api/query'

choice_wordlength = ""
choice_topicknowledge = "Intermediate"
search_query = ""

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

app.secret_key = '.qJYWLR#30a"lGqWtw4SAVooy@50Q'

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(filepath):
    doc = fitz.open(filepath)
    text = ''
    for page in doc:
        text += page.get_text()
    return text

def remove_text_before_keyword(text, keyword):
    index = text.lower().find(keyword.lower())
    if index != -1:
        cleaned_text = text[index + len(keyword):]
        return cleaned_text
    return text

def remove_text_after_references(text):
    references_keywords = ['references']
    reversed_text = text[::-1]  # Reverse the text
    for keyword in references_keywords:
        reversed_index = reversed_text.lower().find(keyword[::-1].lower())  # Reverse keyword search
        if reversed_index != -1:
            cleaned_text = text[:len(text) - reversed_index]
            return cleaned_text
    return text

def call_openai_api(chunk):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant trying to explain a paper (research) to a 12 year old, using easy vocabulary."},
            {"role": "user", "content": f"Summarize the following text in less than {choice_wordlength_final} words for {choice_topicknowledge} level."},
            {"role": "user", "content": f"YOUR DATA TO PASS IN: {chunk}."},
        ],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5
    )
    return response.choices[0]['message']['content']


def split_into_chunks(text, tokens=500):
    global choice_wordlength_final, chunks
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
    words = encoding.encode(text)
    chunks = []
    for i in range(0, len(words), tokens):
        chunks.append(' '.join(encoding.decode(words[i:i + tokens])))

    if choice_wordlength == "100-150 words":
        choice_wordlength_final = 100
    elif choice_wordlength == "200-250 words":
        choice_wordlength_final = 200
    elif choice_wordlength == "350-400 words":
        choice_wordlength_final = 350
    else:
        choice_wordlength_final = 200
    
    choice_wordlength_final = choice_wordlength_final / len(chunks)
    print(choice_wordlength_final)
    return chunks   

def process_chunks(input_text):
    chunks = split_into_chunks(input_text)
    
    # Processes chunks in parallel
    with ThreadPoolExecutor() as executor:
        responses = list(executor.map(call_openai_api, chunks))
    return responses


@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
            # Check if the choice_wordlength is already present in the session
        choice_wordlength = request.form.get("choice_wordlength")
        choice_topicknowledge = request.form.get("choice_topicknowledge")
        print("Choice topic knowledge: %s." % choice_topicknowledge)    
        print("Choice word length: %s." % choice_wordlength)
        # Process the choice_wordlength and choice_topicknowledge here
        # Check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['file']
        # If the user does not select a file, the browser submits an empty part without a filename
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file and allowed_file(file.filename):
            # Save the uploaded file to a temporary folder
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            #file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            file.save(filepath)
            extracted_text = extract_text_from_pdf(filepath)
            cleaned_text = remove_text_before_keyword(extracted_text, 'Abstract')
            cleaned_text = remove_text_after_references(cleaned_text)
            
            finalfinalAnswer=process_chunks(cleaned_text)
            finalfinalfinalAnswer = ""

            while finalfinalAnswer:
                item = finalfinalAnswer.pop(0)
                finalfinalfinalAnswer = finalfinalfinalAnswer + item
            #final_summary = generate_summary(final_summary, final_summary_length, topic_knowledge)

            #final_summary_length = request.form.get('final_summary_length')  # Get selected word length from the form
            #topic_knowledge = request.form.get('topic_knowledge')  # Get selected topic knowledge from the form
            #summary = generate_summary(cleaned_text, final_summary_length, topic_knowledge)

            # Perform further processing or return a response to the user
            #return redirect(url_for('uploaded_file', filename=filename))
            return render_template('index.html', summary = finalfinalfinalAnswer)
    # Render the file upload form template for GET requests
    return render_template('index.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Return a response to the user, e.g., display the uploaded file or provide a download link
    return f'Temporary file {filename} has been uploaded successfully!'

def fetch_paper_summary(topic):
    # Parameters for arXiv API search
    params = {
        'search_query': f'all:{topic}',
        'max_results': 1,
        'sortBy': 'relevance',
        'sortOrder': 'descending',
        'start': 0
    }

    # Send request to arXiv API
    response_arxiv = requests.get(ARXIV_API_URL, params=params)

    if response_arxiv.status_code == 200:
        # Extract the paper summary from the API response
        xml_data = response_arxiv.text
        title_start = xml_data.find("<title>") + len("<title>")
        title_end = xml_data.find("</title>", title_start)
        title = xml_data[title_start:title_end].strip()

        author_start = xml_data.find("<author>")
        author_end = xml_data.find("</author>", author_start)
        author_start_name = xml_data.find("<name>", author_start) + len("<name>")
        author_end_name = xml_data.find("</name>", author_start_name)
        author = xml_data[author_start_name:author_end_name].strip()

        link_start = xml_data.find("<link title=\"pdf\" href=\"") + len("<link title=\"pdf\" href=\"")
        link_end = xml_data.find("\"", link_start)
        link = xml_data[link_start:link_end].strip()

        summary_start = xml_data.find("<summary>") + len("<summary>")
        summary_end = xml_data.find("</summary>", summary_start)
        summary_arxiv = xml_data[summary_start:summary_end].strip()

        return f'<strong>Title:</strong> {title}<br>' \
               f'<strong>Authors:</strong> {author}<br>' \
               f'<strong>Link:</strong> <a href="{link}">{link}</a><br>' \
               f'<strong>Summary:</strong><br>{summary_arxiv}'

    return None

@app.route('/arxivinput', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        topic = request.form['topic']

        # Fetch paper summary using the arXiv API
        summary = fetch_paper_summary(topic)

        if summary:
            return f'Summary of a paper on "{topic}":<br>{summary}'
        else:
            return 'No paper found for the given topic.'

    return '''
        <form method="POST">
            <label for="topic">Enter a topic:</label><br>
            <input type="text" id="topic" name="topic" required><br><br>
            <input type="submit" value="Submit">
        </form>
    '''

if __name__ == '__main__':
    app.run(debug=True)