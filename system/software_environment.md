# Software and Hardware Environment

## Operating System and Hardware

- OS: Microsoft Windows NT 10.0.26200.0 (Windows 11 generation), 64-bit
- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
- Logical processors: 20
- RAM: 15.65 GB
- GPU adapters: NVIDIA GeForce RTX 4050 Laptop GPU and Intel Iris Xe Graphics
- GPU note: the packaged validation and statistical scripts are CPU-compatible; no GPU is required unless an individual runner explicitly enables it.

## MATLAB and PlatEMO

- MATLAB: 9.9.0.2037887 (R2020b) Update 8
- MATLAB evidence: `matlab_r2020b_startup.log` inside `logs/full_run_logs.zip`
- Formal R2020b baseline: PlatEMO v2.9.0
- Compatibility/reference implementation: PlatEMO v4.3
- Included compatibility source subsets: `code/nsga2_code_extract/PlatEMO_v2.9/` and the referenced MATLAB runners in `code/`
- Full PlatEMO distributions are third-party software and are not relicensed in this repository. Install the stated releases beside the repository when performing a complete MATLAB rerun.

Some diagnostic scripts compare v2.9.0 and v4.3 behavior. These diagnostics are retained for auditability and are not evidence that the formal no-replicate selector used `replicate`.

## Python

The final no-replicate audit recorded Python 3.13.12, pandas 2.3.3, scikit-learn 1.8.0, SciPy 1.16.3, and SHAP 0.52.0. The environment files additionally pin the principal packages used for package validation and result reconstruction:

- Python 3.13.12
- NumPy 2.2.6
- pandas 2.3.3
- SciPy 1.16.3
- scikit-learn 1.8.0
- joblib 1.5.3
- matplotlib 3.10.8
- openpyxl 3.1.5
- PyYAML 6.0.3
- SHAP 0.52.0

`environment.yml` is the primary Conda specification. `requirements.txt` is provided for pip-based inspection environments.
