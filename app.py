import os
#from PyPDF2 import PdfReader
import fitz
import re
import openai
from concurrent.futures import ThreadPoolExecutor
import tiktoken
from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = 'temp_pdfs'
ALLOWED_EXTENSIONS = {'pdf'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

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

#def generate_summary(text, final_summary_length, topic_knowledge):
    #final_summary_length = "100-150"
    #topic_knowledge = "begineer level"
#    prompt = f"Summarize the following text in {final_summary_length} words for {topic_knowledge}:\n{text}"
 #   response = openai.Completion.create(
#        engine='davinci',
#        prompt=prompt,
#        max_tokens=final_summary_length,
#        temperature=0.6,
#        n=1,
#        stop=None
#    )
#    summary = response.choices[0].text.strip()
#    return summary



def call_openai_api(chunk):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Summarize the following text in 200 words for beginner level with no prior understanding of the field. Try to use very easy terms or at least explain them."},
            {"role": "user", "content": f"YOUR DATA TO PASS IN: {chunk}."},
        ],
        max_tokens=500,
        n=1,
        stop=None,
        temperature=0.5
    )
    return response.choices[0]['message']['content'].strip()


def split_into_chunks(text, tokens=500):
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo')
    words = encoding.encode(text)
    chunks = []
    for i in range(0, len(words), tokens):
        chunks.append(' '.join(encoding.decode(words[i:i + tokens])))
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
            return render_template('result.html', text=cleaned_text, summary = finalfinalfinalAnswer)
    # Render the file upload form template for GET requests
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    # Return a response to the user, e.g., display the uploaded file or provide a download link
    return f'Temporary file {filename} has been uploaded successfully!'

if __name__ == '__main__':
    app.run(debug=True)
