#
# Data class
#
import xarray as xr
import os
import babet as bb
from moarpalettes import get_palette

class Data:
    """A data class for ATMICP

    Parameters
    ----------

    value: numeric, optional
        an example paramter

    """

    def __init__(self, value=44):
        self.value = value

    def get_ifs_data(cf_option=['cf', 'pf'], exp_option=['pi', 'curr', 'incr'], res='US025', levtype='sfc'):
        """Get IFS data

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

        # perturb_option = ['q_and_t', 'progn_vars'] # TODO: build this in as argument 

        base_dir = '/gf5/predict/AWH019_ERMIS_ATMICP/ITERATION/MED-R/EXP/{}/{}/{}/{}' # exp, res, levtype, cf
        expver_dict = {'pi': ['b2us', 'b2uu'],
                        'curr': ['b2ut'],
                        'incr': ['b2v0', 'b2v1']}
        
        perturb_dict = {'b2us': 't+q',
                    'b2uu': 'progn_vars',
                    'b2ut': 'none',
                    'b2v0': 't+q',
                    'b2v1': 'progn_vars'}

        # collect per-climate datasets (each will have climate dim length 1)
        climate_dsets = []

        for exp in exp_option:
            # collect per-perturbation datasets for this climate
            perturb_dsets = []
            for expver in expver_dict[exp]:
                # collect files/variants that should map to 'number'
                number_dsets = []
                for c in cf_option:
                    dir_path = os.path.join(base_dir.format(exp, res, levtype, c), f'{expver}*.nc')
                    ds = xr.open_mfdataset(
                        dir_path,
                        engine='netcdf4',
                        preprocess=bb.data.Data.preproc_ds_v2
                    ).get(['t2m', 'msl', 'tcwv'])

                    # give single-file/collection the scalar dims climate & perturbation
                    ds = ds.expand_dims(climate=[exp], perturbation=[perturb_dict[expver]])
                    number_dsets.append(ds)

                # concat the list of 'number' variants into the number dimension
                # (if cf_option has length 1 this will still be fine)
                perturb_ds = xr.concat(number_dsets, dim='number')
                perturb_dsets.append(perturb_ds)

            # concat all perturbations for THIS climate along 'perturbation'
            climate_ds = xr.concat(perturb_dsets, dim='perturbation')
            climate_dsets.append(climate_ds)

        # finally concat across climates
        ifs = xr.concat(climate_dsets, dim='climate')
        
        return ifs

