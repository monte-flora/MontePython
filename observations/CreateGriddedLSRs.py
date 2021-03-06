import numpy as np
import xarray as xr
import itertools

# Personal Imports 
import os
from os.path import join, exists
from wofs.util.basic_functions import get_key, personal_datetime, check_file_path, to_ordered_dict
from wofs.data.loadWWAs import load_reports, load_tornado_warning
from wofs.util import config
from machine_learning.main.run_ensemble_feature_extraction import run_parallel
from scipy.ndimage import maximum_filter
from skimage.measure import regionprops
get_time = personal_datetime( )

""" usage: stdbuf -oL python -u CreateGriddedLSRs.py 2 > & log & """
###########################################################################
# Label forecast storm objects valid at a single time 
###########################################################################
debug = False 
###########################################

def points_to_grid(xy_pair, nx):
    """
    Convert points to gridded data
    """
    xy_pair = [ (x,y) for x,y in xy_pair if x < nx-1 and y < nx-1 and x > 0 and y > 0 ]
    gridded_lsr = np.zeros((nx, nx))
    for i, pair in enumerate(xy_pair):
        gridded_lsr[pair[0],pair[1]] = i

    return gridded_lsr

def worker(date, time):
    '''
    Function for multiprocessing
    '''
    names = ['severe_hail', 'tornado', 'severe_wind']
    _, adjusted_date, time = get_time.initial_datetime( date_dir = str(date), time_dir = time)
    for duration in [30]:
        hail_xy, torn_xy, wind_xy, nx = load_reports( date, (adjusted_date, time), all_lsrs=False, forecast_length=duration, grid=True)
        gridded_lsr_set = [points_to_grid(xy_pair, nx) for xy_pair in (hail_xy, torn_xy, wind_xy)] 
        
    data = { }
    for pair in zip([0,5,10], ['3km', '15km', '30km']):    
        for i, name in enumerate(names):
            if pair[0] ==0:
                data[f'{name}_{pair[1]}'] = (['y', 'x'], gridded_lsr_set[i])
            else:
                data[f'{name}_{pair[1]}'] = (['y', 'x'], maximum_filter( gridded_lsr_set[i], pair[0]))

    ds = xr.Dataset(data) 
    fname = 'LSRs_%s-%s.nc' % (adjusted_date, time)
    out_path = join( config.LSR_SAVE_PATH, date )

    if debug:
        ds.to_netcdf(fname)
    else:
        fname = join(out_path, fname)
        print (fname)
        os.makedirs(os.path.dirname(fname), exist_ok=True)
        ds.to_netcdf( fname )
        ds.close( )

if debug: 
    print("\n Working in DEBUG MODE...\n") 
    date = '20180501'; time = '0000'
    worker( date, time )

else:
    dates = config.ml_dates
    times = config.observation_times
    run_parallel(
            func = worker,
            nprocs_to_use = 0.4,
            iterator = itertools.product(dates, times)
            )






