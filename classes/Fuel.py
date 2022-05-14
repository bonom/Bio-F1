from typing import Union
import pandas as pd
import numpy as np
import math
import pickle
import sys, os
from classes.RangeDictionary import RangeDictionary
import plotly.express as px
import plotly
from sklearn.linear_model import LinearRegression

from classes.Utils import get_basic_logger, get_host

log = get_basic_logger('Fuel')

class Fuel:
    def __init__(self, df:pd.DataFrame=None, load_path:str=None, start:int=0) -> None:
        if df is not None:

            indexes = list()
            laps = [int(x) for x in df['NumLaps'].unique() if not math.isnan(x)]
            for lap in laps:
                if not math.isnan(lap):
                    indexes.append((min(df.loc[df['NumLaps'] == lap,'FrameIdentifier'].values), max(df.loc[df['NumLaps'] == lap,'FrameIdentifier'].values)))
            
            self.lap_frames = dict()
            max_lap_len = len(indexes)
            for idx in range(max_lap_len):
                if idx < max_lap_len-1:
                    start,_ = indexes[idx]
                    end,_ = indexes[idx+1]
                else:
                    start, end = indexes[idx]
                for i in range(start,end):
                    self.lap_frames[i] = idx + round(((i - start)/(end - start)),4)  
            
            #print(f"Lap frame [0]: {list(self.lap_frames.items())[0]}")
            #print(f"Lap frame [1]: {list(self.lap_frames.items())[1]}")

            df = df.loc[(df['FrameIdentifier'] >= list(self.lap_frames.keys())[0]) & (df['FrameIdentifier'] <= list(self.lap_frames.keys())[-1])]

            self.FuelInTank = RangeDictionary(df[['FrameIdentifier','FuelInTank']])
            self.FuelCapacity = RangeDictionary(df[['FrameIdentifier','FuelCapacity']])
            self.FuelRemainingLaps = RangeDictionary(df[['FrameIdentifier','FuelRemainingLaps']])

            ### MODEL ###
            x = np.array([int(key) for key in self.FuelInTank.keys()]).reshape((-1,1))
            y = np.array(list(self.FuelInTank.values()))
            if math.isnan(y[0]):
                y[0] = 0

            self.model = LinearRegression().fit(x,y)
            
        elif load_path is not None:
            data = self.load(load_path)
            self.lap_frames = data.lap_frames
            self.FuelInTank = data.FuelInTank
            self.FuelCapacity = data.FuelCapacity
            self.FuelRemainingLaps = data.FuelRemainingLaps
            self.model = data.model


    def __getitem__(self, idx) -> dict:
        if idx == -1:
            idx = self.__len__() - 1
        
        idx -= list(self.lap_frames.keys())[0]
        lap = self.get_lap(idx)
        return {'NumLap': lap, 'FuelInTank': self.FuelInTank[idx], 'FuelCapacity': self.FuelCapacity[idx], 'FuelRemaining': self.FuelRemainingLaps[idx]}

    def get_lap(self, frame, get_float:bool=False) -> Union[int,float]:
        if get_float:
            return self.lap_frames[frame]
        
        return int(self.lap_frames[frame])

    def get_frame(self, lap_num:Union[int,float]) -> int:
        for frame, lap in self.lap_frames.items():
            if lap == lap_num:
                return frame
        
        return -1

    def consumption(self, display:bool=False) -> dict:
        
        fuel_consume = {'Frame':[int(value) for value in self.FuelInTank.keys()],'Fuel':[value for value in self.FuelInTank.values()], 'Lap':[]}

        for value in fuel_consume['Frame']:
            fuel_consume['Lap'].append(self.get_lap(value, True))
        
        if display:
            fuel_consume_df = pd.DataFrame(fuel_consume)
            
            max_lap = int(max(fuel_consume_df['Lap']))
            fuel_consume_df = fuel_consume_df[fuel_consume_df['Lap'] <= max_lap]
            fuel_consume_df.drop_duplicates(subset=['Lap'], keep='first', inplace=True)
            
            fig = px.line(fuel_consume_df, x='Lap',y='Fuel', title='Fuel Consumption', range_y=[0,100], range_x=[-0.1,max(fuel_consume_df['Lap'])+1]) #Need to check what is the maximum value of the fuel load
            
            if get_host() == 'DESKTOP-KICFR1D':
                plotly.offline.plot(fig, filename='Plots/Fuel consumption.html')
            else:
                fig.show()


        return fuel_consume
    
    def predict_fuelload(self, x_predict:int) -> float:
        """
        Return the 2 coefficient beta_0 and beta_1 for the linear model that fits the data : Time/Fuel
        """
        x_predict = np.array(x_predict).reshape(-1,1)
        y_predict = self.model.predict(x_predict)
        
        y_predict = round(y_predict[0],2)
        log.info(f"Predicted fuel consumption for lap {self.get_lap(int(x_predict))} (frame {int(x_predict)}) is {y_predict} %")
        
        return y_predict

    def save(self, save_path:str='', id:int=0) -> None:
        save_path = os.path.join(save_path,'Fuel_'+str(id)+'.json')
        with open(save_path, 'wb') as f:
            pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)
    
    def load(self, path:str=''):
        with open(path, 'rb') as f:
            return pickle.load(f)

    

def get_fuel_data(df:pd.DataFrame, separators:dict, path:str=None) -> set:
    """
    Get the fuel data from the dataframe
    """
    ### Initialize the set 
    fuel_data = dict()

    if path is not None:
        log.info('Specified load path, trying to find Fuel_*.json files...')
        files = [f for f in os.listdir(path) if f.endswith('.json') and f.startswith('Fuel_')]
        if len(files) > 0:
            log.info('Specified load path with files inside. Loading fuel data from file...')
            for file in files:
                fuel = Fuel(load_path=os.path.join(path,file))
                idx = int(file.replace('Fuel_','').replace('.json',''))
                fuel_data[idx] = fuel
                
            log.info('Loading completed.')
            return fuel_data
                
    
    if path is not None:
        log.info(f'No Fuel_*.json files found in "{path}". Loading fuel data from dataframe.')
    else:
        log.info('No load path specified. Loading fuel data from dataframe.')

    ### Initialize the columns of interest
    fuel_columns = ['FrameIdentifier', 'NumLaps', 'FuelInTank', 'FuelCapacity','FuelRemainingLaps']

    ### Cycle over all the times we box
    for key, (sep_start,sep_end) in separators.items():
        ### Get the numLap data of the laps we are considering
        numLaps = np.array(df.loc[(df['FrameIdentifier'] >= sep_start) & (df['FrameIdentifier'] <= sep_end),'NumLaps'].unique())
        numLaps = [int(x) for x in numLaps if not math.isnan(x)]

        if len(numLaps) > 3:
            ### Get the fuel data of the laps we are considering
            data = df.loc[(df['FrameIdentifier'] >= sep_start) & (df['FrameIdentifier'] <= sep_end),fuel_columns]

            ### Add them to the set
            fuel = Fuel(df=data, start=sep_start)
            fuel.save(path,id=key)
            fuel_data[key] = fuel
        else:
            log.warning(f"Insufficient data (below 3 laps). Skipping {key+1}/{len(separators.keys())}.")
            
    return fuel_data

if __name__ == "__main__":
    log.warning("This module is not intended to be used as a standalone script. Run 'python main.py' instead.")
    sys.exit(1)