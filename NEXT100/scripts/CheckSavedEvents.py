import pandas as pd
import sys

# Script to return the number of events saved in file as an exit code

f = sys.argv[1]

config = pd.read_hdf(f, "MC/configuration")

N_saved = config[config["param_key"] == "saved_events"].param_value.iloc[0]
N_saved = int(N_saved)

sys.exit(N_saved)
