import sys, os
import pandas as pd
import numpy as np
from classes.Genetic import GeneticSolver
from classes.Car import get_cars
from classes.Timing import Timing, get_timing_data
from classes.Tyres import Tyres, get_tyres_data
from classes.Fuel import Fuel, get_fuel_data
from classes.Extractor import extract_data
from classes.Utils import MultiPlot, get_basic_logger, get_car_name, list_data, ms_to_m, separate_data, list_circuits

import plotly.express as px

import argparse

parser = argparse.ArgumentParser(description='Process F1 Data.')
parser.add_argument('--i', type=int, default=None, help='Car ID')
parser.add_argument('--c', type=str, default=None, help='Circuit path')
args = parser.parse_args()

log_dl = get_basic_logger('DataLoad')
log_main = get_basic_logger('Main')

def printStrategy(strategy):
    log_main.debug(strategy)
    log_main.debug(strategy['TyreStint'])
    log_main.debug(len(strategy['TyreStint']))
    for lap in range(len(strategy['TyreStint'])):
        log_main.info(f"Lap {lap+1} -> Stint '{strategy['TyreStint'][lap]}', Wear '{round(strategy['TyreWear'][lap]['FL'],2)}'% | '{round(strategy['TyreWear'][lap]['FR'],2)}'% | '{round(strategy['TyreWear'][lap]['RL'],2)}'% | '{round(strategy['TyreWear'][lap]['RR'],2)}'%, Fuel '{round(strategy['FuelLoad'][lap],2)}' Kg, PitStop '{'Yes' if strategy['PitStop'][lap] else 'No'}', Time '{strategy['LapTime'][lap]}' ms")

