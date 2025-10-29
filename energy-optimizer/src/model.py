from bisect import bisect,bisect_left
import numpy as np

class Base():
    def searchBefore(self, search, data, keys = None): # data = tuples
        if keys is None:
            keys = [x[0] for x in data]         
        idx = bisect_left(keys, search) -1
        return data[idx][1] if isinstance(data[idx], list) or isinstance(data[idx], tuple) else data[idx]

class BaseNode(Base):
    def __init__(self, name, controllable = False):
        self.name = name
        self.data = []
        self.connections = []
        self.controllable = controllable
        
    def isControllable(self):
        return self.controllable
        
    def getData(self):
        return np.asarray(self.data).round(2).tolist()
        
    def setLimit(self, limit):
        self.limit = limit
        
    def getChange(self):
        raise NotImplementedError("Subclass has not implemented getChange")
        
    def simulate(self, *args):
        pass
        
    def reset(self):
        pass
    
    def getBounds(self):
        return (0, 1)
        

class Model(Base):
    def __init__(self, conditions, steps):
        self.nodes = []
        self.controls = []
        self.fuels = []
        self.conditions = conditions
        self.steps = steps
        self.limits = []
        self.penalties = []
        
    def __repr__(self):
        l = []
        for node in self.nodes:
            l.append(node.name)
            for connection in node.connections:
                l.append(connection.name)
        return  "".join(set(l))
        
    def addCapacitance(self, *args, **kwargs):
        if "startTemp" in kwargs:
            kwargs["startTemp"] = [self.steps[0], kwargs["startTemp"],0]
        capacitance = Capacitance(*args, **kwargs)
        self.nodes.append(capacitance)
        return capacitance

    def addHeatSource(self, *args, **kwargs):
        heater = Heater(*args, **kwargs)
        if heater.energysource:
            if heater.energysource not in self.fuels:
                self.fuels.append(heater.energysource)
            if heater.isControllable():
                self.controls.append(heater)
        return heater

    def getConnections(self):
        return self.connections

    def getSteps(self):
        return self.steps
        
    def createConnection(self, a, b, name = "", factor = 1, controllable = False, **kwargs):
        factor = Common(name, factor, controllable)
        if isinstance(a, Heater):
            b._connect(name, a, factor, **kwargs)
        elif isinstance(b, Heater):
            a._connect(name, b, factor, **kwargs)
        else:
            a._connect(name, b, factor, **kwargs)
            b._connect(name, a, factor, **kwargs)
        if factor.isControllable():
            self.controls.append(factor)
    
    def getBounds(self):
        heaters = len(self.controls)
        return [(0,1)]*(len(self.steps)-1)*heaters
        
    def getInputArray(self):
        controls = len(self.controls)
        return [0]*(len(self.steps)-1)*controls
        
    def getTotalCost(self):
        cost = 0
        for fuel in self.fuels:
            cost += fuel.getCost()
        return cost
        
    def getTemps(self):
        temps = {}
        for node in self.nodes:
            if len(node.connections) > 0:
                temps[node.name] = node.getTemps().round(2).tolist()
        return temps
        
    def getLimits(self):
        return [{'type': 'ineq', 'fun': self.checkTemps }, {'type': 'ineq', 'fun': self.check }]
        
    def addLimit(self, func):
        self.limits.append(func)
    
    def check(self, input):
        output = []
        input = np.array(input).reshape(-1, len(self.controls))
        for limit in self.limits:
            output += np.asarray(limit(self, input)).tolist()
        return output

    def checkTemps(self, input):
        self.model(input)
        output = []
        for node in self.nodes:
            if node.templimit:
                if node.templimit[0]:
                    output = np.append(output, node.getTemps()[2:] - node.templimit[0])
                if node.templimit[1]:
                    output = np.append(output, node.templimit[1] - node.getTemps()[2:])
        return output
        
    def addPenalty(self, func):
        self.penalties.append(func)
        
    def getPenaltyCosts(self, input):
        cost = 0
        for penalty in self.penalties:
            cost += penalty(self, input) # Pass Model + Input array as variables
        return cost
        
    def model(self, input):
        for node in self.nodes + self.controls:
          node.reset()
        input = np.array(input).reshape(-1, len(self.controls))

        for i, timestamp in enumerate(self.steps[1:]):
            duration = (timestamp - self.steps[i])/3600
            condition = self.searchBefore(timestamp, self.conditions)
            input_row = input[i]
            for idx, heater in enumerate(self.controls):
                heater.setLevel(input_row[idx])
            for node in self.nodes + self.controls:
                node.simulate(timestamp, condition, duration)
        cost = self.getTotalCost()
        cost += self.getPenaltyCosts(input) # TODO: Convert some of the hard limits to penalties?
        return cost
        
