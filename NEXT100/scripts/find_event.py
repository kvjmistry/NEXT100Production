
import pandas as pd
import glob


files = sorted(glob.glob("/ospool/ap40/data/krishan.mistry/job/Production/NEXT100_Tl208_Port1a/hypathia/*.h5"))

target_event = 865012

for f in files:
  print(f)
  df =  pd.read_hdf(f, "MC/particles")
  events = df.event_id.unique()
  if (target_event in events):
    print("Found event in :", f)
    break




