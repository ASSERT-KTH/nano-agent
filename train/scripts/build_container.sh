# 1) give Apptainer a roomy temp directory
export APPTAINER_TMPDIR="$PROJECT_DIR/appt_tmp"
mkdir -p "$APPTAINER_TMPDIR"

# 2) build directly into the project area
apptainer build --fakeroot nano.sif scripts/container.def

# 3) clean up
rm -rf "$APPTAINER_TMPDIR"