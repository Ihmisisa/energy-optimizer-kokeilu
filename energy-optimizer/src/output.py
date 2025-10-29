import datetime
import json
from string import Template
import numpy as np
from homeassistant import *

SENSOR_PREFIX = "sensor.energy_opt_"

def writeData(data):
    for key, value in data.items():
        obj = {"state": int(datetime.datetime.now().timestamp()), "attributes": {}}
        obj["attributes"]["data"] = value
        pushState(SENSOR_PREFIX + key, obj)
        with open("../data/" + key + ".json", "w") as outfile:
            outfile.write(json.dumps(obj))

def createSensors(keys):
        with open("./template.txt") as input:
            template = Template(input.read())
            with open("../data/sensors.yaml", "w") as output:
                output.write("command_line:")
                for key in keys:
                    output.write(template.substitute({"sensor": key}))

def optimizeAndOutput(m):
    # Actual optimization
    from scipy.optimize import minimize
    result = minimize(m.model, np.array(m.getInputArray()).flatten(), constraints=m.getLimits(), bounds=m.getBounds(), options={'disp': True, "maxiter": 1000, "ftol": 1e-4})
    
    # Calculate values based on optimized result.x
    m.model(result.x)
    temps = m.getTemps()
    
    # Print data to be shown in console/log
    output = np.array(result.x).reshape(-1, len(m.controls))
    steps = m.getSteps()
    print("Time", " ".join([c.name for c in m.controls]), " ".join([c.name for c in m.nodes]))
    for idx, row in enumerate(output):
        print(datetime.datetime.fromtimestamp(steps[idx]).strftime('%m-%d %H:%M'), row.round(2), [temps[x][idx] for x in temps])
    
    # Write data to json files for optional further processing
    # Also send data directly to Home Assistant Over API
    keys = []
    data = {}
    for node in m.controls:
        data[node.name] = node.getData()
        keys.append(node.name)
    writeData(data)
    
    data = {}
    for node in m.nodes:
        data[node.name] = node.getData()
        keys.append(node.name)
    writeData(data)

    # Create yaml for sensors 
    createSensors(keys)

    # Add some visualization code here?
    return output

