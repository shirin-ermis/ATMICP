#
# Data class
#
import xarray as xr
import glob
import os
import warnings
import babet as bb
from moarpalettes import get_palette
import dask


# Experiment sets that get_ifs_data knows how to load.
#
# 'inidates' is what inidates=None resolves to for that set: an explicit tuple
# loads exactly those dates, None falls back to globbing every inidate on disk.
# 'expver' maps a climate onto its experiment ids, 'perturbation' labels each
# experiment id with the perturbation it applies.
RUN_SETS = {
    # The iterated runs on the three fixed initialisation dates.
    'iterated': {
        'inidates': ('2021-06-18', '2021-06-22', '2021-06-26'),
        'expver': {'pi':   ['b2vj', 'b2vr', 'b2vl', 'b2vo'],
                   'curr': ['b2ut'],
                   'incr': ['b2vk', 'b2vq', 'b2vm', 'b2vn']},
        'perturbation': {'b2ut': 'none',            # actual climate

                         'b2vj': 'iterated',        # preindustrial
                         'b2vr': 'iterated_short',
                         'b2vl': 'tq',
                         'b2vo': 'ocean',

                         'b2vk': 'iterated',        # future
                         'b2vq': 'iterated_short',
                         'b2vm': 'tq',
                         'b2vn': 'ocean'},
    },
    # The set this function used before the iterated runs existed.
    'legacy': {
        'inidates': None,
        'expver': {'pi':   ['b2us', 'b2uu', 'b2ve', 'b2vc'],
                   'curr': ['b2ut'],
                   'incr': ['b2v0', 'b2v1', 'b2vb', 'b2vd']},
        'perturbation': {'b2ut': 'none',            # actual climate

                         'b2us': 'tq',              # preindustrial
                         'b2uu': 'progn_vars',
                         'b2ve': 'tqdvo',
                         'b2vc': 'dvo',

                         'b2v0': 'tq',              # future
                         'b2v1': 'progn_vars',
                         'b2vb': 'tqdvo',
                         'b2vd': 'dvo'},
    },
}

# Hourly ERA5 single-level fields (t2m, tcwv) over the US025 domain, written by
# scripts/era5_download_sfc_hourly.py
ERA5_SFC_PATH = ('/gf5/predict/AWH019_ERMIS_ATMICP/DATA/ERA5/'
                 '{var}_hourly/{var}_hourly_ERA5_0.25x0.25_202106.nc')


