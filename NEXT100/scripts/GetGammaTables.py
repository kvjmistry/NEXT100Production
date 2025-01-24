import numpy as np
import pandas as pd
import sys

# ----------------------------------------------------------------------------------------------------
def CallGetParentCreators(hits_merged, label):

    eioni = len(hits_merged[ (hits_merged.creator_proc == label)])
    while(eioni >0):
        hits_merged = GetParentCreators(hits_merged, parts_mothers, label)
        eioni = len(hits_merged[(hits_merged.creator_proc == label)])

    return hits_merged
# ----------------------------------------------------------------------------------------------------
# Function to get the creator proc, if eIoni or msc, then need to find the parent process
def GetParentCreators(hits_merged, parts_mothers, label):
    ioni_proc = hits_merged # hits merged here only contains eIoni or msc rows
    ioni_proc = ioni_proc[["event_id","mother_id"]]

    parts_mothers_slim = parts_mothers[["particle_id","mother_id"]]

    # Merge the mother information to the eIoni columns
    ioni_proc_mother_merged = pd.merge(
        ioni_proc.reset_index(), 
        parts_mothers, 
        left_on='mother_id', 
        right_on='particle_id', 
        how='inner'
    )

    # Fix the indexing
    ioni_proc_mother_merged = ioni_proc_mother_merged[["index", "creator_proc"]]
    ioni_proc_mother_merged = ioni_proc_mother_merged.set_index("index", drop=True)
    ioni_proc_mother_merged.index.name = None

    # join the tables and then replace the eIoni with the parent creator if eIoni
    hits_merged = pd.merge(hits_merged, ioni_proc_mother_merged, left_index=True, right_index=True, how='inner')
    hits_merged['creator_proc_x'] = np.where(hits_merged['creator_proc_x'] == label, hits_merged['creator_proc_y'], hits_merged['creator_proc_x'])
    
    # Need to update the mother ids
    hits_merged['particle_id'] = np.where(hits_merged['creator_proc_x'] == label, hits_merged['mother_id'], hits_merged['particle_id']) # Update the particle_id and mother id
    hits_merged = hits_merged.drop(['mother_id'], axis=1)
    hits_merged  = pd.merge(hits_merged, parts_mothers_slim, on='particle_id', how='inner')

    hits_merged = hits_merged.drop(['creator_proc_y'], axis=1)
    hits_merged.rename(columns={'creator_proc_x': 'creator_proc'}, inplace=True)

    return hits_merged

# ----------------------------------------------------------------------------------------------------
# Calculate the distance from neighbouring points
def euclidean_distance(p1, p2):
    return np.sqrt(np.sum((p1 - p2) ** 2))

def calculate_distance(row1, row2):
    return np.sqrt((row1['x'] - row2['x'])**2 + (row1['y'] - row2['y'])**2 + (row1['z'] - row2['z'])**2)
# ----------------------------------------------------------------------------------------------------
# Function to merge group ids if their distance is less than some threshold
def MergeGroups(df, distance_threshold):
    while True:
        merged = False
        unique_groups = df['group'].unique()
        
        for group in unique_groups:
            current_group_hits = df[df['group'] == group]
            other_hits = df[df['group'] != group]
            
            for _, current_hit in current_group_hits.iterrows():
                # Calculate distances to all other hits
                distances = other_hits.apply(
                    lambda other_hit: calculate_distance(current_hit, other_hit), axis=1
                )
                
                # Find the closest hit
                min_distance = distances.min()
                if min_distance <= distance_threshold:
                    closest_hit_group = other_hits.loc[distances.idxmin(), 'group']
                    
                    # Merge the groups
                    df.loc[df['group'] == closest_hit_group, 'group'] = group
                    merged = True
        
        # Break the loop if no more groups are merged
        if not merged:
            break
    
    return df
