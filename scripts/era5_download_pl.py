import cdsapi
import numpy as np
import glob
import xarray as xr
import os
import subprocess

var = 'd'
long_var = 'divergence'
savedir = f'/gf5/predict/AWH019_ERMIS_ATMICP/DATA/ERA5/{var}_monthly/' # make sure dir exists

filename = f'{savedir}{var}_mon_ERA5_0.25x0.25_197901-202512.nc'
dataset = "reanalysis-era5-pressure-levels-monthly-means"
request = {
    "product_type": ["monthly_averaged_reanalysis"],
    "variable": [long_var],
    "pressure_level": [ # all available pressure levels
        "1", "2", "3",
        "5", "7", "10",
        "20", "30", "50",
        "70", "100", "125",
        "150", "175", "200",
        "225", "250", "300",
        "350", "400", "450",
        "500", "550", "600",
        "650", "700", "750",
        "775", "800", "825",
        "850", "875", "900",
        "925", "950", "975",
        "1000"
    ],
    "year": [ # full satellite era
        "1979", "1980", "1981",
        "1982", "1983", "1984",
        "1985", "1986", "1987",
        "1988", "1989", "1990",
        "1991", "1992", "1993",
        "1994", "1995", "1996",
        "1997", "1998", "1999",
        "2000", "2001", "2002",
        "2003", "2004", "2005",
        "2006", "2007", "2008",
        "2009", "2010", "2011",
        "2012", "2013", "2014",
        "2015", "2016", "2017",
        "2018", "2019", "2020",
        "2021", "2022", "2023",
        "2024", "2025"
    ],
    "month": [ # all months
        "01", "02", "03",
        "04", "05", "06",
        "07", "08", "09",
        "10", "11", "12"
    ],
    "time": ["00:00"], # 00:00 is standard for monthly means
    "data_format": "netcdf", # makes request massive but oh well
    "download_format": "unarchived"
}

client = cdsapi.Client()
client.retrieve(dataset, request, filename)