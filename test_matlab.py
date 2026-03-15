import os
import shutil
import subprocess

# ---------- CONFIG ----------
# Path to your MATLAB script
MATLAB_SCRIPT_NAME = "screen_attention_analysis.m"

# ---------- MAIN ----------
def launch_matlab():
    project_dir = os.path.dirname(os.path.abspath(__file__))
    analysis_script_path = os.path.join(project_dir, MATLAB_SCRIPT_NAME)
    
    matlab_exe = "/Applications/MATLAB_R2025b.app/bin/matlab"
    if matlab_exe:
        try:
            # Convert paths to MATLAB-friendly format
            matlab_project_dir = project_dir.replace("\\", "/")
            matlab_script_path = analysis_script_path.replace("\\", "/")
            
            # MATLAB command to run
            matlab_command = (
                f"try, cd('{matlab_project_dir}'); run('{matlab_script_path}'); "
                "catch e, disp(getReport(e)); end;"
            )
            
            # Launch MATLAB
            subprocess.Popen([matlab_exe, "-desktop", "-r", matlab_command], cwd=project_dir)
            print("MATLAB launched and screen_attention_analysis.m is running automatically")
        
        except Exception as e:
            print(f"Could not launch MATLAB automatically: {e}")
    else:
        print("MATLAB executable not found in PATH. Add MATLAB to PATH or run the script manually.")

if __name__ == "__main__":
    launch_matlab()