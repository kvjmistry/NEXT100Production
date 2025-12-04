import pandas as pd
import glob


infiles = sorted(glob.glob("/ospool/ap40/data/krishan.mistry/job/Production/NEXT100_Tl208_Port1a/GammaTables/*.h5"))
infiles = sorted(glob.glob("/ospool/ap40/data/krishan.mistry/job/Production/Penelope/NEXT100_Tl208_Port1a/gammatable/*.h5"))


GammaTables = []
GammaHistorys = []


for f in infiles:
  print(f)
  GammaTable = pd.read_hdf(f, "MC/GammaTable")
  GammaHistory = pd.read_hdf(f, "MC/GammaHistory")

  GammaTables.append(GammaTable)
  GammaHistorys.append(GammaHistory)


gammaTables = pd.concat(GammaTables, axis=0)
gammaHistorys = pd.concat(GammaHistorys, axis=0)


outfile = "NEXT100_Tl208_Port1a_GammaTables_4bar_Penelope.h5"

with pd.HDFStore(outfile, mode='w', complevel=5, complib='zlib') as store:
    # Save the new DataFrame under a unique key
    store.put(key='MC/GammaTable', value=gammaTables, format='table')
    store.put(key='MC/GammaHistory', value=gammaHistorys, format='table')
