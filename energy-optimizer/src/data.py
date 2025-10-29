import datetime
import os
import requests
import numpy as np
from bisect import bisect_left

def generateSteps(data):
    # Steps are basically timestamps for which the simulation will be run
    step = int(data[-1][0] - data[-2][0])
    steps = np.arange(data[0][0],data[-1][0]+step+1,step, dtype=int)
    timestamp = int(datetime.datetime.now().timestamp())
    idx = max(bisect_left(steps, timestamp)-1,0)
    steps = steps[idx:]
    steps[0] = timestamp
    return steps

class SHF:
  def fetchPrices(region= "FI", resolution=15, staticFees=0):
    url = "https://api.spot-hinta.fi/TodayAndDayForward"
    params = {
      "region": region,
      "priceResolution": resolution
    }
    data = requests.get(url, params=params).json()
    for idx, x in enumerate(data):
        timestamp = int(datetime.datetime.fromisoformat(x["DateTime"]).timestamp())
        staticFees = staticFees(timestamp) if callable(staticFees) else staticFees
        value = x["PriceWithTax"] + staticFees
        data[idx] = (timestamp, value)
    return data

class Elering:
  def fetchPrices(region="fi", staticFees=0):
    start = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = start + datetime.timedelta(days=2)

    url = f"https://dashboard.elering.ee/api/nps/price?start={start.isoformat()}&end={end.isoformat()}".replace("+00:00", "Z")
    data = requests.get(url).json()["data"][region]
    for idx, x in enumerate(data):
        timestamp = x["timestamp"]
        staticFees = staticFees(timestamp) if callable(staticFees) else staticFees
        value = x["price"]/1000*1.255 + staticFees
        data[idx] = (timestamp, value)
    return data

class OpenMeteo:
  def fetchData(lat, lon):
      start = datetime.datetime.now(datetime.timezone.utc).replace(minute=0, second=0, microsecond=0)
      end = start + datetime.timedelta(days=2)
      url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&hourly=temperature_2m,shortwave_radiation&timeformat=unixtime&forecast_hours=48&start={start}"
      weather = requests.get(url).json()["hourly"]
      conditions = [dict(zip(weather,t)) for t in zip(*weather.values())]
      conditions = [(x["time"], x) for x in conditions]
      return conditions