def DataLoad(car_id:int=19,folder:str=''): #data_folder:str='Data',circuit:str='',
    """
    Main wrapper, takes the folder where the csv's are stores and car id as input and runs the whole process.
    """
    ### Getting data from the 'folder'/'circuit' path
    log_dl.info(f"Getting data for car '{car_id}'...")
    concat_path = os.path.join(folder,'ConcatData')
    if not os.path.exists(concat_path):
        os.makedirs(concat_path)
    
    if os.path.isfile(os.path.join(concat_path,'CarId_{}.csv'.format(car_id))):
        #log_dl.info(f"Found concatenated data for car '{car_id}' in '{concat_path}'")
        df = pd.read_csv(os.path.join(concat_path,'CarId_{}.csv'.format(car_id)))
    else:
        acquired_data_folder = os.path.join(folder,'Acquired_data')
        log_dl.info(f"No existing concatenated data found. Concatenating data for car '{car_id}'...")
        
        ### This function removes duplicates of the dataframe and returns the dataframe with the unique rows (based on 'FrameIdentifier')
        #remove_duplicates(acquired_data_folder) 
        damage:pd.DataFrame = None
        history:pd.DataFrame = None
        lap:pd.DataFrame = None
        motion:pd.DataFrame = None
        session:pd.DataFrame = None
        setup:pd.DataFrame = None
        status:pd.DataFrame = None
        telemetry:pd.DataFrame = None

        damage, history, lap, motion, session, setup, status, telemetry = extract_data(path=acquired_data_folder, idx=car_id)

        ### Creating a single dataframe with all the data
        ### In order to concatenate all data in a single dataframe (which is more easier to deal with) we need to set the FrameIdentifier (which is unique) as index
        damage.set_index('FrameIdentifier',inplace=True)
        history.set_index('FrameIdentifier',inplace=True)
        lap.set_index('FrameIdentifier',inplace=True)
        motion.set_index('FrameIdentifier',inplace=True)
        session.set_index('FrameIdentifier',inplace=True)
        setup.set_index('FrameIdentifier',inplace=True)
        status.set_index('FrameIdentifier',inplace=True)
        telemetry.set_index('FrameIdentifier',inplace=True)

        log_dl.info("Concatenating data...")
        df = pd.concat([damage, history, lap, motion, session, setup, status, telemetry], axis=1)
        log_dl.info("Saving concatenated data...")
        df.drop(columns=['CarIndex'],inplace=True) # CarIndex is not needed anymore because it is in the file name
        df = df.loc[:,~df.columns.duplicated()] #Remove duplicated columns  
        df.sort_index(inplace=True) #Sort the dataframe by the index (in this case FrameIdentifier)
        df.reset_index(inplace=True) #Reset the index to 0,1,2,3... instead of FrameIdentifier
        df.to_csv(os.path.join(concat_path,'CarId_{}.csv'.format(car_id)),index=False) #Save the dataframe as a csv file in order to have it for future use

        log_dl.info(f"Complete unification of data for car '{car_id}' and saved it as 'ConcatData_Car{car_id}.csv'.")
    
    saves = os.path.join(folder,f'Saves/{car_id}')
    if not os.path.exists(saves):
        os.makedirs(saves)
    ### Separating the dataframe into different dataframes
    #log_dl.info(f"Separating data for car '{car_id}'...")
    separators = separate_data(df)
    #log_dl.info(f"Separation complete.")

    ### Getting the tyres data
    log_dl.info(f"Getting the data for the times ({len(separators.keys())})...")
    timing_data:Timing = get_timing_data(df, separators=separators,path=saves)
    log_dl.info(f"Complete getting the data for the times.")

    log_dl.info(f"Getting all the tyres used ({len(separators.keys())})...")
    tyres_data:Tyres = get_tyres_data(df, separators=separators,path=saves)
    log_dl.info(f"Complete getting all the tyres used.")

    log_dl.info(f"Getting the data for the fuel consumption ({len(separators.keys())})...")
    fuel_data:Fuel = get_fuel_data(df, separators=separators,path=saves)
    log_dl.info(f"Complete getting the data for the fuel consumption.")

    ### Return data
    to_ret = {'Times':timing_data,'Tyres':tyres_data,'Fuel':fuel_data}

    return to_ret

    for key,value in timing_data.items():
        df = pd.DataFrame(columns=['Frame','Lap','Delta','Wear_FL','Wear_FR','Wear_RL','Wear_RR','Fuel'])
        #best = min([x for x in value.LapTimes if x > 0])
        for idx, delta in enumerate(value.Deltas): #Deltas
            ### Get Frame to use indexing (__getitem__)
            frame = value.get_frame(idx+1)
            
            ### Tyres
            tyres_wear = {'FL':0, 'FR':0, 'RL':0, 'RR':0}
            for tyre in ['FL', 'FR', 'RL', 'RR']:
                wear = tyres_data[key][frame][tyre+'Tyre']['TyreWear']
                tyres_wear[tyre] = wear
            
            fuel_consume = fuel_data[key][frame]['FuelInTank']
            
            df.loc[idx] = [int(frame),idx,delta,tyres_wear['FL'],tyres_wear['FR'],tyres_wear['RL'],tyres_wear['RR'],fuel_consume]

            #log.debug(f"Lap: {idx}, Delta: {delta}, Wear: {tyres_wear}, Fuel: {fuel_consume}")
        
        df.sort_values(by=['Lap'],inplace=True)
        df = df.loc[df['Delta'] >= 0]

        x = df['Lap'].values
        y = df['Delta'].values
        y = [np.log(y) if y > 0 else 0 for y in df['Delta'].values]

        try:
            coefficients = np.polyfit(x,y,1)

            poly = np.poly1d(coefficients)

            new_x = np.linspace(x[0], x[-1])
            new_y = poly(new_x)
        except:
            new_x = 0
            new_y = 0

        #fig = make_subplots(rows=4, cols=2)
        fig = MultiPlot(4,2,titles=['TimeDelta w.r.t '+ms_to_m(value.BestLapTime), 'LapDeltaPolyFit', 'TyresWear on '+tyres_data[key].get_visual_compound(), 'Fuel Consumption', 'Delta/Wear', 'Delta/Fuel', 'FuelPolyFit'])
        

        fig1 = px.line(df, x='Lap', y='Delta', title='Delta')
        fig2 = px.line(pd.DataFrame({'Lap':new_x, 'Delta':new_y}), x='Lap', y='Delta', title='Delta')
        fig3 = px.line(df, x='Lap', y=['Wear_FL','Wear_FR','Wear_RL','Wear_RR'], title='Tyres Wear')
        fig4 = px.line(df, x='Lap', y='Fuel', title='Fuel Consumption')

        df = df.sort_values(by='Delta')
        fig5 = px.line(df,x='Delta',y=['Wear_FL','Wear_FR','Wear_RL','Wear_RR'])
        fig6 = px.line(df,x='Delta',y='Fuel')

        x = df['Delta'].values
        y = df['Fuel'].values

        coefficients = np.polyfit(x, y, 1)
        poly = np.poly1d(coefficients)

        new_x = np.linspace(x[0], x[-1])
        new_y = poly(new_x)

        fig7 = px.line(pd.DataFrame({'Delta':new_x, 'Fuel':new_y}), x='Delta', y='Fuel', title='Fuel Consumption')

        fig.add_trace(fig1, row=1, col=1)
        fig.add_trace(fig2, row=1, col=2)
        fig.add_trace(fig3, row=2, col=1)
        fig.add_trace(fig4, row=2, col=2)
        fig.add_trace(fig5, row=3, col=1)
        fig.add_trace(fig6, row=3, col=2)
        fig.add_trace(fig7, row=4, col=1)

        path = os.path.abspath(folder)
        if os.name == 'posix':
            path = path.split('/')
        else:
            path = path.split('\\')
        
        plots_path = os.path.join('Plots',path[-2],path[-1])
        fig.set_title(f"Car {car_id} -> {get_car_name(car_id,path=folder)} (DATA {key})")
        
        fig.save(os.path.join(plots_path,f'Car{car_id}.html'))
        fig.show()
        
    return to_ret
    
