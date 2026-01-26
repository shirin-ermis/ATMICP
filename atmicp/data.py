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

    def get_ifs_data(self, cf_option=['cf', 'pf'], exp_option=['pi', 'curr', 'incr']):
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
        
        Returns
        -------
        xarray.Dataset
            IFS data from iterative runs

        """

        base_dir = '/gf5/predict/AWH019_ERMIS_ATMICP/ITERATION/MED-R/EXP/{}/GLO025/sfc/{}'

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
                    dir_path = os.path.join(base_dir.format(exp, c), f'{expver}*.nc')
                    ds = xr.open_mfdataset(
                        dir_path,
                        engine='netcdf4',
                        preprocess=bb.data.Data.preproc_ds_v2
                    ).get(['t2m', 'msl', 'tcwv'])

                    # give single-file/collection the scalar dims climate & perturbation
                    ds = ds.expand_dims(climate=[exp], perturbation=[perturb_dict[expver]])
                    number_dsets.append(ds)

                # concat the list of 'number' variants into the number dimension
                perturb_ds = xr.concat(number_dsets, dim='number')
                perturb_dsets.append(perturb_ds)

            # concat all perturbations for one climate along 'perturbation'
            climate_ds = xr.concat(perturb_dsets, dim='perturbation')
            climate_dsets.append(climate_ds)

        # finally concat across climates
        ifs = xr.concat(climate_dsets, dim='climate')
        
        return ifs

