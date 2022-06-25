import math
import numpy as np
from classes.Car import Car
from random import SystemRandom
random = SystemRandom()

from classes.Utils import CIRCUIT, get_basic_logger, COMPOUNDS, ms_to_time

log = get_basic_logger('Genetic')

DRY_COMPOUNDS:list = ['Soft', 'Medium', 'Hard']
PITSTOP = [True, False]

def overLimit(values, limit):
    if not isinstance(values, list):
        values = list(values)
    for val in values:
        if val >= limit:
            return True
    
    return False

def checkTyreAvailability(compound, tyres):
    if tyres[compound]['Used'] == 0 and tyres[compound]['New'] == 0:
        return None
    elif tyres[compound]['New'] == 0:
        return "Used"
    return "New"

def changeTyre(tyresWear:dict):
    if all([x < 0.4 for x in tyresWear.values()]):
        return False

    boundary = random.random()
    for wear in tyresWear.values():
        if boundary < wear:
            return True
    return False

class GeneticSolver:
    def __init__(self, population:int=2, mutation_pr:float=0.0, crossover_pr:float=0.0, iterations:int=1, car:Car=None, circuit:str='', wet_probability:float=0.1) -> None:
        self.circuit = circuit
        self.pitStopTime = CIRCUIT[circuit]['PitStopTime']
        self.availableTyres:dict = dict()
        self.sigma = mutation_pr
        self.mu = crossover_pr
        self.population = population
        self.numLaps = CIRCUIT[circuit]['Laps']+1
        self.iterations = iterations
        self.car:Car = car
        self.weather = ['Dry' if random.random() > wet_probability else 'Wet' for i in range(self.numLaps)]
        
        self.mu_decay = 0.99
        self.sigma_decay = 0.99

        self.availableTyres = self.get_available_tyres(circuit)

    def get_available_tyres(self, circuit:str):
        available_tyres = {'Soft':{'Used': 0, 'New': 0}, 'Medium':{'Used': 0, 'New': 0}, 'Hard':{'Used': 0, 'New': 0}, 'Inter':{'Used': 0, 'New': 0}, 'Wet':{'Used': 0, 'New': 0}}
        print(f"Please insert tyres available for '{circuit}':")
        for tyre in ['Soft', 'Medium', 'Hard', 'Inter', 'Wet']:
            #available_tyres[tyre]['Used'] = int(input(f"\t\t\t {tyre} Used: "))
            #available_tyres[tyre]['New'] = int(input(f"\t\t\t {tyre} New: "))
            available_tyres[tyre]['Used'] += 1
            available_tyres[tyre]['New'] += 1
        
        return available_tyres

    def print(self) -> str:
        string = ''
        for i in range(self.population):
            string+=f"---------- Individual {i+1} ----------\n"
            for lap in range(self.numLaps):
                string+=f"{lap+1}º LapTime: {ms_to_time(self.strategies[i]['LapTime'][lap])} | TyreCompound: {self.strategies[i]['TyreCompound'][lap]} | TyreWear: {self.strategies[i]['TyreWear'][lap]} | FuelLoad: {self.strategies[i]['FuelLoad'][lap]} | PitStop: {self.strategies[i]['PitStop'][lap]} | LapsCompound: {self.strategies[i]['LapsCompound'][lap]}\n"
            string+=f"TotalTime: {ms_to_time(self.strategies[i]['TotalTime'])}\n"
            string+="\n"

        return string
    
    def getTyreWear(self, compound:str, lap:int):
        if lap == 0:
            return {'FL':0.0, 'FR':0.0, 'RL':0.0, 'RR':0.0}

        wear = self.car.predict_tyre_wear(compound, lap)
        
        for key, val in wear.items():
            wear[key] = val/100
        
        return wear
    
    def getBestLapTime(self,):
        return self.car.time_diff['Soft']

    def getFuelLoad(self, initial_fuel:float, conditions:list) :
        return self.car.predict_fuel_weight(initial_fuel, conditions)
    
    def getInitialFuelLoad(self, conditions:list):
        return self.car.predict_starting_fuel(conditions)

    def getWearTimeLose(self, compound:str, lap:int):
        return self.car.predict_tyre_time_lose(compound, lap)
        
    def getFuelTimeLose(self, lap:int=0, fuel_load:float=0, initial_fuel:float=0, conditions:list=None):
        if fuel_load == 0:
            fuel_load = self.getFuelLoad(lap, initial_fuel, conditions)
        
        return self.car.predict_fuel_time_lose(fuel_load)
    
    def getLapTime(self, compound:str, compoundAge:int, lap:int, fuel_load:float, conditions:list, drs:bool, pitStop:bool) -> int:
        time = self.car.predict_laptime(tyre=compound, tyre_age=compoundAge, lap=lap, start_fuel=fuel_load, conditions=conditions, drs=drs)

        if pitStop:
            time += self.pitStopTime

        if lap == 0:
            time += 2000

        return round(time) 

    def startSolver(self,):
        fitness_values = list()

        # initial population of random bitstring
        pop = self.initSolver()
        
        # keep track of best solution
        best, best_eval = pop[0], pop[0]['TotalTime']
        
        # enumerate generations
        try:
            for gen in range(self.iterations):
                temp_best, temp_best_eval = 0, pop[0]['TotalTime']

                # evaluate all candidates in the population
                scores = [c['TotalTime'] for c in pop]
                # check for new best solution
                for i in range(self.population):
                    if scores[i] < best_eval:
                        best, best_eval = pop[i], scores[i]
                    if scores[i] < temp_best_eval:
                        temp_best, temp_best_eval = pop[i], scores[i]
                
                # select parents
                selected = self.selection(population=pop,percentage=1)
               
                # create the next generation
                children = [parent for parent in selected]
                #for i in range(0, len(selected)-1):
                #    children.append(selected[i])

                if len(selected) > self.population:
                    selected = selected[:self.population]

                for i in range(0, len(selected), 2): # why not 1? I know there will be 2*population length - 2 but maybe it is good
                    # get selected parents in pairs
                    p1, p2 = selected[i], selected[i+1]
                    # crossover and mutation
                    for c in self.crossover(p1, p2):
                        # mutation
                        for l in self.mutation(c):
                            children.append(l)
                        
                # add children to the population if the population is not full
                for _ in range(self.population-len(children)):
                    children.append(self.randomChild())
                
                # replace population
                pop = children
                
                #self.sigma = self.sigma * self.sigma_decay
                #self.mu = self.mu * self.mu_decay

                fitness_values.append(temp_best_eval)

                #if gen%10:
                log.info(f'Generation {gen+1}/{self.iterations} best overall: {ms_to_time(best_eval)}, best of generation: {ms_to_time(temp_best_eval)}, valid individuals: {round(len(selected)/self.population,2)}%')
                
        except KeyboardInterrupt:
            pass 
        
        return best, best_eval, {key+1:val for key, val in enumerate(fitness_values)}  

    def initSolver(self,):
        strategies = []
        for _ in range(self.population):
            strategies.append(self.randomChild())

        return strategies

    def randomChild(self):
        strategy = {'TyresAvailability': self.availableTyres.copy(), 'TyreCompound': [], 'TyreStatus':[], 'TyreWear':[] , 'FuelLoad':[] , 'PitStop': [], 'LapTime':[], 'NumPitStop': 0, 'LapsCompound':[], 'Weather':self.weather.copy(), 'TotalTime': np.inf}

        weather = [strategy['Weather'][0]]

        ### Get a random compound and verify that we can use it, if so we update the used compounds list and add the compound to the strategy
        compound, tyreState = self.checkCompound(availableTyres=strategy['TyresAvailability'], weather=weather)
        strategy['TyreCompound'].append(compound)
        strategy['TyreStatus'].append(tyreState)

        ### If the compound is used we put a tyre wear of 2 laps (if it is used but available the compound has been used for 2/3 laps.
        ### However, 2 laps out of 3 are done very slowly and the wear is not as the same of 3 laps)
        ### If the compound is new tyre wear = 0
        tyresAge = 0 if tyreState == 'New' else 2
        strategy['TyreWear'].append(self.getTyreWear(compound, tyresAge))

        ### The fuel load can be inferred by the coefficient of the fuel consumption, we add a random value between -10 and 10 to get a little variation
        initialFuelLoad = self.getInitialFuelLoad(conditions=self.weather)+random.randint(-10,10)
        strategy['FuelLoad'].append(initialFuelLoad)

        ### At first lap the pit stop is not made (PitStop list means that at lap i^th the pit stop is made at the beginning of the lap)
        strategy['PitStop'].append(False)

        ### Compute lapTime
        strategy['LapTime'].append(self.getLapTime(compound=compound, compoundAge=tyresAge, lap=0, fuel_load=initialFuelLoad, conditions=weather, drs=False, pitStop=False))

        ### Add the laps counter of the compound on the car (+1 for all lap we complete with the compound, set to 0 when changing compound)
        strategy['LapsCompound'].append(tyresAge)

        ### For every lap we repeat the whole process
        for lap in range(1,self.numLaps):
            weather = strategy['Weather'][:lap+1]

            ### The fuel does not depend on the compound and/or pit stops => we compute it and leave it here
            fuelLoad = self.getFuelLoad(initial_fuel=initialFuelLoad, conditions=weather)
            strategy['FuelLoad'].append(fuelLoad)

            ### With probability of the tyre wear we make a pit stop (if tyre wear low we have low probability, else high)
            if changeTyre(strategy['TyreWear'][lap-1]):
                ### We have the case of the pitStop => new tyre (can be the same compound type of before!!!)
                compound, tyreState = self.checkCompound(availableTyres=strategy['TyresAvailability'], weather=weather)
                
                if compound is None and tyreState is None:
                    return self.fillRemainings(lap, strategy)

                tyresAge = 0 if tyreState == 'New' else 2
                pitStop = True
                strategy['NumPitStop'] += 1
            else:
                ### No pitstop => same tyres of lap before
                compound = strategy['TyreCompound'][lap-1]
                tyreState = "Used"
                tyresAge += 1
                pitStop = False
                
            strategy['TyreStatus'].append(tyreState)
            strategy['TyreCompound'].append(compound)
            strategy['TyreWear'].append(self.getTyreWear(compound, tyresAge))
            strategy['PitStop'].append(pitStop)
            strategy['LapTime'].append(self.getLapTime(compound=compound, compoundAge=tyresAge, lap=lap, fuel_load=fuelLoad, conditions=weather, drs=False, pitStop=pitStop))
            strategy['LapsCompound'].append(tyresAge)
            
        
        ### Check that all constraints are ok and if so compute the Total Time
        allCompounds = set(strategy['TyreCompound'])
        if len(allCompounds) > 0 and strategy['FuelLoad'][-1] >= 1:
            strategy['TotalTime'] = sum(strategy['LapTime'])
        
        return strategy

    def randomCompound(self,weather:str):
        if weather == 'Wet':
            return random.choice(['Inter', 'Wet'])
        return random.choice(['Soft', 'Medium', 'Hard'])
    
    def checkCompound(self, compound:str=None, availableTyres:dict={}, weather:str="Dry"):
        if compound is not None:
            return checkTyreAvailability(compound,availableTyres)
        
        compound = self.randomCompound(weather)
        tyreState = checkTyreAvailability(compound,availableTyres)
        
        if tyreState is None:
            count = 0
            for tyres, states in availableTyres.items():
                if weather[-1] == "Dry" and tyres in ['Soft', 'Medium', 'Hard']:
                    for _, val in states.items():
                        if val > 0:
                            count += val
                if weather[-1] == "Wet" and tyres in ['Inter', 'Wet']:
                    for _, val in states.items():
                        if val > 0:
                            count += val

            if count == 0:
                return None, None
                
        while tyreState is None:
            compound = self.randomCompound(weather)
            tyreState = checkTyreAvailability(compound,availableTyres)

        availableTyres[compound][tyreState] -= 1

        return compound, 'New' if tyreState == 'New' else 'Used'

    def selection(self,population, percentage:float=0.4):
        sortedPopulation = sorted(population, key=lambda x: x['TotalTime'])
        
        selected = [x for x in sortedPopulation if not math.isinf(x['TotalTime'])]
        
        if len(selected) >= int(len(population)*percentage):
            return selected[:int(len(population)*percentage)]
        
        return selected

    def mutation_compound(self, child:dict):
        mutationCompound, tyreSate = self.checkCompound(availableTyres=child['TyresAvailability'])
        
        ### We do not have compounds available => we get a random child
        if mutationCompound is None:
            return self.randomChild()

        ### Initialize lap from which we will mutate
        lap = random.randint(0,self.numLaps-1)

        ### Until new pitStop we change the compound and then correct strategy will make everything ok
        pitStop = child['PitStop'][lap]
        while pitStop == False and lap < self.numLaps-1:
            child['TyreCompound'][lap] = mutationCompound
            pitStop = child['PitStop'][lap+1]
            lap += 1
        
        return self.correct_strategy(child)

    def mutation_pitstop(self,child:dict):
        childPitNum = child['NumPitStop'] 

        ### Check if we cannot make different pitStops number
        if childPitNum < 1:
            child['TotalTime'] = np.inf
            return child
        
        if childPitNum == 1:
            return child
        
        numRandomPitStop = random.randint(1,childPitNum)

        if numRandomPitStop == childPitNum:
            return child
        
        numPitStops = 0
        startLap = 0
        
        while numPitStops < numRandomPitStop:
            if child['PitStop'][startLap] == True:
                numPitStops += 1
            startLap += 1
        
        compound = child['TyreCompound'][startLap]
        for lap in range(startLap, self.numLaps):
            child['PitStop'][lap] = False
            child['TyreCompound'][lap] = compound

        return self.correct_strategy(child)

    def mutation(self,child:dict):
        childCompound = child
        childPitStop = child
        children = []
        if random.random() < self.sigma:
            children.append(self.mutation_compound(childCompound))
        
        if random.random() < self.sigma:
            children.append(self.mutation_pitstop(childPitStop))
        
        return children
    
    def crossover(self, p1:dict, p2:dict,):
        # children are copies of parents by default
        c1, c2 = p1.copy(), p2.copy()
        # check for recombination
        if random.random() < self.mu:
            # select crossover point that is not on the end of the string
            pt = random.randint(1, len(p1['TyreCompound'])-2)
            # perform crossover

            ### {'TyresAvailability': self.availableTyres.copy(), 'TyreCompound': [], 'TyreStatus':[], 'TyreWear':[] , 'FuelLoad':[] , 'PitStop': [], 'LapTime':[], 'NumPitStop': 0, 'LapsCompound':[], 'Weather':[], 'TotalTime': np.inf}
            c1 = {'TyresAvailability': self.availableTyres.copy(),'TyreCompound': p1['TyreCompound'][:pt]+p2['TyreCompound'][pt:], 'TyreStatus':p1['TyreStatus'][:pt]+p2['TyreStatus'][pt:], 'TyreWear': p1['TyreWear'][:pt]+p2['TyreWear'][pt:], 'FuelLoad': p1['FuelLoad'][:pt]+p2['FuelLoad'][pt:], 'PitStop': p1['PitStop'][:pt]+p2['PitStop'][pt:], 'LapTime': p1['LapTime'][:pt]+p2['LapTime'][pt:], 'LapsCompound': p1['LapsCompound'][:pt]+p2['LapsCompound'][pt:], 'Weather':p1, 'NumPitStop': p1['NumPitStop'], 'TotalTime': p1['TotalTime']}
            c2 = {'TyresAvailability': self.availableTyres.copy(),'TyreCompound': p2['TyreCompound'][:pt]+p1['TyreCompound'][pt:], 'TyreStatus':p2['TyreStatus'][:pt]+p1['TyreStatus'][pt:], 'TyreWear': p2['TyreWear'][:pt]+p1['TyreWear'][pt:], 'FuelLoad': p2['FuelLoad'][:pt]+p1['FuelLoad'][pt:], 'PitStop': p2['PitStop'][:pt]+p1['PitStop'][pt:], 'LapTime': p2['LapTime'][:pt]+p1['LapTime'][pt:], 'LapsCompound': p2['LapsCompound'][:pt]+p1['LapsCompound'][pt:], 'Weather':p2, 'NumPitStop': p2['NumPitStop'], 'TotalTime': p2['TotalTime']}
            
            return [self.correct_strategy(c1), self.correct_strategy(c2)]
        
        return [c1, c2]

    def correct_strategy(self, strategy:dict):
        initialFuelLoad = strategy['FuelLoad'][0]
        tyresAge = strategy['LapsCompound'][0]
        compound = strategy['TyreCompound'][0]
        
        tyreState = checkTyreAvailability(compound, strategy['TyresAvailability'])

        if tyreState is None:
            return self.randomChild()

        strategy['TyresAvailability'][compound][tyreState] -= 1
        pitStopCounter = 0
        
        for lap in range(1, self.numLaps):
            ### FuelLoad keeps the same, it just needs to be corrected if changed
            fuelLoad = self.getFuelLoad(lap=lap, initial_fuel=initialFuelLoad)
            strategy['FuelLoad'][lap] = fuelLoad

            ### Get if a pitstop is made and compound lap'
            pitStop = strategy['PitStop'][lap]
            compound = strategy['TyreCompound'][lap]
            
            ### We have two options: either there is a pitstop or the compound has changes, if so we have to recalculate all
            if pitStop or compound != strategy['TyreCompound'][lap-1] or any(strategy['TyreWear'][lap-1].values()) >= 0.8:
                strategy['PitStop'][lap] = True
                pitStopCounter += 1
                
                ### Checking availability of the compound int the set, if not available it will get random strategy
                tyreState = self.checkCompound(compound=compound, availableTyres=strategy['TyresAvailability'])
                if tyreState is None:
                    compound, tyreState = self.checkCompound(availableTyres=strategy['TyresAvailability'])
                    
                    ### If there are no tyres available, the strategy is not correct => replace it with a new randomic one
                    if compound is None and tyreState is None:
                        return self.randomChild()
                else:
                    key = checkTyreAvailability(compound, strategy['TyresAvailability'])
                    if key is None:
                        return self.randomChild()
                    strategy['TyresAvailability'][compound][key] -= 1

                tyresAge = 0 if tyreState == 'New' else 2
            else:
                tyresAge += 1
                tyreState = 'Used'
                
            tyreWear = self.getTyreWear(compound=compound, lap=tyresAge)
            strategy['TyreWear'][lap] = tyreWear
            strategy['TyreStatus'][lap] = tyreState
            strategy['LapsCompound'][lap] = tyresAge
            weather = strategy['Weather'][:lap+1]
            strategy['LapTime'][lap] = self.getLapTime(compound=compound, compoundAge=tyresAge, lap=lap, fuel_load=fuelLoad,conditions=weather, drs=False, pitStop=pitStop)
            pass

        strategy['NumPitStop'] = pitStopCounter

        ### Check that all constraints are ok and if so compute the Total Time
        allCompounds = set(strategy['TyreCompound'])
        if len(allCompounds) > 0 and strategy['FuelLoad'][-1] >= 1:
            strategy['TotalTime'] = sum(strategy['LapTime'])

        return strategy

    def fillRemainings(self, lap:int, strategy:dict):
        compound = strategy['TyreCompound'][lap-1]
        fuelLoad = strategy['FuelLoad'][lap-1]
        for _ in range(lap, self.numLaps):
            strategy['TyreStatus'].append('Used')
            strategy['TyreCompound'].append(compound)
            strategy['TyreWear'].append({'FL':1.0, 'FR':1.0, 'RL':1.0, 'RR':1.0})
            strategy['FuelLoad'].append(1000)
            strategy['LapsCompound'].append(0)
            strategy['PitStop'].append(False)
            strategy['LapTime'].append(0)

        return strategy

    
    def basicTiming(self,):
        pitStoplap = 25
        time = 0
        fuel_load=self.getInitialFuelLoad()
        for i in range(self.numLaps):
            if i == 0:
                time += self.lapTime(compound='Medium', compoundAge=i, lap=i, fuel_load=fuel_load, pitStop=False)
            elif i < pitStoplap:
                time += self.lapTime(compound='Medium', compoundAge=i, lap=i, fuel_load=self.getFuelLoad(i, fuel_load), pitStop=False)
            elif i == pitStoplap:
                time += self.lapTime(compound='Hard', compoundAge=i-pitStoplap, lap=i, fuel_load=self.getInitialFuelLoad(), pitStop=True)
            else:
                time += self.lapTime(compound='Hard', compoundAge=i-pitStoplap, lap=i, fuel_load=self.getInitialFuelLoad(), pitStop=False)
        
        return ms_to_time(time)