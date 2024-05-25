#!/usr/bin/python3
import requests
from urllib import request, parse
import re
import argparse
from datetime import datetime, timedelta
#from bs4 import BeautifulSoup
from collections import OrderedDict
import json
import time
#import matplotlib.pyplot as plt
#import matplotlib.image as mpimg
import itertools
from PIL import Image
from io import BytesIO

# Constants
OCR_API_KEY = 'K83337641288957' # Replace with your actual OCR API key
OCR_API_URL = 'https://api.ocr.space/parse/image'

classes = ["SL", "1A", "2A", "3A", "CC", "FC", "2S"]

parser = argparse.ArgumentParser(description='Train seat crawler')
parser.add_argument('--src', help='Source station code', required=True)
parser.add_argument('--dest', help='Destination station code', required=True)
parser.add_argument('--class', help='Class code', required=True, dest="class1")
parser.add_argument('--date', type=lambda d: datetime.strptime(d, '%d-%m-%Y'), required=True)
parser.add_argument('--filter', nargs='+', help='List of trains to consider', required=False)
parser.add_argument('--reverse', help='Reverse the order of train', required=False, action='store_true')
parser.add_argument('--train', help='Train number', required=False)

args = parser.parse_args()

def get_cookies(headers):
    headers = str(headers).split("\n")
    cookies = ""
    for item in headers:
        if item.startswith("Set-Cookie"):
            cookies += item.split(" ")[1]
    return cookies

def show_captcha():
    global cookies, answer
    ts = int(time.time() * 1000)
    req = request.Request("http://www.indianrail.gov.in/enquiry/captchaDraw.png?" + str(ts))
    res = request.urlopen(req)
    data = res.read()
    cookies = get_cookies(res.headers)
    img = Image.open(BytesIO(data))  # Open the image directly from bytes

    # Call the OCR API
    result = ocr_space_file(img)
    text = result['ParsedResults'][0]['ParsedText']
    obj = re.search(r'^(\s*\d+\s*[-+]\s*\d+\s*)=.*$', text)
    if obj:
        eq = obj.group(1)
        answer = eval(eq)
        print(eq, ' ', answer)
    else:
        plt.imshow(img)  # Display the image object directly
        plt.show()
        answer = input()

def ocr_space_file(image):
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_str = buffered.getvalue()
    
    response = requests.post(
        OCR_API_URL,
        files={"file": ("captcha.png", img_str, "image/png")},
        data={"apikey": OCR_API_KEY, "language": "eng"}
    )
    return response.json()

req = request.Request("http://www.indianrail.gov.in/enquiry/FetchAutoComplete")
res = request.urlopen(req)
stations = json.loads(res.read().decode('ascii'))

for item in stations:
    if item.endswith(" " + args.src):
        args.src_long = item
    if item.endswith(" " + args.dest):
        args.dest_long = item

show_captcha()

def get_train_list():
    global cookies, answer
    ts = int(time.time() * 1000)
    headers = {
        "Cookie": cookies
    }
    data = {
        "inputCaptcha": answer,
        "dt": args.date.strftime("%d-%m-%Y"),
        "sourceStation": args.src_long,
        "destinationStation": args.dest_long,
        "flexiWithDate": "n",
        "inputPage": "TBIS",
        "language": "en",
        "_": ts
    }
    data = parse.urlencode(data).encode()
    req = request.Request("http://www.indianrail.gov.in/enquiry/CommonCaptcha?" + data.decode('ascii'), headers=headers)
    res = request.urlopen(req)
    trains = json.loads(res.read().decode('ascii'))
    nums = []
    for item in trains['trainBtwnStnsList']:
        if item['fromStnCode'] == args.src and item['toStnCode'] == args.dest:
            nums.append([item['trainNumber'], item['trainType'], item['trainName'], item['departureTime'], item['duration'], item['arrivalTime']])
    return nums

def get_route(num):
    global cookies, answer
    ts = int(time.time() * 1000)
    headers = {
        "Cookie": cookies
    }
    data = {
        "inputCaptcha": answer,
        "inputPage": "TBIS_SCHEDULE_CALL",
        "trainNo": num,
        "journeyDate": args.date.strftime("%d-%m-%Y"),
        "sourceStation": args.src_long,
        "language": "en",
        "_": ts
    }
    data = parse.urlencode(data).encode()
    req = request.Request("http://www.indianrail.gov.in/enquiry/CommonCaptcha?" + data.decode('ascii'), headers=headers)
    res = request.urlopen(req)
    route = json.loads(res.read().decode('ascii'))
    stations = []
    for item in route['stationList']:
        stations.append([item['stationCode'], item['dayCount']])
    day = 1
    for item in stations:
        if item[0] == args.src:
            day = int(item[1])
    for item in stations:
        item[1] = int(item[1]) - day
    return stations

def get_availability(num, src, dest, date):
    global cookies, answer
    ts = int(time.time() * 1000)
    headers = {
        "Cookie": cookies
    }
    data = {
        "inputCaptcha": answer,
        "inputPage": "TBIS_CALL_FOR_FARE",
        "trainNo": num[0],
        "dt": date.strftime("%d-%m-%Y"),
        "sourceStation": src,
        "destinationStation": dest,
        "classc": args.class1,
        "quota": "GN",
        "traintype": num[1][0],
        "language": "en",
        "_": ts
    }
    data = parse.urlencode(data).encode()
    req = request.Request("http://www.indianrail.gov.in/enquiry/CommonCaptcha?" + data.decode('ascii'), headers=headers)
    res = request.urlopen(req)
    d = res.read()
    avail = json.loads(d.decode('utf8'))
    try:
        return avail['avlDayList'][0]['availablityStatus'], avail['totalCollectibleAmount']
    except:
        return "Error"

numbers = sorted(get_train_list(), key=lambda x: x[3])
if args.reverse:
    numbers.reverse()

for number in numbers:
    if args.train and number[0] != args.train:
        continue
    if number[0] == "13008" or number[0] == "13007" or number[0] == "19023" or number[0] == "12925":
        continue
    print("\nTrain Number: " + str(number[0]) + "\nTrain Name: " + str(number[2]) + "\nDeparture Time: " + str(number[3]) + "\nArrival Time: " + str(number[5]))
    route = get_route(number[0])
    i = 0
    src_idx = -1
    dest_idx = -1
    while i < len(route):
        if route[i][0] == args.src:
            src_idx = i
        if route[i][0] == args.dest:
            dest_idx = i
        i += 1
    if src_idx == -1 or dest_idx == -1:
        print("Source or dest not found")
        continue
    avail = get_availability(number, route[src_idx][0], route[dest_idx][0], args.date + timedelta(days=route[src_idx][1]))
    print("Availability: " + str(avail))
    if args.train and number[0] == args.train:
        break
