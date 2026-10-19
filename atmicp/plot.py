"""Shared plotting helpers for the notebooks."""
import numpy as np
import cartopy.crs as ccrs
from cmcrameri import cm

from . import style


def plot_maps(da, col, proj=ccrs.PlateCarree(), col_wrap=4, cmap=cm.vik,
              vlim=None, title=None, size=1.3, aspect=2.0, **kwargs):
    """Facet map plot with coastlines, colour scale symmetric about zero.

    `vlim` defaults to the 99th percentile of |da|. PlateCarree is the default
    because other projections cost ~4 s a panel. `size` and `aspect` are one
    panel's height (in) and width/height ratio.
    """
    da = da.assign_coords(longitude=(((da.longitude + 180) % 360) - 180)).sortby('longitude')

    if vlim is None:
        vlim = float(np.nanpercentile(np.abs(da), 99))

    p = da.plot(col=col, col_wrap=col_wrap,
                transform=ccrs.PlateCarree(),
                subplot_kws={'projection': proj},
                cmap=cmap, vmin=-vlim, vmax=vlim, size=size, aspect=aspect,
                rasterized=True,  # keeps the vector PDF small
                **kwargs)

    for ax in p.axes.flat:
        ax.coastlines(resolution='110m', linewidth=0.5, color='k')
        ax.set_global()

    if title is not None:
        # fixed gap of ~1/3 in above the panels, whatever the number of rows
        nrow = int(np.ceil(da[col].size / col_wrap))
        p.fig.suptitle(title, y=1 + 0.35 / (nrow * size),
                       fontsize=style.scaled(style.FS_TITLE, p.fig))

    return p


def balanced_wrap(n, most=6):
    """Column count for `n` panels that avoids a last row holding one panel."""
    wrap = min(n, most)
    while wrap > 2 and n % wrap == 1:
        wrap -= 1
    return wrap
