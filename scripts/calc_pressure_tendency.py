import xarray as xr
import babet as bb
import atmicp

# definitions
AOPP_BASE_PATH = '/gf5/predict/AWH019_ERMIS_ATMICP/DATA/'
OUT_FILE = f'{AOPP_BASE_PATH}/postproc/pressure_tendency/ifs_pressure_tendency_GLO100.nc'
N_STEPS = 3  # first time steps after each inidate
G = 9.80665  # gravity, m/s2

if __name__ == "__main__":

    print("### Importing data ###")

    ifs_sfc = atmicp.Data.get_ifs_data(levtype='sfc', res='GLO100', variables=['t2m', 'msl'])
    ifs_pl = atmicp.Data.get_ifs_data(levtype='pl', res='GLO100', variables=['u', 'v'])
    height = xr.open_dataset(f'{AOPP_BASE_PATH}/ifs_geopotential_GLO100.nc').squeeze('time').z / G

    # first few (daily) pl time steps of each inidate; sfc is 3-hourly, so take it at the pl times
    ifs_pl = xr.concat([ifs_pl.sel(inidate=d, time=slice(d, None)).isel(time=slice(0, N_STEPS))
                        for d in ifs_pl.inidate.values], dim='inidate')
    ifs_sfc = ifs_sfc.sel(time=ifs_pl.time)

    # single chunk in level/lat/lon so the vertical integral and horizontal gradients stay within one chunk
    ifs_pl = ifs_pl.chunk({'level': -1, 'latitude': -1, 'longitude': -1})
    ps = bb.Met.sfc_pressure_from_mslp(ifs_sfc.t2m, ifs_sfc.msl, height).chunk({'latitude': -1, 'longitude': -1})

    # keep only experiments available on both sfc and pl
    ps, ifs_pl = xr.align(ps, ifs_pl, join='inner')
    print('perturbations:', ps.perturbation.values)

    print("### Calculating pressure tendencies ###")

    dlnpsdt = atmicp.Met.pressure_tendency(ps, ifs_pl.u, ifs_pl.v).rename('dlnpsdt')
    dlnpsdt.attrs = {'units': 's-1', 'long_name': 'surface pressure tendency d(ln ps)/dt'}

    print("### Saving ###")
    dlnpsdt.to_netcdf(OUT_FILE)
