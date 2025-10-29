#!/usr/bin/with-contenv bashio

# Change work folder
cd /src

# Latitude and longitude to ENV variables for the Python
export LAT="$(bashio::config 'lat')"
export LON="$(bashio::config 'lon')"

# Create config folder if it doesn't exist yet
mkdir -p /homeassistant/energy-optimizer/src

# Create output folder if it doesn't exist yet
mkdir -p /homeassistant/energy-optimizer/output

# Copy main.py to Home Assistant folder so that it can be customized
echo "Copying main.py to homeassistant config folder."
cp -n main.py /homeassistant/energy-optimizer/src/

echo 'Copying optimizer v2 from Home Assistant config folder.'
cp /homeassistant/energy-optimizer/src/* .

# Run main logic
echo "Starting optimization..."
python3 main.py

cp /data/*.json /homeassistant/energy-optimizer/output/
cp /data/*.yaml /homeassistant/energy-optimizer/sensors/
