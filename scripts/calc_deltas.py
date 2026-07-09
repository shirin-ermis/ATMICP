import numpy as np
import xarray as xr
import pandas as pd
import matplotlib.pyplot as plt
from mystatsfunctions import OLSE,LMoments
import sys
import pathlib
from fair import *
from fair import return_empty_emissions, run_FaIR
import argparse

# definitions
AOPP_BASE_PATH = '/gf5/predict/AWH019_ERMIS_ATMICP/DATA/'
DELTA_PATH = f'{AOPP_BASE_PATH}/postproc/deltas/'

parser = argparse.ArgumentParser()
parser.add_argument(
    "--month",
    type=int,
    nargs="+",
    required=True
)
parser.add_argument("--var", required=True)
parser.add_argument("--start_year", type=int)
parser.add_argument("--end_year", type=int)
args = parser.parse_args()
PERTURB_MONTH = args.month # month to create delta for
VAR = args.var # variable to create delta for
START_YEAR = args.start_year if args.start_year is not None else 1979 # start year for regression
END_YEAR = args.end_year # end year for regression

def interpolate_to_model_grid(ds, var):

    # load reference grid and pressure at model levels
    model_level_p = pd.read_csv('/home/e/ermis/Irene-damages/model_to_pressure_levels.csv')['ph [hPa]'].values[::-1][:137] # half levels pressure 
    ref_ds = xr.open_dataset(f'{AOPP_BASE_PATH}/postproc/deltas/aux/{var}_reg_ref.grb2')
    
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

def get_erf():

    ## ERF components from AR6
    erf_ar6 = pd.read_csv('{}source/ancil/AR6_ERF_1750-2019.csv'.format(AOPP_BASE_PATH),index_col=0)
    erf_ar6.loc[:,'ghg'] = erf_ar6.loc[:,'total_anthropogenic'] - erf_ar6.loc[:,'aerosol']
    
    ### extend ERF to 2022
    ssp245_erf = pd.read_csv('{}source/ancil/ERF_ssp245_1750-2500.csv'.format(AOPP_BASE_PATH),index_col=0)
    ssp245_erf['aerosol'] = ssp245_erf.loc[:,'aerosol-radiation_interactions'] + ssp245_erf.loc[:,'aerosol-cloud_interactions']
    ssp245_erf.loc[:,'ghg'] = ssp245_erf.loc[:,'total_anthropogenic'] - ssp245_erf.loc[:,'aerosol']
    
    for year in [2020, 2021, 2022]: # not using end_year here, why?
        erf_ar6.loc[year] = ssp245_erf.loc[year] * erf_ar6.loc[year-1] / ssp245_erf.loc[year-1]

    return erf_ar6

def get_AWI():

    end_year = 2022 # fixed by HC5
    HC5 = get_HC5()
    erf = get_erf()

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

    # NOTE I could have one AWI that is longer that I use for the regression against ERA5 
    # and another that ends in 2022 for the regression against HC5. Need to implement later

    return AWI

if __name__ == "__main__":
    
    assert END_YEAR<=2022, "End year must be less than or equal to 2022, HC5 limited to 2022"

    print("### Importing data ###")
    
    # Load ERA5 data
    era5_var  = xr.open_dataset(f'{AOPP_BASE_PATH}/ERA5/{VAR}_monthly/{VAR}_mon_ERA5_0.25x0.25_197901-202512.nc').rename(
        {'valid_time': 'time', 'pressure_level': 'level'}
    )
    sh_var = {'q': False, 't': True, 'd': True,
              'vo': True, 'u': False, 'v': False}[VAR] # is this variable on the spherical harmonic grid?

    # Anthropogenic warming index
    awi = get_AWI()

    # Select only the specified month
    months = era5_var['time'].dt.month

    era5_var = era5_var.chunk({"time": -1}) # massive speedup!
    
    for month in PERTURB_MONTH:
        
        var_years = era5_var.sel(time=months.isin([month])).groupby('time.year').mean(dim='time').sel(year=slice(START_YEAR, END_YEAR)) # select the specified month and average each year

        print(f"### Regressing using data from {START_YEAR} to {END_YEAR} ###")
        
        # Interpolate variable
        timeslices = [x for x in np.arange(START_YEAR,END_YEAR+1,1)] 
        X = np.array([awi.loc[timeslice] for timeslice in timeslices])
        X = X[:,None,None,None]
        Y = var_years[VAR].squeeze().values
        olsreg = OLSE.simple( Y = Y )

        # create objects for computation
        olsreg.X = np.ma.array(X, mask=olsreg._mask)

        w = olsreg.W

        x = olsreg.X
        y = olsreg.Y
        olsreg.fit( X = X )

        # compute estimated attributable warming over 1850-1900 to endyear period
        awi_change = awi.loc[END_YEAR] - awi.loc[1850:1900].mean()
        var3d_out = olsreg.b1 * awi_change
        var3d_err = olsreg.err_b1 * awi_change # standard error of the delta (slope error scaled by same AWI change)

        # create DataArray objects
        var3d_out = xr.zeros_like(var_years[VAR].isel(year=-1).squeeze()) + var3d_out
        var3d_err = xr.zeros_like(var_years[VAR].isel(year=-1).squeeze()) + var3d_err

        print("### Regridding and saving ###")
        print(var3d_out)

        # Interpolate and save as nc file
        var_interp = interpolate_to_model_grid(var3d_out, var=VAR).to_netcdf(f'{DELTA_PATH}/{VAR}_{month}_delta_ERA5_{START_YEAR}-{END_YEAR}.nc')

        # Interpolate and save standard errors on the same model grid (netcdf only, no spherical harmonics)
        interpolate_to_model_grid(var3d_err, var=VAR).to_netcdf(f'{DELTA_PATH}/{VAR}_{month}_delta_stderr_ERA5_{START_YEAR}-{END_YEAR}.nc')