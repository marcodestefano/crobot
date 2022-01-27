import json
import traceback
import hmac
import hashlib
import time
import requests
import urllib
from decimal import Decimal

BASE_URI = "https://api.crypto.com/v2/"
SETTINGS_FILE = "settings.json"
API_KEY = "APIKey"
API_SECRET = "APISecret"

def create_pair(crypto, base):
    return crypto + "_" + base

def amount_format(value):
    return '{0:f}'.format(Decimal(str(value)))

def getRatio(currentValue, minValue, maxValue):
    return Decimal(1 - ((Decimal(currentValue)-Decimal(minValue))/(Decimal(maxValue)-Decimal(minValue))))

def get_json_data(filename):
    with open(filename) as keys:
        content = json.load(keys)
    return content

def params_to_str(obj, level):
    MAX_LEVEL = 3
    if level >= MAX_LEVEL:
        return str(obj)

    return_str = ""
    for key in sorted(obj):
        return_str += key
        if isinstance(obj[key], list):
            for subObj in obj[key]:
                return_str += params_to_str(subObj, ++level)
        else:
            return_str += str(obj[key])
    return return_str

def query(method, params={}):
    credentials = get_json_data(SETTINGS_FILE)
    apikey = credentials[API_KEY]
    apisecret = credentials[API_SECRET]
    req = {
        "id" : 1,
        "method": method,
        "api_key": apikey,
        "params" : params,
        "nonce": int(time.time() * 1000)
    }
    
    param_str = "" 
    if "params" in req:
        param_str = params_to_str(req['params'], 0)
    payload_str = req['method'] + str(req['id']) + req['api_key'] + param_str + str(req['nonce'])
    
    req['sig'] = hmac.new(
        bytes(str(apisecret), 'utf-8'),
        msg=bytes(payload_str, 'utf-8'),
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return requests.post(BASE_URI + method, json=req, headers={'Content-Type':'application/json'})

def publicquery(method, params={}):
    paramsList = urllib.parse.urlencode(params)
    return requests.get(BASE_URI + method + "?" + paramsList)
