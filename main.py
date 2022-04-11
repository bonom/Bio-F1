import math
import sys
import pandas as pd
import os
from tqdm import tqdm
from classes.Tyres import get_tyres_data
from classes.Extractor import extract_data,unify_car_data
from classes.Utils import get_basic_logger

import plotly.express as px

log = get_basic_logger('MAIN')

def remove_duplicates(directory:str):
    files = os.listdir(directory)
    files = [f for f in os.listdir(directory) if f.endswith('.csv')]
    for file in tqdm(files):
        df = pd.read_csv(os.path.join(directory,file))
        try:
            df.drop_duplicates(['FrameIdentifier','CarIndex'],inplace=True)
            df.sort_values(by=['FrameIdentifier','CarIndex'],inplace=True)
        except KeyError:
            df.drop_duplicates(['FrameIdentifier'],inplace=True)
            df.sort_values(by=['FrameIdentifier'],inplace=True)
        
        df.to_csv(os.path.join(directory,file),index=False)
    


def list_data(directory:str='Data'):
    folders = list(os.walk(directory))[0][1]
    print(f"Select the folder data to use:")
    for idx,folder in enumerate(folders):
        print(f" {idx} for {folder}")
    
    folder_id = int(input("Enter the folder id: "))
    while folder_id < 0 or folder_id >= len(folders):
        folder_id = int(input("Invalid input. Enter a valid folder id: "))
    
    folder = folders[folder_id]

    return "Data/{}".format(folder)
    

def main(folder:str='',car_id:int=19):
    log.info(f"Getting data for car '{car_id}'...")
    if folder == '':
        folder = list_data()
    
    damage, history, lap, motion, session, setup, status, telemetry, min_frame, max_frame = extract_data(path=folder)

    damage.set_index('FrameIdentifier',inplace=True)
    history.set_index('FrameIdentifier',inplace=True)
    lap.set_index('FrameIdentifier',inplace=True)
    motion.set_index('FrameIdentifier',inplace=True)
    session.set_index('FrameIdentifier',inplace=True)
    setup.set_index('FrameIdentifier',inplace=True)
    status.set_index('FrameIdentifier',inplace=True)
    telemetry.set_index('FrameIdentifier',inplace=True)

    df = pd.concat([damage, history, lap, motion, session, setup, status, telemetry], axis=1)
    df.sort_index(inplace=True)
    df.reset_index(inplace=True)

    log.info(f"Complete unification of data for car '{car_id}'")

    tyres_data = get_tyres_data(df)

    #for idx, data in tyres_data:
    #    data.tyres_slip(display=False)
    #    data.tyres_wear(display=False)
    #    data.tyres_timing(display=False)
    

if __name__ == "__main__":
    if len(sys.argv) > 1:
        main(sys.argv[1])
    else:
        main()

    
    """
    import plotly.express as px
    #import plotly #if for offline save
    from plotly.subplots import make_subplots

    # HOW TO PLOT SUBPLOTS WITH PLOTLY EXPRESS

    fig = make_subplots(rows=3, cols=2)
    damage = pd.read_csv('Data/Damage.csv')
        
    fig1 = px.line(damage.loc[(damage['CarIndex']==19) & (damage['FrameIdentifier'] < 32450)],x="FrameIdentifier",y=['TyresWearRL','TyresWearRR','TyresWearFL','TyresWearFR'], range_y=[0,100])
    fig2 = px.line(damage.loc[(damage['CarIndex']==19) & (damage['FrameIdentifier'] < 32450)],x="FrameIdentifier",y=['TyresDamageRL','TyresDamageRR','TyresDamageFL','TyresDamageFR'], range_y=[0,100])

    motion = pd.read_csv('Data/Motion.csv')
    fig3 = px.line(motion.loc[(motion['CarIndex'] == 19) & (motion['FrameIdentifier'] < 32450)], y=['RLWheelSlip', 'RRWheelSlip', 'FLWheelSlip', 'FRWheelSlip'], x='FrameIdentifier', range_y=[-1.1,1.1])
    fig4 = px.line(motion.loc[(motion['CarIndex'] == 19) & (motion['FrameIdentifier'] < 32450)], y=['Roll'], x='FrameIdentifier')
    
    telemetry = pd.read_csv('Data/Telemetry.csv')
    fig5 = px.line(telemetry.loc[(telemetry['CarIndex'] == 19) & (telemetry['FrameIdentifier'] < 32450)], y=['RLTyreSurfaceTemperature', 'RRTyreSurfaceTemperature', 'FLTyreSurfaceTemperature', 'FRTyreSurfaceTemperature'], x='FrameIdentifier')
    fig6 = px.line(telemetry.loc[(telemetry['CarIndex'] == 19) & (telemetry['FrameIdentifier'] < 32450)], y=['RLTyreInnerTemperature', 'RRTyreInnerTemperature', 'FLTyreInnerTemperature', 'FRTyreInnerTemperature'], x='FrameIdentifier')

    fig1_traces = []
    fig2_traces = []
    fig3_traces = []
    fig4_traces = []
    fig5_traces = []
    fig6_traces = []

    for trace in range(len(fig1["data"])):
        fig1_traces.append(fig1["data"][trace])

    for trace in range(len(fig2["data"])):
        fig2_traces.append(fig2["data"][trace])
    
    for trace in range(len(fig3["data"])):
        fig3_traces.append(fig3["data"][trace])
    
    for trace in range(len(fig4["data"])):
        fig4_traces.append(fig4["data"][trace])
    
    for trace in range(len(fig5["data"])):
        fig5_traces.append(fig5["data"][trace])
    
    for trace in range(len(fig6["data"])):
        fig6_traces.append(fig6["data"][trace])
    
    for traces in fig1_traces:
        fig.append_trace(traces, row=1, col=1)
    for traces in fig2_traces:
        fig.append_trace(traces, row=1, col=2)
    for traces in fig3_traces:
        fig.append_trace(traces, row=2, col=1)
    for traces in fig4_traces:
        fig.append_trace(traces, row=2, col=2)
    for traces in fig5_traces:
        fig.append_trace(traces, row=3, col=1)
    for traces in fig6_traces:
        fig.append_trace(traces, row=3, col=2)

    
    fig.show()

    #plotly.offline.plot(fig, filename='tyres_data.html')
    """