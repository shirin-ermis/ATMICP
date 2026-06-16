#!/bin/bash
#SBATCH --job-name=deltad6             # Job name
#SBATCH --output=output.log           # Output log file
#SBATCH --error=error.log             # Error log file
#SBATCH --ntasks=1                    # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4             # Number of CPU cores
#SBATCH --mem=80G                     # Memory allocation (adjust as needed)
#SBATCH --time=03:00:00               # Max runtime (HH:MM:SS)
#SBATCH --partition=shared            # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL          # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)

# Load necessary modules (if required)
source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
# conda env list
conda activate debug_forecast-icp

# Change variable here
VAR='d' # True if interpolating q, False if interpolating t
MONTHS=(6)
START_YEAR=1979
END_YEAR=2021

# is variable in spherical harmonics in IFS?
declare -A on_spherical_harm
on_spherical_harm[q]=false
on_spherical_harm[t]=true
on_spherical_harm[d]=true
on_spherical_harm[vo]=true

# directories
deltas_dir='/gf5/predict/AWH019_ERMIS_ATMICP/DATA/postproc/deltas'

if [[ "${on_spherical_harm[$VAR]}" == "false" ]]; then # for variables on regular grid
    echo "Running delta postprocessing for $VAR, spherical harmonics: ${on_spherical_harm[$VAR]}"

    for month in "${MONTHS[@]}"; do

        # calculate deltas from monthly means
        echo "Calculating $VAR delta for month $month"
        python calc_deltas.py --month "$month" --var "$VAR" --start_year "$START_YEAR" --end_year "$END_YEAR" # calculate deltas for the month of perturbation

        # name of delta file
        delta_file="${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.nc"

        # deal with missing values
        cdo setmisstoc,0 ${deltas_dir}/${delta_file} ${deltas_dir}/tmp.nc
        # cp ${deltas_dir}/${delta_file} ${deltas_dir}/tmp.nc # if missing values treatment not needed

        # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
        cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc ${deltas_dir}/donor_q.nc
        ncrename -d lev,level ${deltas_dir}/donor_q.nc # rename dimension
        ncrename -v lev,level ${deltas_dir}/donor_q.nc # rename variable
        ncks -A -v level,hyam,hybm,hyai,hybi ${deltas_dir}/donor_q.nc ${deltas_dir}/tmp.nc

        # Convert to grib2
        cdo -f grb2 copy ${deltas_dir}/tmp.nc ${deltas_dir}/${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2

        # Clean up
        rm ${deltas_dir}/tmp.nc
    done

else
    echo "Running delta postprocessing for $VAR, spherical harmonics: ${on_spherical_harm[$VAR]}"

    # calculate deltas from monthly means
    for month in "${MONTHS[@]}"; do
        # python calc_deltas.py --month "$month" --var "$VAR" --start_year "$START_YEAR" --end_year "$END_YEAR" # calculate deltas for the month of perturbation

        cp ${deltas_dir}/${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.nc ${deltas_dir}/tmp_${VAR}.nc

        # Add hyai, hybi, hyam, hybm variables from a donor file, add metadata to the level dimension
        cp /gf5/predict/AWH019_ERMIS_ATMICP/test_ATMICP/TEMPBLOB_IC/upptemp_with_blob_sh.nc ${deltas_dir}/donor_${VAR}.nc
        ncrename -d lev,level ${deltas_dir}/donor_${VAR}.nc # rename dimension
        ncrename -v lev,level ${deltas_dir}/donor_${VAR}.nc # rename variable
        ncks -A -v level,hyam,hybm,hyai,hybi ${deltas_dir}/donor_${VAR}.nc ${deltas_dir}/tmp_${VAR}.nc

        # Convert file to grib in spherical coordinates
        cdo setmisstoc,0 ${deltas_dir}/tmp_${VAR}.nc ${deltas_dir}/tmp_${VAR}_tmp.grb2
        cdo -f grb2 gp2spl ${deltas_dir}/tmp_${VAR}_tmp.grb2 ${deltas_dir}/${VAR}_${month}_delta_ERA5_${START_YEAR}-${END_YEAR}.grb2
        
        # Clean up
        rm ${deltas_dir}/tmp_${VAR}_tmp.grb2
        rm ${deltas_dir}/tmp_${VAR}.nc
    done
fi