class Data:
    """A data class for ATMICP

    Parameters
    ----------

    value: numeric, optional
        an example paramter

    """

    def __init__(self, value=44):
        self.value = value

    def get_ifs_data(
            cf_option=['cf', 'pf'],
            exp_option=['pi', 'curr', 'incr'],
            res='US025',
            levtype='sfc',
            inidates=None,
            runs='iterated'
            ):

        """Get IFS data

        Experiments that have not been retrieved yet are skipped with a warning
        rather than raising, so a partially downloaded run set still loads.

        Inputs
        ------
        exp_option: list of str
            List of experiment options to load. Options are:
            - 'pi' : pre-industrial
            - 'curr' : current climate
            - 'incr' : increased greenhouse gases climate
        cf_option: list of str
            List of 'cf' and 'pf' option
        res: str
            Resolution and area string, e.g. 'US025', 'GLO100'
        levtype: str
            'sfc' or 'pl'
        inidates: list of str, optional
            Initialisation dates to load, as 'YYYY-MM-DD'. Defaults to whatever
            the run set specifies: the three fixed dates for 'iterated', and
            every inidate on disk for 'legacy'.
        runs: str
            Which experiment set to load, one of RUN_SETS ('iterated', 'legacy')

        Returns
        -------
        xarray.Dataset
            IFS data from iterative runs

        """

        # Exception handling
        if res not in ['US025', 'GLO100']:
            raise ValueError("res must be one of ['US025', 'GLO100']")
        if levtype not in ['sfc', 'pl']:
            raise ValueError("levtype must be one of ['sfc', 'pl']")

        if not set(exp_option).issubset(set(['pi', 'curr', 'incr'])):
            raise ValueError("exp_option must be subset of ['pi', 'curr', 'incr']")
        if not set(cf_option).issubset(set(['cf', 'pf'])):
            raise ValueError("cf_option must be subset of ['cf', 'pf']")

        if res == 'US025' and levtype == 'pl':
            raise ValueError("res 'US025' only supports levtype 'sfc'")

        if runs not in RUN_SETS:
            raise ValueError(f"runs must be one of {sorted(RUN_SETS)}")

        run_set = RUN_SETS[runs]
        expver_dict = run_set['expver']
        perturb_dict = run_set['perturbation']

        # None means "use this run set's default", which is itself allowed to be
        # None for the legacy set (i.e. glob every inidate on disk)
        if inidates is None:
            inidates = run_set['inidates']

        base_dir = '/gf5/predict/AWH019_ERMIS_ATMICP/ITERATION/MED-R/EXP/{}/{}/{}/{}' # exp, res, levtype, cf

        variables = {'sfc': ['t2m', 'msl', 'tcwv'],
            'pl': ['t', 'z', 'q']}

        # collect per-climate datasets (each will have climate dim length 1)
        climate_dsets = []

        for exp in exp_option:
            # collect per-perturbation datasets for this climate
            perturb_dsets = []
            for expver in expver_dict[exp]:
                # collect files/variants that should map to 'number'
                number_dsets = []
                for c in cf_option:
                    dir_path = base_dir.format(exp, res, levtype, c)
                    paths = Data._inidate_paths(dir_path, expver, inidates)

                    # nothing retrieved for this expver/cf combination yet
                    if not paths:
                        continue

                    print(f"Loading {len(paths)} file(s) for {expver} ({c}) from {dir_path}", flush=True)
                    ds = xr.open_mfdataset(
                        paths,
                        engine='netcdf4',
                        preprocess=bb.data.Data.preproc_ds_v2
                    ).get(variables[levtype])

                    # give single-file/collection the scalar dims climate & perturbation
                    ds = ds.expand_dims(climate=[exp], perturbation=[perturb_dict[expver]])
                    number_dsets.append(ds)

                # experiment not downloaded yet: warn and carry on without it
                if not number_dsets:
                    warnings.warn(
                        f"No files found for {expver} ({exp}, {res}, {levtype}) "
                        f"on the requested inidates - skipping this experiment."
                    )
                    continue

                # concat the list of 'number' variants into the number dimension
                # (if cf_option has length 1 this will still be fine)
                perturb_ds = xr.concat(number_dsets, dim='number')
                perturb_dsets.append(perturb_ds)

            # every experiment for this climate is missing: drop the climate
            if not perturb_dsets:
                warnings.warn(f"No experiments found for climate '{exp}' - skipping it.")
                continue

            # concat all perturbations for THIS climate along 'perturbation'
            climate_ds = xr.concat(perturb_dsets, dim='perturbation')
            climate_dsets.append(climate_ds)

        if not climate_dsets:
            raise FileNotFoundError(
                f"No IFS files found at all for runs='{runs}', res='{res}', "
                f"levtype='{levtype}', inidates={inidates}"
            )

        # finally concat across climates
        ifs = xr.concat(climate_dsets, dim='climate')

        return ifs

    def _inidate_paths(dir_path, expver, inidates):
        """Existing files for `expver` in `dir_path`, for the given inidates.

        `inidates=None` globs every inidate on disk, which is how this function
        used to find its files. Otherwise only the named dates are considered,
        and any that are missing are warned about and left out.

        Parameters
        ----------
        dir_path: str
            Directory holding the '{expver}_{inidate}.nc' files
        expver: str
            Experiment id, e.g. 'b2vl'
        inidates: iterable of str or None
            Initialisation dates as 'YYYY-MM-DD'

        Returns
        -------
        list of str
            Sorted paths that exist; empty if none do.

        """
        if inidates is None:
            return sorted(glob.glob(os.path.join(dir_path, f'{expver}*.nc')))

        paths, missing = [], []
        for inidate in inidates:
            path = os.path.join(dir_path, f'{expver}_{inidate}.nc')
            (paths if os.path.exists(path) else missing).append(path)

        # only worth flagging a partial retrieval: an expver with nothing at all
        # is reported by the caller, which knows the climate it belongs to
        if missing and paths:
            warnings.warn(
                f"{expver}: missing inidates "
                f"{[os.path.basename(p) for p in missing]} in {dir_path}"
            )

        return paths

    def get_era5_sfc(var='t2m', path=None):
        """Get hourly ERA5 surface data over the US025 domain.

        Written by scripts/era5_download_sfc_hourly.py, on the same 0.25 degree
        grid and the same area (70/-150/30/-100) as the IFS retrievals, so it
        can be differenced against them without regridding.

        Parameters
        ----------
        var: str
            ERA5 short name, one of the variables the download script
            retrieves ('t2m', 'tcwv')
        path: str, optional
            Override the default file location

        Returns
        -------
        xarray.Dataset
            ERA5 data with 'time', 'latitude' and 'longitude' dimensions

        """
        path = ERA5_SFC_PATH.format(var=var) if path is None else path

        if not os.path.exists(path):
            raise FileNotFoundError(
                f"No ERA5 {var} file at {path}. Run "
                f"scripts/era5_download_sfc_hourly.py {var} (or submit "
                f"scripts/era5_download_sfc_hourly.sh) to retrieve it."
            )

        era5 = xr.open_dataset(path)

        if 'valid_time' in era5.dims:
            era5 = era5.rename({'valid_time': 'time'})

        # scalar leftovers from the CDS request that get in the way of arithmetic
        era5 = era5.drop_vars(['expver', 'number'], errors='ignore')

        return era5

    def get_lsm(res='US025'):
        """Get land-sea mask

        Parameters
        ----------
        res: str
            Resolution string, e.g. 'US025', 'GLO100'
        
        Returns
        -------
        xarray.DataArray
            Land-sea mask

        """

        if res not in ['US025', 'GLO100']:
            raise ValueError("res must be one of ['US025', 'GLO100']")
        elif res == 'US025':
            raise ValueError("LSM not yet available for US025 resolution")
        elif res == 'GLO100':
            lsm_dir = '/gf5/predict/AWH019_ERMIS_ATMICP/ITERATION/ifs_lsm_{}.nc'
            lsm_path = lsm_dir.format(res)
            lsm = xr.open_dataset(lsm_path).lsm.squeeze('time') 
        
        return lsm

