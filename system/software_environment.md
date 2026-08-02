# Software and Hardware Environment

## Operating System

- OS: Microsoft Windows NT 10.0.26200.0
- Architecture: 64-bit
- Machine name recorded during packaging: LAPTOP-NEKNF074

## CPU / RAM / GPU

- CPU: Intel64 Family 6 Model 186 Stepping 2, GenuineIntel
- Logical processors: 20
- RAM: 15.65 GB
- GPU adapters detected from Windows display registry:
  - NVIDIA GeForce RTX 4050 Laptop GPU
  - Intel(R) Iris(R) Xe Graphics
- GPU usage note: packaged validation scripts do not require GPU execution unless a specific runner states otherwise.

## MATLAB / PlatEMO

- MATLAB version recorded from `matlab_r2020b_startup.log`: 9.9.0.2037887 (R2020b) Update 8
- MATLAB direct launch note: a later direct `matlab -batch` check encountered a local license checkout error, so the package records the existing run-environment log rather than a fresh launch result.
- PlatEMO-related folders present in the workspace:
  - PlatEMO
  - PlatEMO_v2.9.0
  - PlatEMO_v4.3
  - platemo_v43_compat
  - matlab_platemo
- Final paper note: if a specific experiment block used a specific PlatEMO version, cite that block-level runner or source map entry alongside this environment record.

## Python

- Environment file: `environment.yml`
- Requirements file: `requirements.txt`
- Main packages: numpy, pandas, scipy, scikit-learn, joblib, matplotlib, seaborn, openpyxl, PyYAML, statsmodels.
