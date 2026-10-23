#
# Met class
#
import numpy as np

EARTH_RADIUS = 6.371e6  # m


class Met:
    """Meteorological diagnostics for ATMICP"""

    def pressure_tendency(ps, u, v):
        """d(ln ps)/dt [1/s] from the divergence of the column-integrated wind,
        -1/ps * div(int_0^ps v dp).

        Inputs
        ------
        ps: xarray.DataArray
            Surface pressure in Pa
        u, v: xarray.DataArray
            Winds on pressure levels ('level' in hPa or Pa), with 'latitude' and
            'longitude' in degrees

        Returns
        -------
        xarray.DataArray
            Surface pressure tendency d(ln ps)/dt in 1/s
        """
        p = u.level * 100 if u.level.attrs.get('units') in ['hPa', 'millibar', 'millibars'] else u.level
        u = u.assign_coords(level=p).sortby('level')
        v = v.assign_coords(level=p).sortby('level')

        # integrate above ground only
        above = u.level <= ps
        U = u.where(above, 0).integrate('level')
        V = v.where(above, 0).integrate('level')

        # spherical divergence; 180/pi converts d/d(deg) to d/d(rad); NaN at the poles where cos(lat) = 0
        coslat = np.cos(np.deg2rad(U.latitude)).where(abs(U.latitude) < 90)
        div = (U.differentiate('longitude') + (V * coslat).differentiate('latitude')) \
            * (180 / np.pi) / (EARTH_RADIUS * coslat)

        return -div / ps
