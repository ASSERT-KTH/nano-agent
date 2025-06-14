# Building this apptainer requires >20GB of space to finish building, so we build it in a larger directory.

# 1) give Apptainer a roomy temp directory (PROJECT_DIR points to a larger directory)
export APPTAINER_TMPDIR="$PROJECT_DIR/appt_tmp"
mkdir -p "$APPTAINER_TMPDIR"

# 2) build directly into the project area
apptainer build nano.sif scripts/container.def  

# 3) clean up
rm -rf "$APPTAINER_TMPDIR"
