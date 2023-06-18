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
    print(len(chunk))
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an assistant trying to explain a paper (research) to a 12 year old, using easy vocabulary."},
            {"role": "user", "content": f"Summarize the following text in {choice_wordlength_final} words for {choice_topicknowledge} level."},
            {"role": "user", "content": f"YOUR DATA TO PASS IN: {chunk}."},
        ],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5
    )
    return response.choices[0]['message']['content']


def split_into_chunks(text, tokens=500):
    global choice_wordlength_final
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
    words = encoding.encode(text)
    chunks = []
    for i in range(0, len(words), tokens):
        chunks.append(' '.join(encoding.decode(words[i:i + tokens])))

    if choice_wordlength == "100-150 words":
        choice_wordlength_final = 150
    elif choice_wordlength == "200-250 words":
        choice_wordlength_final = 250
    elif choice_wordlength == "350-400 words":
        choice_wordlength_final = 400
    else:
        choice_wordlength_final = 250
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

#@app.route('/arxivinput', methods=['GET', 'POST'])
def analyze_user_input(user_text):
    global search_query
    # Make a request to OpenAI's Chat API to analyze the user's input
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an Arxiv topic recommender system based on interests of the user."},
            {"role": "user", "content": f"Based on the user input about themselves, find what are their interests, what topics they would like to read about on Arxiv and only list the field, and topics they would like to know more about. In your output message only inlcude a list like: quantum field theory, general relativity, black holes."},
            {"role": "user", "content": f"YOUR DATA TO PASS IN: {user_text}."},
        ],
        max_tokens=100,
        n=1,
        stop=None,
        temperature=0.5
    )
    
    # Extract the generated search query from the OpenAI response
    search_query = response.choices[0]['message']['content']
    print(search_query)

    return search_query

def recommend(search_query):
    # Fetch relevant papers from the arXiv API
    arxiv_url = 'http://export.arxiv.org/api/query'
    params = {
        'search_query': search_query,
        'max_results': 10
    }
    response2 = requests.get(arxiv_url, params=params)

    if response2.status_code == 200:
        # Parse the API response and extract relevant paper information
        papers = parse_arxiv_response(response2.text)
        return render_template('arxivinput.html', papers=papers)
    else:
        return 'Error occurred while fetching papers from the arXiv API.'

def parse_arxiv_response(response_text):
    # Find the start and end tags for each paper entry
    entry_start = '<entry>'
    entry_end = '</entry>'

    # Find the start and end tags for the title, authors, and abstract
    title_start = '<title>'
    title_end = '</title>'
    authors_start = '<author>'
    authors_end = '</author>'
    abstract_start = '<summary>'
    abstract_end = '</summary>'

    # Initialize the list to store paper information
    papers = []

    # Loop through the response text and extract paper information
    while True:
        # Find the start and end indices of the next paper entry
        start_index = response_text.find(entry_start)
        end_index = response_text.find(entry_end)

        # Break the loop if no more paper entries are found
        if start_index == -1 or end_index == -1:
            break

        # Extract the paper entry
        paper_entry = response_text[start_index:end_index + len(entry_end)]

        # Extract the title
        title_start_index = paper_entry.find(title_start)
        title_end_index = paper_entry.find(title_end)
        title = paper_entry[title_start_index + len(title_start):title_end_index]

        # Extract the authors
        authors_start_index = paper_entry.find(authors_start)
        authors_end_index = paper_entry.find(authors_end)
        authors = paper_entry[authors_start_index + len(authors_start):authors_end_index]

        # Extract the abstract
        abstract_start_index = paper_entry.find(abstract_start)
        abstract_end_index = paper_entry.find(abstract_end)
        abstract = paper_entry[abstract_start_index + len(abstract_start):abstract_end_index]

        # Create a dictionary with the paper information
        paper = {
            'title': title,
            'authors': authors,
            'abstract': abstract
        }

        # Append the paper dictionary to the list
        papers.append(paper)

        # Update the response text by removing the processed paper entry
        response_text = response_text[end_index + len(entry_end):]

    return papers

@app.route('/arxivinput', methods=['GET', 'POST'])
def index():
    k = ""
    if request.method == 'POST':
        user_text = request.form.get('user_text')
        analyze_user_input(user_text)
        k = recommend(search_query)
        return k
    return render_template('arxivinput.html')

if __name__ == '__main__':
    app.run(debug=True)