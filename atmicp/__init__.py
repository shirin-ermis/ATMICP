"""ATMICP is is a package to help with analysing atmospheric initial condition perturbations 
for forecast-based attribution.

"""
# Import version info
from .version_info import VERSION_INT, VERSION  # noqa

# Import main classes
from .data import Data    # noqa
from .constants import Constants  # noqa

# Shared figure style, used as atmicp.style.<...> in the notebooks
from . import style  # noqa
