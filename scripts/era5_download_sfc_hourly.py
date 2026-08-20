"""Retrieve hourly ERA5 single-level fields over the US025 domain.

    python era5_download_sfc.py [var ...]

with `var` one of the keys of VARIABLES ('t2m', 'tcwv'); defaults to all of
them. Files land where atmicp.Data.get_era5_sfc expects them, on the same grid
and area as the IFS retrievals so they difference without regridding.
"""
import sys
import os

import cdsapi

# short name -> CDS long name
VARIABLES = {
    # 't2m': '2m_temperature',
    'tcwv': 'total_column_water_vapour',
}

BASEDIR = '/gf5/predict/AWH019_ERMIS_ATMICP/DATA/ERA5'

client = cdsapi.Client()

for var in (sys.argv[1:] or list(VARIABLES)):
    if var not in VARIABLES:
        raise SystemExit(f"unknown variable '{var}', expected one of {sorted(VARIABLES)}")

    savedir = f'{BASEDIR}/{var}_hourly/'
    os.makedirs(savedir, exist_ok=True)

    filename = f'{savedir}{var}_hourly_ERA5_0.25x0.25_202106.nc'
    if os.path.exists(filename):
        print(f'{filename} exists already - skipping', flush=True)
        continue

    dataset = "reanalysis-era5-single-levels"
    request = {
        "product_type": ["reanalysis"],
        "variable": [VARIABLES[var]],
        "year": ["2021"],
        "month": ["06"],
        "day": [f"{day:02d}" for day in range(1, 31)],
        "time": [f"{hour:02d}:00" for hour in range(24)], # hourly
        "area": [70, -150, 30, -100], # same domain as the US025 IFS retrievals
        "grid": [0.25, 0.25], # same grid, so no regridding before differencing
        "data_format": "netcdf",
        "download_format": "unarchived"
    }

    print(f'retrieving {var} to {filename}', flush=True)
    client.retrieve(dataset, request, filename)
