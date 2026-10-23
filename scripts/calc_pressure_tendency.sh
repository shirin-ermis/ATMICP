#!/bin/bash
#SBATCH --job-name=ps-tendency            # Job name
#SBATCH --output=output_%j.log            # Output log file (%j = job id)
#SBATCH --error=error_%j.log              # Error log file
#SBATCH --ntasks=1                        # Number of tasks (usually 1 for Python)
#SBATCH --cpus-per-task=4                 # Number of CPU cores
#SBATCH --mem=80G                         # Memory allocation (adjust as needed)
#SBATCH --time=03:00:00                   # Max runtime (HH:MM:SS)
#SBATCH --partition=shared                # Partition/queue name (adjust for your system)
#SBATCH --mail-type=END,FAIL              # Notifications for job completion/failure
#SBATCH --mail-user=shirin.ermis@physics.ox.ac.uk    # Your email (optional)

# Load necessary modules (if required)
source /home/e/ermis/nobackups/miniforge3/etc/profile.d/conda.sh
conda activate atmicp

python calc_pressure_tendency.py
