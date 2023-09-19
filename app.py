from flask import Flask, render_template, request
import requests
import difflib
from difflib import Differ
from bs4 import BeautifulSoup
import mysql.connector
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from apscheduler.schedulers.background import BackgroundScheduler
from pytz import timezone
import datetime


app = Flask(__name__)
scheduler = BackgroundScheduler()
# Create a database connection
db_connection = mysql.connector.connect(
    host='localhost',
    user='root',
    password='',
    database='flask_check'
)
def fetch_webpage(url):
    driver = None  # Initialize the driver outside the try block
    try:
        options = Options()
        options.headless = True  # Run in headless mode (without opening a browser window)
        driver = webdriver.Chrome(options=options)
        driver.get(url)
        time.sleep(5)
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Find the <body> element and get its text content
        body = soup.find('body')
        if body:
            text = body.get_text()
        else:
            text = ""

        cleaned_text = " ".join(text.split())

        return cleaned_text
    except Exception as e:
        # Handle any exceptions or errors here
        print("Error fetching webpage:", str(e))
        return ""
    finally:
        if driver:
            driver.quit()  # Close the WebDriver when done (if it was created)

def fetch_existing_content_from_db(record_id):
    cursor = db_connection.cursor()
    cursor.execute("SELECT content FROM checker WHERE id = %s", (record_id,))
    existing_content = cursor.fetchone()[0]
    cursor.close()
    return existing_content
def send_email(subject, body, to_email):
    api_key = "FBEABD80B6C9592D2EFAC6C57E848BAA512BBBAEC01F78E81EF4A45D318C6EEF9EBB73CE62E92C694C9972B737B5D84C"
    sender_email = "sitecheck@lateralhub.com"  # Replace with a valid sender email domain

    api_url = "https://api.elasticemail.com/v2/email/send"

    data = {
        "apikey": api_key,
        "from": sender_email,
        "to": to_email,
        "subject": subject,
        "bodyText": body,
    }

    try:
        response = requests.post(api_url, data=data)
        response_data = response.json()

        if response.status_code == 200 and response_data.get("success", False):
            return True
        else:
            error_message = response_data.get("error", "Unknown error")
            print("Failed to send email:", error_message)
            return False
    except Exception as e:
        print("Error sending email:", str(e))
        return False
def generate_diff(existing_content, new_content):
    if existing_content == new_content:
        return "Not changed"
    d = difflib.Differ()
    diff = list(d.compare(existing_content.splitlines(), new_content.splitlines()))
    diff_output = '\n'.join(diff)
    return diff_output
def generate_email_content(existing_content, new_content):
    differ = Differ()
    differences = []
    existing_sentences = existing_content.split(". ")
    new_sentences = new_content.split(". ")
    max_sentences = min(len(existing_sentences), len(new_sentences))
    added_sentences = []
    deleted_sentences = []
    for i in range(max_sentences):
        diff = list(differ.compare(existing_sentences[i].split(), new_sentences[i].split()))
        added_words = []
        deleted_words = []
        for line in diff:
            if line.startswith('- '):
                deleted_words.append(line[2:])
            elif line.startswith('+ '):
                added_words.append(line[2:])
        sentence_diff = ""
        if added_words:
            sentence_diff += "+ " + " ".join(added_words)
        if deleted_words:
            sentence_diff += "\n- " + " ".join(deleted_words)

        if sentence_diff:
            differences.append(f"{sentence_diff}\n")
        else:
            pass
    if len(new_sentences) > max_sentences:
        added_sentences = new_sentences[max_sentences:]
        differences.append("Additional Data in New Content:\n")
        for i, sentence in enumerate(added_sentences):
            differences.append(f"+ {sentence}\n")
    if len(existing_sentences) > max_sentences:
        deleted_sentences = existing_sentences[max_sentences:]
        differences.append("Deleted Data from Existing Content:\n")
        for i, sentence in enumerate(deleted_sentences):
            differences.append(f"- {sentence}\n")
    if not differences:
        differences.append("No Changes in Content")
    return '\n'.join(differences)

