import xarray as xr
import os
import babet as bb
from moarpalettes import get_palette

class Constants:
    """Constants for ATMICP

    Parameters
    ----------

    """
    pnw = [-123, -119, 45, 52] # lon min, lon max, lat min, lat max
    west_coast = [-150, -100, 30, 70]
    palette = get_palette.Petroff6().to_sn_palette()

    def __init__(self, value=44):
        self.value = value
