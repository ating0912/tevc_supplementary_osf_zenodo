import subprocess

p = subprocess.run(
    [r"C:\Program Files\MATLAB\R2026a\bin\matlab.exe", "-batch", "disp('py_matlab_test')"],
    cwd=r".",
    text=True,
    capture_output=True,
    timeout=60,
)
print("code=", p.returncode)
print("stdout=", p.stdout)
print("stderr=", p.stderr)