def main():
    if not os.path.exists('Plots'):
        os.mkdir('Plots')

    data = dict()
    
    if args.c == '' or args.c is None:
        circuit_folder = os.path.abspath(list_circuits(os.path.abspath('Data')))
    else:
        circuit_folder = os.path.abspath(args.c)
    # if args.f == '' or args.f is None:
    #     ### There is no specific folder of data => we use all the data in a given circuit
    #     if args.c == '' or args.c is None:
    #         ### There is no specific circuit => We have to get it from the user
    #         circuit_folder = os.path.abspath(list_circuits(args.d)) # Returns the path to the circuit folder
    #     else:
    #         circuit_folder = os.path.abspath(args.c)
    #     folder = os.path.abspath(list_data(circuit_folder)) # Returns the path to the data folder
    #     data_folder = os.path.abspath('Data')

    # else:
    #     folder:str = os.path.abspath(args.f)
    #     if args.c == '' or args.c is None:
    #         circuit = folder.split('/')[:-1] if os.name == 'posix' else folder.split('\\')[:-1]
    #         circuit_folder = ''
    #         for c in circuit:
    #             circuit_folder += c+'/' if os.name == 'posix' else c+'\\'
    #         circuit_folder = os.path.abspath(circuit_folder)
    #     else:
    #         circuit_folder = os.path.abspath(args.c)
    #     data_folder = os.path.abspath('Data')

    if args.i is not None:
        log_main.info("------------------------- Loading data -------------------------")
        for folder in os.listdir(circuit_folder):
            if folder not in ['.DS_Store', 'CarSaves']:
                data = DataLoad(args.i, os.path.join(circuit_folder,folder))
        log_main.info("----------------------- End data loading -----------------------")
        log_main.info("-------------------------  Car loading -------------------------")
        car = get_cars(path=circuit_folder,load_path=os.path.join(circuit_folder,'CarSaves'), car_idx=args.i)
        log_main.info("-----------------------  End car loading -----------------------")
        log_main.info("----------------------- Start Evolutions -----------------------")
        genetic = GeneticSolver(population=1000, mutation_pr=0.5, crossover_pr=0.5, iterations=1000, numLaps=54, car=car)
        strategy, _, vals = genetic.startSolver()
        log_main.info("----------------------- Ended Evolutions -----------------------")
        printStrategy(strategy)
        df = pd.DataFrame(list(vals.items()), columns=['Generation','Fitness'])
        (px.line(df, x='Generation', y='Fitness', title="Fitness values",)).show()
    else:
        for folder in os.listdir(circuit_folder):
            for i in range(0,20):
                data[i] = DataLoad(i,folder) #data_folder,circuit_folder,
        
        cars = get_cars(path=circuit_folder,load_path=os.path.join(circuit_folder,'CarSaves'))
        
        for i in range(0,20):
            genetic = GeneticSolver(population=1000, mutation_pr=1, crossover_pr=1, iterations=1, numLaps=54, car=cars[i])
            strategy, _, vals = genetic.startSolver()
            printStrategy(strategy)
            df = pd.DataFrame(list(vals.items()), columns=['Generation','Fitness'])
            (px.line(df, x='Generation', y='Fitness', title="Fitness values",)).show()

if __name__ == "__main__":
    main() 
    sys.exit(0)
    