# ----------------------------------------------------------------------------------------------------
# Function groups hits that are within ~ 1 step length together
# Will assign a new group, assumes neighbouring hits are created by same particle
def GetGroups(hits_merged):

    electrons = hits_merged[(hits_merged.particle_name == "e-") | (hits_merged.particle_name == "e+") ]

    distance_cut = 1.5 # mm -- max step size is 1 mm

    # Loop over unique mothers
    electrons["group"] = 0
    electrons = electrons.reset_index(drop=True)

    group_index = 0

    # Loop over the rows
    for i in range(1, len(electrons)):
        prev_point = electrons.iloc[i - 1][['x', 'y', 'z']].to_numpy()
        curr_point = electrons.iloc[i][['x', 'y', 'z']].to_numpy()
        distance = euclidean_distance(curr_point,prev_point)

        if (distance < distance_cut):
            electrons.at[i-1, "group"] = group_index
        else:
            electrons.at[i-1, "group"] = int(group_index)
            group_index = int(group_index + 1)

        if (i == len(electrons)-1):
            electrons.at[i, "group"] = int(group_index)

    # display(electrons)
    # Merge groups that have hits within 10 mm
    electrons = MergeGroups(electrons, 3)

    # Group by 'group' and calculate mean of 'x', 'y', 'z', keep other columns
    # This collated all the hits into a row the mean positions for rows with the same group
    grouped = electrons.groupby(['group', 'mother_id']).agg({
        'event_id': 'first',  # Keep the first event_id in each group
        'x': 'mean',          # Mean of x
        'y': 'mean',          # Mean of y
        'z': 'mean',          # Mean of z
        'energy': 'sum',      # Sum of energy
        'creator_proc': 'first'
    }).reset_index()

    # Assign the same group number to all rows where creator_proc == "conv"
    # This is to fix a bug where geant4 messes up the step size
    conv_rows = grouped['creator_proc'] == 'conv'
    new_group_number = grouped.loc[conv_rows, 'group'].min()  # Use the smallest group number in those rows
    grouped.loc[conv_rows, 'group'] = new_group_number
    
    return grouped, electrons

# ----------------------------------------------------------------------------------------------------
# Identify if any of the mother ids are electrons
# If they are then look at their mother to see if its a gamma
def GetParentName(parts, id_):
    parent = parts[parts.particle_id == id_]
    parent_name = parent["particle_name"].item()
    mother_id = parent["mother_id"].item()
    particle_id = parent["particle_id"].item()
    creator_proc = parent.creator_proc.item()

    if (creator_proc == "RadioactiveDecay"):
        creator_proc="RD"
    if ( (creator_proc == "phot" or creator_proc == "eIoni") and parent_name == "gamma"):
        creator_proc="xray"


    if (parent.primary.item()==1):
        primary = True
    else:
        primary = False

    return parent_name, particle_id, mother_id, creator_proc, primary

# ----------------------------------------------------------------------------------------------------
# Now we identify if any of the mother ids are electrons. If they are
# then look for their mother to see what gamma they came from
# also get information about how that gamma was made. e.g x-ray, radioactive decay (RD) or eBrem
def GetElectronMother(grouped):
    new_labels = []
    mother_creator_procs = []
    for index, row in grouped.iterrows():
        parent_name = ""
        mother_id = row.mother_id
        while (parent_name != "gamma" or primary_flag):
            parent_name, particle_id, mother_id, creator_proc, primary_flag = GetParentName(parts, mother_id)
        new_labels.append(particle_id)
        mother_creator_procs.append(creator_proc)

    grouped["mother_id"] = new_labels
    grouped["type"]= mother_creator_procs

    print("printing before")
    display(grouped)

    # Merge rows from duplicated entries
    grouped = grouped.groupby(['mother_id', 'creator_proc', 'group'], as_index=False).agg({
        'event_id': 'first',  # Keep the first event_id in each group
        'x': 'mean',          # Mean of x
        'y': 'mean',          # Mean of y
        'z': 'mean',          # Mean of z
        'energy': 'sum',       # Sum of energy
        # 'group' : 'first',
        'type' : 'first'
    })

    # Rename some columns
    grouped.rename(columns={'mother_id': 'gamma_id'}, inplace=True)
    grouped.rename(columns={'creator_proc': 'interaction'}, inplace=True)

    return grouped

# ----------------------------------------------------------------------------------------------------
def GetMotherInfo(particle_id):
    mother = parts[parts.particle_id == particle_id]
    mother_name = mother.particle_name.item()
    mother_id = mother.mother_id.item()
    energy = mother.kin_energy.item()
    creator_proc = mother.creator_proc.item()
    primary = mother.primary.item()
    return mother_name, mother_id, energy, creator_proc, primary

