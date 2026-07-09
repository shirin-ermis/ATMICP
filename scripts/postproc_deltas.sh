#!/bin/bash
#SBATCH --job-name=delta-postproc         # Job name
#SBATCH --output=output_%A_%a.log         # Output log file (%A = job id, %a = array task id)
#SBATCH --error=error_%A_%a.log           # Error log file
#SBATCH --ntasks=1                        # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4                 # Number of CPU cores
#SBATCH --mem=80G                         # Memory allocation (adjust as needed)
#SBATCH --time=03:00:00                   # Max runtime (HH:MM:SS)
#SBATCH --partition=shared                # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL              # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)
#SBATCH --array=0-14                       # IMPORTANT: set to 0-(#VARS * #MONTHS - 1)

# Load necessary modules (if required)
source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
# conda env list
conda activate debug_forecast-icp

# Change variables and months here; the array runs all VAR x MONTH combinations.
# Remember to update the #SBATCH --array line above: 0-(#VARS * #MONTHS - 1)
VARS=(t q d vo sp)
MONTHS=(5 6 7)
START_YEAR=1979
END_YEAR=2021

# is variable in spherical harmonics in IFS?
declare -A on_spherical_harm
on_spherical_harm[q]=false
on_spherical_harm[t]=true
on_spherical_harm[d]=true
on_spherical_harm[vo]=true
on_spherical_harm[sp]=true

# directories
deltas_dir='/gf5/predict/AWH019_ERMIS_ATMICP/DATA/postproc/deltas'

# map array task id -> (VAR, month): task id = var_index * #MONTHS + month_index
NMONTHS=${#MONTHS[@]}
NCOMBOS=$(( ${#VARS[@]} * NMONTHS ))

if [[ -z "$SLURM_ARRAY_TASK_ID" ]]; then
    echo "ERROR: SLURM_ARRAY_TASK_ID not set. Submit as an array job, e.g.:"
    echo "  sbatch --array=0-$(( NCOMBOS - 1 )) postproc_deltas.sh"
    exit 1
fi

if (( SLURM_ARRAY_TASK_ID >= NCOMBOS )); then
    echo "Task id $SLURM_ARRAY_TASK_ID out of range (only $NCOMBOS combinations), nothing to do."
    exit 0
fi

VAR=${VARS[$(( SLURM_ARRAY_TASK_ID / NMONTHS ))]}
month=${MONTHS[$(( SLURM_ARRAY_TASK_ID % NMONTHS ))]}

echo "Task $SLURM_ARRAY_TASK_ID: postprocessing $VAR delta for month $month, spherical harmonics: ${on_spherical_harm[$VAR]}"

# calculate deltas from monthly means
python calc_deltas.py --month "$month" --var "$VAR" --start_year "$START_YEAR" --end_year "$END_YEAR" # calculate deltas for the month of perturbation

# name of delta file
delta_file="${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.nc"

# per-task temp file names so concurrent array tasks don't clobber each other
tmp="tmp_${VAR}_${month}"
donor="donor_${VAR}_${month}"

if [[ "${on_spherical_harm[$VAR]}" == "false" ]]; then # for variables on regular grid

    # deal with missing values
    cdo setmisstoc,0 ${deltas_dir}/${delta_file} ${deltas_dir}/${tmp}.nc
    # cp ${deltas_dir}/${delta_file} ${deltas_dir}/${tmp}.nc # if missing values treatment not needed

    # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
    cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc ${deltas_dir}/${donor}.nc
    ncrename -d lev,level ${deltas_dir}/${donor}.nc # rename dimension
    ncrename -v lev,level ${deltas_dir}/${donor}.nc # rename variable
    ncks -A -v level,hyam,hybm,hyai,hybi ${deltas_dir}/${donor}.nc ${deltas_dir}/${tmp}.nc

    # Convert to grib2
    cdo -f grb2 copy ${deltas_dir}/${tmp}.nc ${deltas_dir}/${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2

    # Clean up
    rm ${deltas_dir}/${tmp}.nc
    rm ${deltas_dir}/${donor}.nc

else

    cp ${deltas_dir}/${delta_file} ${deltas_dir}/${tmp}.nc

    if [[ "$VAR" != "sp" ]]; then
        # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
        cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc ${deltas_dir}/${donor}.nc
        ncrename -d lev,level ${deltas_dir}/${donor}.nc # rename dimension
        ncrename -v lev,level ${deltas_dir}/${donor}.nc # rename variable
        ncks -A -v level,hyam,hybm,hyai,hybi ${deltas_dir}/${donor}.nc ${deltas_dir}/${tmp}.nc
        rm ${deltas_dir}/${donor}.nc
    fi

    # Convert file to grib in spherical coordinates (sp stays single-level)
    cdo setmisstoc,0 ${deltas_dir}/${tmp}.nc ${deltas_dir}/${tmp}_tmp.grb2
    cdo -f grb2 gp2spl ${deltas_dir}/${tmp}_tmp.grb2 ${deltas_dir}/${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2

    # Clean up
    rm ${deltas_dir}/${tmp}_tmp.grb2
    rm ${deltas_dir}/${tmp}.nc
fi
