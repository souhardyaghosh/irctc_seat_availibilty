import time
import requests
from flask import Flask, jsonify, request
from PIL import Image
from io import BytesIO
import re
from datetime import datetime

app = Flask(__name__)

def handle_captcha(ocr_api_url, ocr_api_key):
    ts = int(time.time() * 1000)
    url = f"http://www.indianrail.gov.in/enquiry/captchaDraw.png?" + str(ts)
    response = requests.get(url)

    if response.status_code == 200:
        captcha_image = response.content
    else:
        return None

    files = {'file': ('captcha.png', BytesIO(captcha_image), 'image/png')}
    data = {'apikey': ocr_api_key, 'language': 'eng'}
    ocr_response = requests.post(ocr_api_url, files=files, data=data)

    if ocr_response.status_code == 200:
        ocr_result = ocr_response.json()
        try:
            captcha_text = ocr_result['ParsedResults'][0]['ParsedText']
            match = re.search(r'^(\s*\d+\s*[-+]\s*\d+\s*)=.*$', captcha_text)
            if match:
                return eval(match.group(1))
            else:
                return None
        except (KeyError, IndexError):
            return None
    else:
        return None

@app.route('/trains')
def get_trains():
    source = request.args.get('source')
    destination = request.args.get('destination')
    date_str = request.args.get('date')
    train_class = request.args.get('class')

    try:
        date_obj = datetime.strptime(date_str, "%d-%m-%Y")
        date_formatted = date_obj.strftime("%d-%m-%Y")
    except ValueError:
        return jsonify({'error': 'Invalid date format. Please use DD-MM-YYYY.'}), 400

    ocr_api_url = 'https://api.ocr.space/parse/image'
    ocr_api_key = 'K83337641288957'

    captcha_answer = handle_captcha(ocr_api_url, ocr_api_key)
    if captcha_answer is None:
        return jsonify({'error': 'Failed to solve CAPTCHA'}), 400

    data = {
        'inputCaptcha': captcha_answer,
        'dt': date_formatted,
        'sourceStation': source,
        'destinationStation': destination,
        'flexiWithDate': "n",
        'inputPage': "TBIS",
        'language': "en",
        'classc': train_class
    }
    # part added
    if response.status_code != 200:
        return jsonify({'error': 'Failed to fetch train data'}), 500

    try:
        train_data = response.json()
        train_names = [train['trainName'] for train in train_data.get('trainBtwnStnsList', [])]
        return jsonify({'train_names': train_names})
    except ValueError as e:
        return jsonify({'error': 'Failed to parse train data'}), 500
#till here
if __name__ == '__main__':
    app.run(debug=True)
