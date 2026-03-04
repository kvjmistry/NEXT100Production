import os
import glob

# Base directory where the files are located
# base_dir="NEXT100_Kr83m"
# base_dir="NEXT100_Kr83m_Full"
# base_dir="NEXT100_Tl208_Port1a"
base_dir="NEXT100_Tl208_Port1a_DEP"
# base_dir="NEXT100_Tl208_Port1a_DEP_Full"

recostage="hypathia"

# Loop through each pressure and corresponding diffusion folders

folder_path = os.path.join(base_dir, recostage)

# Get all .h5 files in the current directory
files = glob.glob(os.path.join(folder_path, "*.h5"))

# Rename each file
for file in files:
    base, ext = os.path.splitext(file)  # Split filename and extension
    new_name = f"{base}_0{ext}"  # Add _0 before .h5
    os.rename(file, new_name)  # Rename the file
    print(f"Renamed: {file} -> {new_name}")

