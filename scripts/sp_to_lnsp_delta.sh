#!/bin/bash
#SBATCH --job-name=sp-to-lnsp                # Job name
#SBATCH --output=output.log           # Output log file
#SBATCH --error=error.log             # Error log file
#SBATCH --ntasks=1                    # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4             # Number of CPU cores
#SBATCH --mem=80G                     # Memory allocation (adjust as needed)
#SBATCH --time=03:00:00               # Max runtime (HH:MM:SS)
#SBATCH --partition=shared            # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL          # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)

# Converts a surface pressure (sp) climate-signal delta in spherical harmonics
# (as produced by postproc_deltas.sh) into the corresponding log-surface-pressure
# (lnsp) delta, since IFS carries lnsp rather than sp as its spectral surface field.
#
# The conversion is nonlinear, so it is not just a log of the delta:
#   delta_lnsp = ln(sp_base + delta_sp) - ln(sp_base) = ln(sp_base + delta_sp) - lnsp_base
# sp_base/lnsp_base is the actual base-state field the delta will be added to,
# taken from the lnsp already present in the base initial condition (AN_inishml),
# which is at the same T1279 truncation as the deltas.
#
# The arithmetic is done in gridpoint space (sp2gpl) and transformed back to
# spectral (gp2spl) to match the storage convention of the other variable deltas.

source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
conda activate debug_forecast-icp

set -euo pipefail

MONTHS=(5 6 7)
START_YEAR=1979
END_YEAR=2021

deltas_dir='/gf5/predict/AWH019_ERMIS_ATMICP/DATA/postproc/deltas'
base_ic='/gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/AN_inishml' # source of the base-state lnsp field

workdir=$(mktemp -d "${deltas_dir}/tmp_sp2lnsp.XXXXXX")
trap 'rm -rf "$workdir"' EXIT

echo "Extracting base-state lnsp from $base_ic"
grib_copy -w shortName=lnsp "$base_ic" "${workdir}/lnsp_base_sh.grb2"
cdo -s -f grb2 sp2gpl "${workdir}/lnsp_base_sh.grb2" "${workdir}/lnsp_base_gp.grb2"
cdo -s -f grb2 exp "${workdir}/lnsp_base_gp.grb2" "${workdir}/sp_base_gp.grb2"

for month in "${MONTHS[@]}"; do
    echo "Converting sp -> lnsp delta for month $month"

    sp_delta="${deltas_dir}/sp_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2"
    lnsp_delta="${deltas_dir}/lnsp_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2"

    if [[ ! -f "$sp_delta" ]]; then
        echo "Missing $sp_delta, skipping" >&2
        continue
    fi

    # delta_sp (spectral) -> gridpoint, onto the same grid as sp_base/lnsp_base
    cdo -s -f grb2 sp2gpl "$sp_delta" "${workdir}/sp_delta_gp.grb2"

    # delta_lnsp = ln(sp_base + delta_sp) - lnsp_base, computed on the gridpoint fields
    cdo -s -f grb2 sub -ln -add "${workdir}/sp_base_gp.grb2" "${workdir}/sp_delta_gp.grb2" \
        "${workdir}/lnsp_base_gp.grb2" "${workdir}/lnsp_delta_gp.grb2"

    # back to spectral, at the same T1279 truncation as the other variable deltas
    cdo -s -f grb2 gp2spl "${workdir}/lnsp_delta_gp.grb2" "${workdir}/lnsp_delta_sh.grb2"

    # relabel as lnsp (the arithmetic chain above traces back to the lnsp fields,
    # so metadata should already read lnsp/152, but set it explicitly to be sure)
    grib_set -s shortName=lnsp,paramId=152 "${workdir}/lnsp_delta_sh.grb2" "$lnsp_delta"

    echo "Wrote $lnsp_delta"
    cdo -s infon "$lnsp_delta"

    rm -f "${workdir}/sp_delta_gp.grb2" "${workdir}/lnsp_delta_gp.grb2" "${workdir}/lnsp_delta_sh.grb2"
done
