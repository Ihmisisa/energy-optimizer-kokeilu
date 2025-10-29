### Imports
import datetime
import requests
from helpers import *
from model import *
from data import *
from homeassistant import *

### Location -> set in Addon settings
### Defaults here for running outside HA Addon
lat = os.environ.get('LAT', 60.17)
lon = os.environ.get('LON', 24.94)

### Data loads
conditions = OpenMeteo.fetchData(lat, lon)
el_prices = SHF.fetchPrices(region = "FI", resolution=15, staticFees=0.05)

### If you load data on 15min resolution, you can remap to hourly
### resolution but use maximum 15min price as the hourly price
el_prices = remap(el_prices, np.max, 4) # Max price of 4 timesteps
# el_prices = remap(el_prices, np.min, 4) # Min price of 4 timesteps
# el_prices = remap(el_prices, np.mean, 4) # Mean price of 4 timesteps (15min->1h)

### Power sources
electricity = Fuel("Electricity", el_prices)
wood = Fuel("Wood", 0.08)

### Steps are basically timestamps for which the simulation will be run
steps = generateSteps(el_prices)

### This is the main Model that makes the calculations
m = Model(conditions, steps=steps)

### Get initial temps from Home Assistant (with default)
T0 = getFloat("sensor.average_temperature_inside", 20.5)

### Some heaters have variable power based on weather or some other condition
heatpump_cop = lambda time, cond: min(6, map(cond["temperature_2m"], -22, 6, 2, 5.1))
heatpump_power = lambda cond: min(6.3, map(cond["temperature_2m"], -25, -15, 3.2, 4.8))
sun_power = lambda cond: cond["shortwave_radiation"]/1000

### Outside temperature is determined by a lambda function from weather data
out = m.addCapacitance("Out", tempFunc=lambda time,cond: cond["temperature_2m"])

### Rooms/spaces. Name, heat capacity (kWh/C), HARD temp limits , starting temp
house = m.addCapacitance("House", 12, templimit=(20.5,22), startTemp=T0)
boiler = m.addCapacitance("Boiler", 10, templimit=(50,80), startTemp=50)

### Heat sources
### Note: COP can also be a static number instead of a function
### Name, power (integer or function), energy source, cop=(integer or function)
heater = m.addHeatSource("ImmersionHeater", 7, electricity)
heatpump = m.addHeatSource("HeatPump", heatpump_power, electricity, cop=heatpump_cop)
fireplace = m.addHeatSource("Fireplace", 2, wood)
sun = m.addHeatSource("Sun", sun_power) # Sun is one heat source
other = m.addHeatSource("Other", 0.2) # Non-controllable heat sources

### Connections between rooms
m.createConnection(house, out, factor=0.2) # House heat loss 0.1kW/deltaC
m.createConnection(house, boiler, name="B2H", controllable=True)
# Boiler loses some energy slowly
m.createConnection(house, boiler, name="B2H", factor=0.01)

### Connections between rooms and heaters
m.createConnection(boiler, heater)
m.createConnection(house, heatpump)
m.createConnection(boiler, fireplace)
m.createConnection(house, sun, factor=2) # Factor takes area of the house into account
m.createConnection(house, other)

### Some heaters are connected to multiple "areas"
### Here is an example on how to divide power between areas
### When on, 25% of the power goes to garage and 75% to the house
#m.createConnection(house, heater2, factor=0.75)
#m.createConnection(garage, heater2, factor=0.25)

### Advanced limits

# Forces certain heater to be at >= 90% power level before using other one
#m.addLimit(lambda model, input: (input[:,1] - 0.9)*(input[:,2]-0.01).clip(min=0))

# This penalizes temperature below 19.5 but allows them if it "saves money"
#m.addPenalty(lambda model, input: (19.5 - house.getTemps()).clip(min=0).sum())

# Penalizes power increases of the heatpump. Can be used to "calm the cost-optimization".
#def diffLimit(obj):
#    return np.diff(np.asarray(obj.data)[:,2], axis=0).clip(min=0).sum()*0.01
#m.addPenalty(lambda model, input: diffLimit(heatpump))

# Do the actual optimization and output results
from output import *
optimizeAndOutput(m)