# ----------------------------------------------------------------------------------------------------
# Get the particle tree up to the primary
def GetHistories(grouped):
    history_df = pd.DataFrame()

    primary = 0
    signal_flags = []
    for index in grouped.index:
        brem_flag = False
        counter = 0
        found_signal = False
        gamma_id = grouped.iloc[index].gamma_id.item()
        interaction_type = grouped.iloc[index].type
        group_index = grouped.iloc[index].group.item()
        
        mother_name, mother_id, energy, creator_proc, primary = GetMotherInfo(gamma_id)
        
        history_df = pd.concat([
        history_df, 
            pd.DataFrame({"event_id" : parts.event_id.iloc[0].item(), "group": group_index, "tree": counter ,"particle": mother_name, "particle_id": mother_id, "creator_proc":creator_proc , "energy": energy}, index=[0])
        ], ignore_index=True)
        
        # Check if the type was a brem
        if (interaction_type == "eBrem"):
            brem_flag = True

        counter = counter+1

        while (not primary):
            mother_name, mother_id, energy, creator_proc, primary = GetMotherInfo(mother_id)
            
            history_df = pd.concat([
            history_df, 
                pd.DataFrame({"event_id" : parts.event_id.iloc[0].item(), "group": group_index, "tree": counter, "particle": mother_name, "particle_id": mother_id, "creator_proc":creator_proc, "energy": energy}, index=[0])
            ], ignore_index=True)

            # Check for signal definition
            if (counter == 1 and ((mother_name == "e-") or (mother_name == "e+")) and (creator_proc == "conv" or creator_proc == "phot") and brem_flag):
                signal_flags.append(True)
                found_signal = True
            
            counter = counter+1

        if (not found_signal):
            signal_flags.append(False)
        

    grouped['signal'] = signal_flags

    return grouped, history_df

# ----------------------------------------------------------------------------------------------------
def ComputeBremTable(event):

    parts = particles[particles.event_id == event]
    hits = all_hits[all_hits.event_id == event]

    # Add the mother id and mother creator proc information to the hits table
    parts_mothers = parts[["particle_name","particle_id","mother_id", "creator_proc"]] # useful columns for identifying the mothers
    hits_merged  = pd.merge(hits, parts_mothers, on='particle_id', how='inner')

    # Replace ioni/msc labels with the parent interaction process. This tells us the gamma interaction that made the ionization.
    hits_merged = CallGetParentCreators(hits_merged, "eIoni")
    hits_merged = CallGetParentCreators(hits_merged, "msc")

    # Group the hits based on proximities
    grouped, electrons  = GetGroups(hits_merged)

    # Now we identify if any of the mother ids are electrons. If they are
    # then look for their mother to see what gamma they came from
    # also get information about how that gamma was made. e.g x-ray, radioactive decay (RD) or eBrem
    grouped = GetElectronMother(grouped)

    # Get the particle tree up to the primary, also add signal flag to the grouped df
    grouped, history_df = GetHistories(grouped)

    # Some table formatting
    grouped_order = ['event_id', 'x', 'y', 'z', 'energy', 'gamma_id', 'interaction', 'group', 'type', 'signal']
    grouped = grouped[grouped_order]

    print("Printing Hit Energies:", hits.energy.sum(), grouped.energy.sum(), grouped.energy.sum()/hits.energy.sum())
    return grouped, history_df

# ----------------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------
file = sys.argv[1]

particles = pd.read_hdf(file, "parts")
all_hits = pd.read_hdf(file, "hits")
events = particles.event_id.unique()

gammaTables = []
gammaHistorys = []

for index, eid in enumerate(events):
    print("On index, Event:", index, eid)
    gammaTables, gammaHistorys  = ComputeBremTable(eid)

gammaTables = pd.concat(gammaTables, axis=0)
gammaHistorys = pd.concat(gammaHistorys, axis=0)

print("Gamma Table")
print(gammaTables)
print("Gamma History")
print(gammaHistorys)

outfile = sys.argv[2]
with pd.HDFStore(outfile, mode='w', complevel=5, complib='zlib') as store:
    # Save the new DataFrame under a unique key
    store.put(key='MC/GammaTable', value=gammaTables, format='table')
    store.put(key='MC/gammaHistory', value=gammaHistorys, format='table')