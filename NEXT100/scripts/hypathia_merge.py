import os
import pandas as pd

event_ids_file = "unmatched_DE_Reco.h5"
hypathia_dir = "HypathiaFiles"
output_file = "hypathia_unmatched_events.h5"
reco_key = "RECO/Events"

# Correct key and column name from the HDF5 file
event_ids = pd.read_hdf(event_ids_file, key="unmatched_voxel_groups")["event_id"].unique()

hypathia_files = os.listdir(hypathia_dir)
total_events = 0

with pd.HDFStore(output_file, "w") as out_store:
    for f in hypathia_files:
        path = os.path.join(hypathia_dir, f)
        try:
            with pd.HDFStore(path, "r") as store:
                df = store[reco_key]
                matched = df[df["event_id"].isin(event_ids)]
                if not matched.empty:
                    out_store.append(reco_key, matched, format="table")
                    total_events += len(matched)
        except Exception as e:
            print(f, e)
