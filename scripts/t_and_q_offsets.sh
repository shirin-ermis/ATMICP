#!/bin/bash
#SBATCH --job-name=q_and_t_delta      # Job name
#SBATCH --output=output.log           # Output log file
#SBATCH --error=error.log             # Error log file
#SBATCH --ntasks=1                    # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4             # Number of CPU cores
#SBATCH --mem=48G                     # Memory allocation (adjust as needed)
#SBATCH --time=03:00:00               # Max runtime (HH:MM:SS)
#SBATCH --partition=shared            # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL          # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)

# Load necessary modules (if required)
# eval "$(conda shell.bash hook)"
source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
conda env list
conda activate forecast-icp-3-7-12_new

# Run your Python script
var_q=True # True if interpolating q, False if interpolating t

if [ "$var_q" = True ]; then
    echo "Running q_offset.py"
    # python scripts/q_offset.py

    # -----------Convert file to grib ----------------
    # cdo setmisstoc,0 deltas/q_interp.nc deltas/tmp.nc
    cp deltas/q_interp_ERA5_1979-2023.nc deltas/tmp.nc

    # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
    cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc deltas/donor_q.nc
    ncrename -d lev,level deltas/donor_q.nc # rename dimension
    ncrename -v lev,level deltas/donor_q.nc # rename variable
    ncks -A -v level,hyam,hybm,hyai,hybi deltas/donor_q.nc deltas/tmp.nc

    # Convert to grib2
    cdo -f grb2 copy deltas/tmp.nc deltas/q_interp_ERA5_1979-2023.grb2
    rm deltas/tmp.nc
else
    # echo "Running t_offset.py"
    # python t_offset.py 
    cp deltas/t_interp_ERA5_1979-2023.nc deltas/tmp_t.nc

    # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
    cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc deltas/donor_q.nc
    ncrename -d lev,level donor_q.nc # rename dimension
    ncrename -v lev,level donor_q.nc # rename variable
    ncks -A -v level,hyam,hybm,hyai,hybi deltas/donor_q.nc deltas/tmp_t.nc

    # Convert file to grib in spherical coordinates
    cdo setmisstoc,0 deltas/tmp_t.nc deltas/tmp_t_tmp.grb2
    cdo -f grb2 gp2spl deltas/tmp_t_tmp.grb2 deltas/t_interp_sh_ERA5_1979-2023.grb2
    rm deltas/tmp_t_tmp.grb2
    rm deltas/tmp_t.nc
fi

