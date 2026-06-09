#!/bin/bash
#SBATCH --job-name=erasp               # Job name
#SBATCH --output=output.log           # Output log file
#SBATCH --error=error.log             # Error log file
#SBATCH --ntasks=1                    # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4             # Number of CPU cores
#SBATCH --mem=48G                     # Memory allocation (adjust as needed)
#SBATCH --time=72:00:00               # Max runtime (HH:MM:SS)
#SBATCH --partition=shared            # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL          # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)

# Load necessary modules (if required)
source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
# conda env list
conda activate cdsapi

# Run your Python script
python era5_download_sfc.py