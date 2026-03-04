from pathlib import Path


def MakeList(jobname, recostage_in, recostage_out, diff):
    # Define the local directory path
    local_path = f"/ospool/ap40/data/krishan.mistry/job/Production/{jobname}/{recostage_in}/"

    # Get all files in the directory
    file_list = [f"{file.name}" for file in Path(local_path).iterdir() if file.is_file()]

    # Write to a text file
    output_file = f"../job/filelists/{jobname}_{recostage_out}.txt"
    with open(output_file, "w") as f:
        f.write("\n".join(file_list))

    print(f"File list saved to {output_file}")

# jobname="NEXT100_Kr83m"
#jobname="NEXT100_Kr83m_Full"
#jobname="NEXT100_Tl208_Port1a"
jobname="NEXT100_Tl208_Port1a_DEP"
# jobname="NEXT100_Tl208_Port1a_DEP_Full"


MakeList(jobname, "hypathia", "sophronia")