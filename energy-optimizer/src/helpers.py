import numpy as np

# Mapping function
# Source: https://docs.arduino.cc/language-reference/en/functions/math/map/
# "The Arduino documentation is licensed under the Creative Commons Attribution-Share Alike 4.0 license."

def map(x, in_min, in_max, out_min, out_max):
  return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min;

def remap(data, func, amount):
  data = np.asarray(data)
  timestamps = data[::amount,0]
  values = func(data[:,1].reshape(-1, amount),axis=-1)
  data = np.column_stack((timestamps, values)).tolist()
  return data
 