class Capacitance(BaseNode):
    def __init__(self, name, capacity = 500000000000, templimit = None,  startTemp=None, tempFunc = None):
        self.name = name
        self.capacity = capacity
        self.templimit = templimit
        self.connections = []
        self.tempFunc = tempFunc
        self.startTemp = startTemp
        self.reset()
        super(Capacitance, self).__init__(name)
        
    def reset(self):
        self.data = [self.startTemp] if self.startTemp else []
        
    def getTemp(self, timestamp, condition = None):
        if(callable(self.tempFunc)):
            return self.tempFunc(timestamp, condition)
        return self.searchBefore(timestamp, self.data)
        
    def getTemps(self):
        if self.data:
          return np.asarray([row[1] for row in self.data])
        return None
    
    def _connect(self, name, source, factor, **kwargs):
        connection = Connection(name, self, source, factor, **kwargs)
        self.connections.append(connection)
        return connection
        
    def simulate(self, timestamp, condition, rec_duration):
        dT = 0
        energyLoss = 0
        for connection in self.connections:
            energy = connection.getChange(timestamp, condition, rec_duration)
            energyLoss += -energy if energy < 0 else 0
            dT += energy/self.capacity
        temp = self.getTemp(timestamp, condition) + dT
        energyLoss = round(energyLoss, 2)
        if self.data:
            self.data[-1][2] = energyLoss
        self.data.append([timestamp, temp, energyLoss])
        
class Common(BaseNode):
    def __init__(self, name, value, controllable = False):
        self.value = value
        super(Common, self).__init__(name, controllable)
        
    def setLevel(self, level):
        self.value = level
        
class Connection(BaseNode):
    def __init__(self, name, target, source, factor = 1, controllable = False):
        super(Connection, self).__init__(name, controllable)
        self.source = source
        self.target = target
        self.factor = factor

    def getChange(self, timestamp, condition, rec_duration):
        if isinstance(self.source, Capacitance):
            return (self.source.getTemp(timestamp, condition) - self.target.getTemp(timestamp, condition))*self.factor.value*rec_duration
        if isinstance(self.source, Heater):
            return self.source.useEnergy(timestamp, condition, rec_duration, self.factor.value)

#class EnergySource(BaseNode):
#
#class Battery(EnergySource):
#    def __init__(self, name, capacity, currentCapacity):
#        self.prices = prices
#        self.cost = 0
#        super(Fuel, self).__init__(name)

class Fuel(BaseNode):
    def __init__(self, name, prices, parent = None, controllable = False):
        self.prices = prices
        self.cost = 0
        self.parent = parent
        super(Fuel, self).__init__(name, controllable)
        
    def __repr__(self):
        return  "{} {}€".format(self.name,self.cost.round(2))
        
    def reset(self):
        self.cost = 0

    def getCost(self):
        return self.cost

    def getPrice(self, timestamp):
        if callable(self.prices):
            return self.prices(timestamp)
        if isinstance(self.prices, list):
            return self.searchBefore(timestamp, self.prices)
        return self.prices
        
    def useEnergy(self, timestamp, energy, condition):
        self.cost += self.getPrice(timestamp)*abs(energy)

class Heater(BaseNode):
    def __init__(self, name, power, energysource = None, cop = 1):
        self.power = power
        self.energysource = energysource
        self.power_level = 1
        self.cop = cop
        controllable = True if energysource else False
        super(Heater, self).__init__(name, controllable)
        
    def reset(self):
        if self.energysource:
            self.energysource.reset()
        self.data = []
        
    def getMaxPower(self, timestamp, condition):
        if callable(self.power):
          condition["level"] = self.power_level
          return self.power(condition)
        return self.power
        
    def setLevel(self, level):
        self.power_level = level
        
    def useEnergy(self, timestamp, condition, duration, factor):
        energy = self.getMaxPower(timestamp, condition)*duration*factor*self.power_level
        if(self.energysource):
            cop = self.cop(timestamp, condition) if callable(self.cop) else self.cop
            self.energysource.useEnergy(timestamp, energy/cop, condition)
        timestamp = timestamp-duration*3600
        if self.data and self.data[-1][0] == timestamp:
            self.data[-1][2] += energy/duration
        else:
            self.data.append([timestamp, self.power_level, energy/duration])
        return energy
