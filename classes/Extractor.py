from typing import Union
import os
import pandas as pd
import numpy as np
from tqdm import tqdm
from classes.Utils import get_basic_logger
from typing import Union
import sys

log = get_basic_logger('Extractor')

def fixer(df:pd.DataFrame, frame:int, col:str, before) -> pd.DataFrame:
    """
    Fixer function for the ``unify_car_data``  function, it returns the first compatible value in the dataframe.
    """
    if len(df.loc[df['FrameIdentifier'] == frame, col].to_numpy()) != 1:
        return before
    return df.loc[df['FrameIdentifier'] == frame, col].to_numpy()[0]

def unify_car_data(idx:int,damage:pd.DataFrame,history:pd.DataFrame,lap:pd.DataFrame,motion:pd.DataFrame,session:pd.DataFrame,setup:pd.DataFrame,status:pd.DataFrame,telemetry:pd.DataFrame,max_frame:int,min_frame:int=0) -> pd.DataFrame:
    """
    Unifies all dataframes into one dataframe. Dataframes must come after the ``extract_data`` function in order to work properly. 
    ATTENTION: This function is computationally heavy so use with care.

    Parameters: 
    - idx: int
        index of the car
    - damage: pd.DataFrame
        damage dataframe
    - history: pd.DataFrame
        history dataframe
    - lap: pd.DataFrame 
        lap dataframe
    - motion: pd.DataFrame
        motion dataframe
    - session: pd.DataFrame 
        session dataframe
    - setup: pd.DataFrame
        setup dataframe
    - status: pd.DataFrame
        status dataframe
    - telemetry: pd.DataFrame
        telemetry dataframe
    - max_frame: int    
        maximum frame number
    - min_frame: int
        minimum frame number

    Returns:
    - df: pd.DataFrame
        The unified dataframe

    Example:
    -------
    >>> unify_car_data(car_index,damage,history,lap,motion,session,setup,status,telemetry,max_frame,min_frame)
    """
    
    damage.drop('CarIndex', axis=1, inplace=True)
    history.drop('CarIndex', axis=1, inplace=True)
    lap.drop('CarIndex', axis=1, inplace=True)
    motion.drop('CarIndex', axis=1, inplace=True)
    setup.drop('CarIndex', axis=1, inplace=True)
    status.drop('CarIndex', axis=1, inplace=True)
    telemetry.drop('CarIndex', axis=1, inplace=True)

    
    damage_cols = damage.columns.to_numpy()
    history_cols = history.columns.to_numpy()
    lap_cols = lap.columns.to_numpy()
    motion_cols = motion.columns.to_numpy()
    session_cols = session.columns.to_numpy()
    setup_cols = setup.columns.to_numpy()
    status_cols = status.columns.to_numpy()
    telemetry_cols = telemetry.columns.to_numpy()
    
    columns = set()
    for i in damage_cols:
        if i not in columns:
            columns.add(i)
    for i in history_cols:
        if i not in columns:
            columns.add(i)
    for i in lap_cols:
        if i not in columns:
            columns.add(i)
    for i in motion_cols:
        if i not in columns:
            columns.add(i)
    for i in session_cols:
        if i not in columns:
            columns.add(i)
    for i in status_cols:
        if i not in columns:
            columns.add(i)
    for i in setup_cols:
        if i not in columns:
            columns.add(i)
    for i in telemetry_cols:
        if i not in columns:
            columns.add(i)
    
    
    add = {col:[] for col in columns}
    frames = list()
    columns.remove('FrameIdentifier')
    for i in tqdm(range(min_frame,max_frame)):#max_frame
        frames.append(i-min_frame) #(i)
        for col in columns:
            if col in damage_cols:
                add[col].append(fixer(damage, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in history_cols:
                add[col].append(fixer(history, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in lap_cols:   
                add[col].append(fixer(lap, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in motion_cols:
                add[col].append(fixer(motion, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in session_cols:
                add[col].append(fixer(session, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in setup_cols:
                add[col].append(fixer(setup, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in status_cols:
                add[col].append(fixer(status, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
            elif col in telemetry_cols:
                add[col].append(fixer(telemetry, i, col, add[col][-1] if len(add[col]) != 0 else np.nan))
     
    df = pd.DataFrame(columns=columns)
    for col in columns:
        if col != "FrameIdentifier":
            df[col] = add[col]

    df = df.reindex(sorted(df.columns), axis=1)
    
    df.insert(0, 'FrameIdentifier', frames)
    df.set_index('FrameIdentifier', inplace=True)
    df.to_csv(f"Car_{idx}_DATA.csv", index=True)

    return df

def remove_duplicates(directory:str):
    """
    Function that explores the directory and removes the duplicates row cycling over all *.csv files.
    """
    files = os.listdir(directory)
    files = [f for f in os.listdir(directory) if f.endswith('.csv')]
    for file in tqdm(files):
        df = pd.read_csv(os.path.join(directory,file), low_memory=False)
        try:
            df.drop_duplicates(['PacketId','FrameIdentifier','CarIndex'],inplace=True)
            df.sort_values(by=['PacketId','FrameIdentifier','CarIndex'],inplace=True)
        except KeyError:
            df.drop_duplicates(['PacketId','FrameIdentifier'],inplace=True)
            df.sort_values(by=['PacketId','FrameIdentifier'],inplace=True)
        
        df.to_csv(os.path.join(directory,file),index=False)
    

def extract_data(path:str='Data',idx:int=19) -> Union[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Extracts the very essentials data from the csv, in particular:
    - Damage    :   ['FrameIdentifier', 'CarIndex', 'TyresWearRL', 'TyresWearRR', 'TyresWearFL', 'TyresWearFR', 'TyresDamageRL', 'TyresDamageRR', 'TyresDamageFL', 'TyresDamageFR']
    - History   :   ['FrameIdentifier', 'CarIndex', 'NumLaps', 'NumTyreStints', 'BestLapTimeLapNum', 'BestSector1LapNum', 'BestSector2LapNum', 'BestSector3LapNum', 'lapTimeInMS[i]', 'sector1TimeInMS[i]', 'sector2TimeInMS[i]', 'sector3TimeInMS[i]', 'lapValidBitFlags[i]', 'endLap[j]', 'tyreActualCompound[j]', 'tyreVisualCompound[j]'
    - Lap       :   ['FrameIdentifier', 'CarIndex', 'LastLapTimeInMS', 'CurrentLapTimeInMS', 'Sector1TimeInMS', 'Sector2TimeInMS', 'LapDistance', 'TotalDistance', 'CurrentLapNum', 'Sector', 'PitStopShouldServePen']
    - Motion    :   ['FrameIdentifier', 'CarIndex', 'WorldPositionX', 'WorldPositionY', 'WorldPositionZ', 'RLWheelSlip', 'RRWheelSlip', 'FLWheelSlip', 'FRWheelSlip']
    - Session   :   ['FrameIdentifier', 'Weather', 'TrackTemperature', 'AirTemperature', 'TotalLaps', 'TrackLength', 'SessionType', 'TrackId', 'Formula', 'SessionTimeLeft', 'SessionDuration', 'NumMarshalZones', 'ZoneStart[i]', 'ZoneFlag[i]', 'ZoneFlag[16]', 'SafetyCarStatus', 'NumWeatherForecastSamples', 'ForecastAccuracy', 'PitStopWindowIdealLap', 'PitStopWindowLatestLap', 'PitStopRejoinPosition']
    - Setup     :   ['FrameIdentifier', 'CarIndex', 'FrontWing', 'RearWing', 'OnThrottle', 'OffThrottle', 'FrontCamber', 'RearCamber', 'FrontToe', 'RearToe', 'FrontSuspension', 'RearSuspension', 'FrontAntiRollBar', 'RearAntiRollBar', 'FrontSuspensionHeight', 'RearSuspensionHeight', 'BrakePressure', 'BrakeBias', 'RearLeftTyrePressure', 'RearRightTyrePressure', 'FrontLeftTyrePressure', 'FrontRightTyrePressure', 'Ballast', 'FuelLoad'] 
    - Status    :   ['FrameIdentifier', 'CarIndex', 'FuelInTank', 'FuelCapacity', 'FuelRemainingLaps', 'ActualTyreCompound', 'VisualTyreCompound', 'TyresAgeLaps', 'VehicleFIAFlags', 'ERSStoreEnergy', 'ERSDeployMode', 'ERSHarvestedThisLapMGUK', 'ERSHarvestedThisLapMGUH', 'ERSDeployedThisLap']
    - Telemetry :   ['FrameIdentifier', 'CarIndex', 'RLBrakeTemperature', 'RRBrakeTemperature', 'FLBrakeTemperature', 'FRBrakeTemperature', 'RLTyreSurfaceTemperature', 'RRTyreSurfaceTemperature', 'FLTyreSurfaceTemperature', 'FRTyreSurfaceTemperature', 'RLTyreInnerTemperature', 'RRTyreInnerTemperature', 'FLTyreInnerTemperature', 'FRTyreInnerTemperature', 'EngineTemperature', 'RLTyrePressure', 'RRTyrePressure', 'FLTyrePressure', 'FRTyrePressure', 'Speed', 'Throttle', 'Brake', 'Gear', 'EngineRPM', 'DRS']
    
    Inputs:
    - idx       :   int
        Car index we wanto to extract (default=19 because 19 is the car we are driving)

    Returns:
    - damage    :   pd.DataFrame
    - history   :   pd.DataFrame
    - lap       :   pd.DataFrame
    - motion    :   pd.DataFrame
    - session   :   pd.DataFrame
    - setup     :   pd.DataFrame
    - status    :   pd.DataFrame
    - telemetry :   pd.DataFrame
        List mapping lap number to frame number

    Examples:
    --------
    >>> extract_data(car_number) # car_number in range [0,19] (or [0,21] if my team active)
    
    """
    
    damage = pd.read_csv(os.path.join(path, 'Damage.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    damage = damage.loc[damage['CarIndex']==idx,['FrameIdentifier','CarIndex','TyresWearRL','TyresWearRR','TyresWearFL','TyresWearFR','TyresDamageRL','TyresDamageRR','TyresDamageFL','TyresDamageFR']]
    
    history = pd.read_csv(os.path.join(path, 'History.csv'), low_memory=False).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    history = history.loc[history['CarIndex']==idx].drop(['PacketFormat','GameMajorVersion','GameMinorVersion','PacketVersion','PacketId','SessionUID','SessionTime','PlayerCarIndex','SecondaryPlayerCarIndex'], axis=1)
    for column in list(history.columns):
        if history[column].isnull().values.all():
            history.drop(column, axis=1, inplace=True)

    lap = pd.read_csv(os.path.join(path, 'Lap.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    lap = lap.loc[lap['CarIndex']==idx,['FrameIdentifier','CarIndex','LastLapTimeInMS','CurrentLapTimeInMS','Sector1TimeInMS','Sector2TimeInMS','LapDistance','TotalDistance','CurrentLapNum','Sector','PitStopShouldServePen','DriverStatus']]

    motion = pd.read_csv(os.path.join(path, 'Motion.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    motion = motion.loc[motion['CarIndex']==idx, ['FrameIdentifier','CarIndex','WorldPositionX','WorldPositionY','WorldPositionZ','RLWheelSlip','RRWheelSlip','FLWheelSlip','FRWheelSlip','Pitch','Roll']]

    session = pd.read_csv(os.path.join(path, 'Session.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier'], keep='last').drop(['PacketFormat','GameMajorVersion','GameMinorVersion','PacketVersion','PacketId','SessionUID','SessionTime','PlayerCarIndex','SecondaryPlayerCarIndex','PitSpeedLimit','GamePaused','IsSpectating','SpectatorCarIndex','SliProNativeSupport','NetworkGame','AIDifficulty','SeasonLinkIdentifier','WeekendLinkIdentifier','SessionLinkIdentifier','SteeringAssist','BrakingAssist','GearboxAssist','PitAssist','PitReleaseAssist','ERSAssist','DRSAssist','DynamicRacingLine','DynamicRacingLineType'], axis=1)
    for column in list(session.columns):
        if session[column].isnull().values.all():
            session.drop(column, axis=1, inplace=True)

    setup = pd.read_csv(os.path.join(path, 'Setup.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    setup = setup.loc[setup['CarIndex']==idx].drop(['PacketFormat','GameMajorVersion','GameMinorVersion','PacketVersion','PacketId','SessionUID','SessionTime','PlayerCarIndex','SecondaryPlayerCarIndex'], axis=1)
    
    status = pd.read_csv(os.path.join(path, 'Status.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    status = status.loc[status['CarIndex'] == idx, ['FrameIdentifier','CarIndex','FuelInTank','FuelCapacity','FuelRemainingLaps','ActualTyreCompound','VisualTyreCompound','TyresAgeLaps','VehicleFIAFlags','ERSStoreEnergy','ERSDeployMode','ERSHarvestedThisLapMGUK','ERSHarvestedThisLapMGUH','ERSDeployedThisLap']]

    telemetry = pd.read_csv(os.path.join(path, 'Telemetry.csv')).replace('-', np.nan).drop_duplicates(subset=['FrameIdentifier','CarIndex'], keep='last')
    telemetry = telemetry.loc[telemetry['CarIndex'] == idx].drop(['PacketFormat','GameMajorVersion','GameMinorVersion','PacketVersion','PacketId','SessionUID','SessionTime','PlayerCarIndex','SecondaryPlayerCarIndex','Steer','Clutch','RevLightsPercent','RevLightsBitValue','RLSurfaceType','RRSurfaceType','FLSurfaceType','FRSurfaceType','MFD','MFDSecondaryPlayer','SuggestedGear'], axis=1, )
    
    return damage, history, lap, motion, session, setup, status, telemetry#, int(min_frame), int(max_frame), lap_frames
        

if __name__ == "__main__":
    log.warning("This module is not intended to be used as a standalone script. Run 'python main.py' instead.")
    sys.exit(1)
    