def update_records():
    cursor = db_connection.cursor()
    cursor.execute("SELECT id, url, content FROM checker")
    records = cursor.fetchall()
    email_content = ""
    for record in records:
        record_id, url, existing_content = record
        changes = "Not changed"
        if url != "":
            new_content = fetch_webpage(url)
            changes = generate_diff(existing_content, new_content)
        if changes != "Not changed":
            changes_for_email_content = generate_email_content(existing_content, new_content)
            email_content += f"Content changes detected for URL {url} (ID: {record_id}):\n\n{changes_for_email_content}\n\n"
            email_content += "_" * 170 + "\n\n"
            cursor.execute("UPDATE checker SET content = %s WHERE id = %s", (new_content, record_id))
            db_connection.commit()
    if email_content != "":
        to_email = "albert@lateralhub.com"
        to_email2 = "brad@lateralhub.com"
        to_email3 = "katie@lateralhub.com"
        to_email4 = "saimulxlr@gmail.com"
        to_email5 = "comsixsem@gmail.com"
        subject = "Content Check Results"
        body = email_content
        send_email(subject, body, to_email)
        send_email(subject, body, to_email2)
        send_email(subject, body, to_email3)
        send_email(subject, body, to_email4)
        send_email(subject, body, to_email5)
    cursor.close()
@app.route('/', methods=['GET', 'POST'])
def index():
    cursor = db_connection.cursor()
    cursor.execute("SELECT COUNT(*) FROM checker")
    count = cursor.fetchone()[0]
    if count < 50:
        for _ in range(50 - count):
            cursor.execute("INSERT INTO checker (url, content) VALUES (%s, %s)", ("", ""))
        db_connection.commit()
    urls = []
    cursor.execute("SELECT url FROM checker LIMIT 50")
    urls_from_db = cursor.fetchall()
    email_content = ""
    for url_row in urls_from_db:
        urls.append(url_row[0])
    cursor.close()
    if request.method == 'POST':
        urls = [request.form[f'url_{i}'] for i in range(1, 51)]
        cursor = db_connection.cursor()
        for i in range(50):
            changes = "Not changed"
            cursor.execute("UPDATE checker SET url = %s WHERE id = %s", (urls[i], i + 1))
            db_connection.commit()
            if urls[i] != "":
                existing_content = fetch_existing_content_from_db(i + 1)
                new_content = fetch_webpage(urls[i])
                print(existing_content)
                print(urls[i])
                print(new_content)
                changes = generate_diff(existing_content, new_content)
            if changes != "Not changed":
                changes_for_email_content = generate_email_content(existing_content, new_content)
                email_content += f"Content changes detected for URL {urls[i]} (ID: {i + 1}):\n\n{changes_for_email_content}\n\n"
                email_content += "_" * 170 + "\n\n"
                cursor.execute("UPDATE checker SET url = %s, content = %s WHERE id = %s", (urls[i], new_content, i + 1))
                db_connection.commit()
        if email_content != "":
            to_email = "albert@lateralhub.com"
            to_email2 = "brad@lateralhub.com"
            to_email3 = "katie@lateralhub.com"
            to_email4 = "saimulxlr@gmail.com"
            to_email5 = "comsixsem@gmail.com"
            subject = "Content Check Results"
            body = email_content
            send_email(subject, body, to_email)
            send_email(subject, body, to_email2)
            send_email(subject, body, to_email3)
            send_email(subject, body, to_email4)
            send_email(subject, body, to_email5)
        cursor.close()
    return render_template('index.html', urls=urls)
new_york_timezone = timezone('America/New_York')
send_time = new_york_timezone.localize(datetime.datetime.now().replace(hour=6, minute=15, second=0))
send_time1 = new_york_timezone.localize(datetime.datetime.now().replace(hour=6, minute=20, second=0))
scheduler.add_job(update_records, 'date', run_date=send_time)
scheduler.add_job(update_records, 'date', run_date=send_time1)
scheduler.start()
if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0')