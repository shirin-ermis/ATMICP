import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from mystatsfunctions import OLSE,LMoments
import sys
import pathlib
from fair import *
from fair import return_empty_emissions, run_FaIR

# definitions
AOPP_BASE_PATH = '/gf5/predict/AWH019_ERMIS_ATMICP/DATA/'
DELTA_PATH = f'{AOPP_BASE_PATH}/postproc/deltas/'


# delta script params -- script needs two inputs!
SEASONAL = False # is this a seasonal forecast
PERTURB_MONTH = [int(x) for x in sys.argv[1]] # month of perturbation
VAR = sys.argv[2] # variable to calculate delta for

def interpolate_to_model_grid(ds, sh=False):

    # load reference grid and pressure at model levels
    model_level_p = pd.read_csv('/home/e/ermis/Irene-damages/model_to_pressure_levels.csv')['ph [hPa]'].values[::-1][:137] # half levels pressure 
    if sh: 
        ref_ds = xr.open_dataset('/gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/temperature_blob_model_grid.grb2')
    else:
        ref_ds = xr.open_dataset('/home/e/ermis/test_ATMICP/grid_q.nc', engine='netcdf4')
    
    # horizontal interpolation
    tmp = ds.interp(latitude=ref_ds.latitude, longitude=ref_ds.longitude, method='linear')

    # vertical interpolation
    tmp = tmp.interp(level=model_level_p, method='linear', kwargs={'fill_value': 'extrapolate'})

    # add output into frame of reference dataset
    target = xr.zeros_like(ref_ds) + tmp.values[::-1]

    return target.fillna(0)

def get_HC5():

    ## HadCRUT5
    HC5 = xr.open_dataset('{}source/ancil/HadCRUT.5.0.2.0.analysis.summary_series.global.annual.nc'.format(AOPP_BASE_PATH))
    HC5 = HC5.tas_mean.to_pandas()
    HC5.index = HC5.index.year

    return HC5

def get_erf(end_year=2022):

    ## ERF components from AR6
    erf_ar6 = pd.read_csv('{}source/ancil/AR6_ERF_1750-2019.csv'.format(AOPP_BASE_PATH),index_col=0)
    erf_ar6.loc[:,'ghg'] = erf_ar6.loc[:,'total_anthropogenic'] - erf_ar6.loc[:,'aerosol']
    
    ### extend ERF to 2022
    ssp245_erf = pd.read_csv('{}source/ancil/ERF_ssp245_1750-2500.csv'.format(AOPP_BASE_PATH),index_col=0)
    ssp245_erf['aerosol'] = ssp245_erf.loc[:,'aerosol-radiation_interactions'] + ssp245_erf.loc[:,'aerosol-cloud_interactions']
    ssp245_erf.loc[:,'ghg'] = ssp245_erf.loc[:,'total_anthropogenic'] - ssp245_erf.loc[:,'aerosol']
    
    # for year in range(2020,end_year+1): 
    for year in [2020, 2021, 2022]: # not using end_year here, why?
        erf_ar6.loc[year] = ssp245_erf.loc[year] * erf_ar6.loc[year-1] / ssp245_erf.loc[year-1]

    return erf_ar6

def get_AWI(end_year=2022):

    HC5 = get_HC5()
    erf = get_erf(end_year=end_year)

    ## ant / nat FaIR run
    fair_erf = pd.DataFrame(index=erf.index,columns=pd.MultiIndex.from_product([['ant','aer','nat'],['forcing']]),
                            data=pd.concat([erf.loc[:,'ghg'],erf.loc[:,'aerosol'],
                                            erf.loc[:,'total_natural']], axis=1).values)
    fair_emms = return_empty_emissions(start_year=1750,end_year=end_year,scen_names=['ant','aer','nat'])
    fair_temps = run_FaIR(emissions_in=fair_emms,forcing_in=fair_erf)['T'].loc[1850:]

    ## regress HadCRUT5 onto FaIR temperature output & define anthropogenic warming index
    X = np.column_stack([np.ones(fair_temps.loc[:end_year].index.size),fair_temps.loc[:end_year]])
    Y = HC5.loc[1850:end_year].values[:,None]
    mlr = OLSE.multiple(Y)
    mlr.fit(X)
    AWI = ( mlr.B[1]*fair_temps.aer + mlr.B[2]*fair_temps.ant ).default

    return AWI

if __name__ == "__main__":
    
    print("### Importing data ###")
    
    # Load ERA5 data
    era5_var  = xr.open_dataset(f'{AOPP_BASE_PATH}/ERA5/{VAR}_monthly/{VAR}_mon_ERA5_0.25x0.25_197901-202512.nc').rename(
        {'valid_time': 'time'}
    )
    sh_var = {'q': False, 't': True, 'd': True,
              'vo': True, 'u': False, 'v': False}[VAR] # is this variable on the spherical harmonic grid?

    # Anthropogenic warming index
    awi = get_AWI()
    print(awi.shape)

    # Select only the specified month
    start_year = 1979
    end_year = 2023
    months = era5_var['time'].dt.month

    # if isinstance(PERTURB_MONTH, int):
    #     PERTURB_MONTH = [PERTURB_MONTH]
    #     print(f"### Calculating deltas for month {PERTURB_MONTH} ###")

    print(f"### Month type: {type(PERTURB_MONTH[0])} ###")
    for month in PERTURB_MONTH:
        var_years = era5_var.sel(time=months.isin([month])).groupby('time.year').mean(dim='time').sel(year=slice(start_year, 2022)) # select the specified month and average each year

        print(f"### Regressing using data from {start_year} to {end_year} ###")
        
        # Interpolate variable
        timeslices = [x for x in np.arange(start_year,end_year,1)] 
        X = np.array([awi.loc[timeslice] for timeslice in timeslices])
        X = X[:,None,None,None]
        Y = var_years[VAR].squeeze().values
        print(X.shape, Y.shape)
        olsreg = OLSE.simple( Y = Y )

        # create objects for computation
        olsreg.X = np.ma.array(X, mask=olsreg._mask)

        w = olsreg.W

        x = olsreg.X
        y = olsreg.Y
        olsreg.fit( X = X )

        # compute estimated attributable warming over 1850-1900 to 2011 period
        var3d_out = olsreg.b1 * (awi.loc[2011] - awi.loc[1850:1900].mean())

        # create DataArray object
        var3d_out = xr.zeros_like(var_years[VAR].isel(year=-1).squeeze()) + var3d_out
        
        print("### Regridding and saving ###")

        # Interpolate and save as nc file
        var_interp = interpolate_to_model_grid(var3d_out, sh=sh_var)#.to_netcdf(f'{DELTA_PATH}/{VAR}_interp_ERA5_{start_year}-{end_year}_month{month}.nc')