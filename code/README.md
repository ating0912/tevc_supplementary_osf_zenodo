# Research Code

This directory contains the Python, MATLAB, PowerShell, batch, JavaScript, and compatibility sources collected for the TEVC experiments and result reconstruction. `../manifest/code_inventory.csv` is the authoritative file inventory, and `../manifest/source_file_map.csv` maps packaged outputs to their producing workspace sources.

Third-party PlatEMO distributions are not relicensed here. Install PlatEMO v2.9.0 for the formal MATLAB R2020b baseline and PlatEMO v4.3 for compatibility/reference checks described in `../system/software_environment.md`.

The current package validators and manifest generators are in `../scripts/`. Historical analysis and package-construction programs remain here for provenance. In particular, `build_tevc_github_package.py` and `build_tevc_reproducibility_package.py` are intentionally disabled because they embed superseded pre-`20260811` file maps and README conclusions. See `../manifest/code_authority.csv` before reusing a historical producer.
