import os
import requests

# Token can be used to load data from HA
TOKEN = os.getenv("SUPERVISOR_TOKEN", "")

# Headers required to load data from HA
headers = {
  "Authorization": "Bearer " + TOKEN,
  "Content-Type": "application/json"
}

BASE_URL = "http://supervisor/core/api/states/"


def pushState(entityID, obj):
    try:
        requests.post(BASE_URL + entityID, json=obj, headers=headers)
    except:
        pass
        
def getData(id, default = None):
    try:
        data = requests.get(BASE_URL + id, headers=headers)
        return data.json()["state"]
    except:
        return default

def getFloat(id, default=None):
    try:
        return float(getData(id, default))
    except:
        return default
