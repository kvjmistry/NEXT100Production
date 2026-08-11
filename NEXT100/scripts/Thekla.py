# Thekla.py
# This script will run John Waitons test Thekla city. This city takes sophronia files
# as an input and produces a new file with global track information, such as number
# of tracks and blob energies. 

from invisible_cities.reco import paolina_functions as plf
from invisible_cities.core.system_of_units import mm
from invisible_cities.types.ic_types import types_dict_tracks, xy
from invisible_cities.evm.event_model import BHit, Voxel, Hit, Cluster, HitCollection
from invisible_cities.cities.components import track_blob_info_creator_extractor
from invisible_cities.io.dst_io        import load_dst
from invisible_cities.io.hits_io        import load_hits, hits_from_df
from invisible_cities.core              import system_of_units as units
from invisible_cities.types.symbols     import HitEnergy
from invisible_cities.reco.paolina_functions import voxelize_hits
from invisible_cities.types.ic_types   import NN

import os
import numpy as np
import pandas as pd
from typing import Callable, List
from sklearn.cluster import DBSCAN

import sys,os,os.path
import numpy as np
import pandas as pd
from networkx import Graph
from typing import Tuple, Callable, Sequence

def find_highest_energy_node( track: Graph
                            , extreme : Voxel
                            , radius  : float) -> Tuple[Voxel, dict]:
    """Find the node with the highest associated energy in the track graph"""
    # we want to obtain the node information here, so have to flag data = True
    # and take first element
    # (energy information is encoded into node, for some reason)
    distances         = plf.shortest_paths(track)

    nodes_within_radius = [node for node in track.nodes if distances[extreme][node] <= radius]
    highest_energy_node = max(nodes_within_radius, key=lambda node: node.E)
    print(highest_energy_node)
    return highest_energy_node

def find_highest_encapsulating_node( track   : Graph
                                   , extreme : Voxel
                                   , big_radius    : float
                                   , small_radius  : float) -> Tuple[Voxel, dict]:
    '''
    Find the voxel within a big radius for which the most energy
    is captured within an equivalent smaller radius.
    '''
    distances = plf.shortest_paths(track)
    nodes_within_radius = [node for node in track.nodes if distances[extreme][node] <= big_radius]

    def energy_within_radius(node):
        return plf.energy_of_voxels_within_radius(distances[node], small_radius)

    highest_encapsulating_node = max(nodes_within_radius, key=energy_within_radius)
    return highest_encapsulating_node


def blob_energies_hits_and_centres_altered( track_graph  : Graph
                                          , big_radius   : float
                                          , small_radius : float) -> Tuple[float, float, Sequence[BHit], Sequence[BHit], Tuple[float, float, float], Tuple[float, float, float]]:
    """Return the energies, the hits and the positions of the blobs.
       Does so with a double iteration method, first taking the extremes
       and defining an extreme radius around them to find the voxel with the
       largest energy, and redefining that as the central voxel.
       """
    distances = plf.shortest_paths(track_graph)
    a, b, _   = plf.find_extrema_and_length(distances)

    # find the highest energy voxel in a radius
    #va_highE = find_highest_energy_node(track_graph, a, big_radius)
    #vb_highE = find_highest_energy_node(track_graph, b, big_radius)
    va_highE = find_highest_encapsulating_node(track_graph, a, big_radius, small_radius)
    vb_highE = find_highest_encapsulating_node(track_graph, b, big_radius, small_radius)
    # Select any node and check its attributes
    ha = plf.hits_in_blob(track_graph, small_radius, va_highE)
    hb = plf.hits_in_blob(track_graph, small_radius, vb_highE)

    voxels = list(track_graph.nodes())
    e_type = voxels[0].Etype
    Ea = sum(getattr(h, e_type) for h in ha)
    Eb = sum(getattr(h, e_type) for h in hb)

    # Consider the case where voxels are built without associated hits
    if len(ha) == 0 and len(hb) == 0 :
        Ea = plf.energy_of_voxels_within_radius(distances[va_highE], small_radius)
        Eb = plf.energy_of_voxels_within_radius(distances[vb_highE], small_radius)

    ca = plf.blob_centre(va_highE)
    cb = plf.blob_centre(vb_highE)

    if Eb > Ea:
        return (Eb, Ea, hb, ha, cb, ca)
    else:
        return (Ea, Eb, ha, hb, ca, cb)


# now lets think up the new functionality for determining the blob centre
def track_blob_info_creator_extractor_altered(vox_size         : Tuple[float, float, float],
                                      strict_vox_size  : bool                      ,
                                      energy_threshold : float                     ,
                                      min_voxels       : int                       ,
                                      scan_radius      : float                     ,
                                      blob_radius      : float                     ,
                                      max_num_hits     : int
                                     ) -> Callable:
    """
    For a given paolina parameters returns a function that extract tracks / blob information from a HitCollection.

    Parameters
    ----------
    vox_size         : [float, float, float]
        (maximum) size of voxels for track reconstruction
    strict_vox_size  : bool
        if False allows per event adaptive voxel size,
        smaller of equal thatn vox_size
    energy_threshold : float
        if energy of end-point voxel is smaller
        the voxel will be dropped and energy redistributed to the neighbours
    min_voxels       : int
        after min_voxel number of voxels is reached no dropping will happen.
    blob_radius      : float
        radius of blob

    Returns
    ----------
    A function that from a given HitCollection returns a pandas DataFrame with per track information.
    """
    def create_extract_track_blob_info(hitc):
        df = pd.DataFrame(columns=list(types_dict_tracks.keys()))
        if len(hitc.hits) > max_num_hits:
            return df, hitc, True
        #track_hits is a new Hitcollection object that contains hits belonging to tracks, and hits that couldnt be corrected
        track_hitc = HitCollection(hitc.event, hitc.time)
        out_of_map = np.any(np.isnan([h.Ep for h in hitc.hits]))
        if out_of_map:
            #add nan hits to track_hits, the track_id will be -1
            track_hitc.hits.extend  ([h for h in hitc.hits if np.isnan   (h.Ep)])
            hits_without_nan       = [h for h in hitc.hits if np.isfinite(h.Ep)]
            #create new Hitcollection object but keep the name hitc
            hitc      = HitCollection(hitc.event, hitc.time)
            hitc.hits = hits_without_nan

        hit_energies = np.array([getattr(h, HitEnergy.Ep.value) for h in hitc.hits])

        if len(hitc.hits) > 0 and (hit_energies>0).any():
            voxels           = plf.voxelize_hits(hitc.hits, vox_size, strict_vox_size, HitEnergy.Ep)
            (    mod_voxels,
             dropped_voxels) = plf.drop_end_point_voxels(voxels, energy_threshold, min_voxels)

            for v in dropped_voxels:
                track_hitc.hits.extend(v.hits)

            tracks = plf.make_track_graphs(mod_voxels)
            tracks = sorted(tracks, key=plf.get_track_energy, reverse=True)

            vox_size_x = voxels[0].size[0]
            vox_size_y = voxels[0].size[1]
            vox_size_z = voxels[0].size[2]
            del(voxels)

            track_hits = []
            for c, t in enumerate(tracks, 0):
                tID = c
                energy = plf.get_track_energy(t)
                numb_of_hits   = len([h for vox in t.nodes() for h in vox.hits])
                numb_of_voxels = len(t.nodes())
                numb_of_tracks = len(tracks   )
                pos   = [h.pos for v in t.nodes() for h in v.hits]
                x, y, z = map(np.array, zip(*pos))
                r = np.sqrt(x**2 + y**2)

                e     = [h.Ep for v in t.nodes() for h in v.hits]
                ave_pos = np.average(pos, weights=e, axis=0)
                ave_r   = np.average(r  , weights=e, axis=0)
                distances = plf.shortest_paths(t)
                extr1, extr2, length = plf.find_extrema_and_length(distances)
                extr1_pos = extr1.XYZ
                extr2_pos = extr2.XYZ

                e_blob1, e_blob2, hits_blob1, hits_blob2, blob_pos1, blob_pos2 = blob_energies_hits_and_centres_altered(t, scan_radius, blob_radius)

                overlap = float(sum(h.Ep for h in set(hits_blob1).intersection(set(hits_blob2))))
                list_of_vars = [hitc.event, tID, energy, length, numb_of_voxels,
                                numb_of_hits, numb_of_tracks,
                                min(x), min(y), min(z), min(r), max(x), max(y), max(z), max(r),
                                *ave_pos, ave_r, *extr1_pos,
                                *extr2_pos, *blob_pos1, *blob_pos2,
                                e_blob1, e_blob2, overlap,
                                vox_size_x, vox_size_y, vox_size_z]

                df.loc[c] = list_of_vars

                for vox in t.nodes():
                    for hit in vox.hits:
                        hit.track_id = tID
                        track_hits.append(hit)

            #change dtype of columns to match type of variables
            df = df.apply(lambda x : x.astype(types_dict_tracks[x.name]))
            track_hitc.hits.extend(track_hits)
        return df, track_hitc, out_of_map

    return create_extract_track_blob_info


def CreateFakeTrack():
    # make a track (it'll need to be much bigger than this obviously)
    tr_1 = []
    # Create a spherical blob centered at (50, 50, 50) with radius 10 mm
    center_x, center_y, center_z = 50 * units.mm, 50 * units.mm, 50 * units.mm
    radius = 50 * units.mm
    step = 10
    # Create a tail for the blob
    tail_length = 40  # Number of points in the tail
    tail_direction = np.array([0.57735027, 0.57735027, 0.57735027])  # Unit vector for tail direction
    tail_start = np.array([center_x, center_y, center_z]) + tail_direction * radius

    for i in range(tail_length):
        perturbation = np.random.uniform(-0.5, 0.5, size=3) * units.mm  # Add some randomness to the tail
        current_position = tail_start + i * step * tail_direction + perturbation
        current_position[2] = np.round(current_position[2])  # Make Z position discrete
        energy = np.random.uniform(low=5, high=20)  # Random energy values for tail points
        tr_1.append([0, 1, current_position[0], current_position[1], current_position[2], 1, energy, energy])

    for _ in range(500): 
        while True:
            x = np.random.uniform(center_x - radius, center_x + radius)
            y = np.random.uniform(center_y - radius, center_y + radius)
            z = np.random.uniform(center_z - radius, center_z + radius)
            z = np.round(z)  # Make Z position discrete
            distance_to_center = np.sqrt((x - center_x)**2 + (y - center_y)**2 + (z - center_z)**2)
            if distance_to_center <= radius:
                # Make points closer to the center more energetic with a smooth transition
                e = np.random.uniform(low=50, high=100) * (1 - distance_to_center / radius) + \
                    np.random.uniform(low=5, high=50) * (distance_to_center / radius)
                tr_1.append([0, 1, x, y, z, 1, e, e])
                break

    return pd.DataFrame(tr_1, columns=['event', 'npeak', 'X', 'Y', 'Z', 'Q', 'E', 'Ep'])

def redistribute_energy(group: pd.DataFrame, val: str = "pass") -> pd.DataFrame:
    """
    Redistribute energy per slice given Q of the SiPMs.
    """
    tot_E = group.E.sum()
    mask = group[val].values < 0
    drp = group[mask]
    srv = group[~mask]

    if drp.empty:
        return srv

    if srv.empty:
        drp = drp.copy()
        drp[["X", "Y", "Q"]] = NN
        return drp

    srv = srv.copy()
    srv["E"] = (srv.Q / srv.Q.sum()) * tot_E
    return srv


def merge_NN_hits(hits: pd.DataFrame, same_peak: bool = True) -> pd.DataFrame:
    sel = hits.Q.eq(NN)
    if not sel.any():
        return hits

    normal = hits[~sel].copy()
    nn     = hits[sel]

    if normal.empty:
        return normal

    corr = pd.DataFrame(0.0, index=normal.index, columns=["E", "Ec"])

    if same_peak:
        normal_groups = {p: g for p, g in normal.groupby("npeak")}
    else:
        z_normal = normal.Z.values
        idx_normal = normal.index.values

    for _, row in nn.iterrows():
        if same_peak:
            cand = normal_groups.get(row.npeak)
            if cand is None or cand.empty:
                continue
            dz = (cand.Z - row.Z).abs()
            closest = cand.loc[np.isclose(dz, dz.min())]
        else:
            dz = np.abs(z_normal - row.Z)
            m  = np.isclose(dz, dz.min())
            closest = normal.loc[idx_normal[m]]

        wE  = closest.E  / closest.E.sum()
        wEc = closest.Ec / closest.Ec.sum()
        corr.loc[closest.index, "E"]  += row.E  * wE
        corr.loc[closest.index, "Ec"] += row.Ec * wEc

    normal[["E", "Ec"]] += corr
    return normal


def make_Q_cut(df: pd.DataFrame, q_thr: float = 0):
    df.loc[df.Q <  q_thr, "pass"] = -1
    df.loc[df.Q >= q_thr, "pass"] = 0

    df = (df.groupby(["Z"], group_keys=False)
            .apply(redistribute_energy, "pass")
            .reset_index(drop=True))
    df = merge_NN_hits(df)
    return df.drop("pass", axis=1)


def drop_isolated_clusters(distance: List[float] = [16., 16., 4.], nhit: int = 3) -> Callable:
    """
    DBSCAN clustering in (X,Y[,Z]) scaled by distance; keeps non-noise hits,
    and optionally recovers "noise" hits that fall inside the Z-span of kept clusters.
    """
    ndim = len(distance)
    dist = np.sqrt(ndim)

    def drop(df: pd.DataFrame) -> pd.DataFrame:
        if len(df) == 0:
            return df

        coords = []
        coords.append(df.X.values / distance[0])
        coords.append(df.Y.values / distance[1])
        if ndim == 3:
            coords.append(df.Z.values / distance[2])
        coords = np.column_stack(coords)

        try:
            db = DBSCAN(eps=dist, min_samples=nhit)
            labels = db.fit_predict(coords)
        except Exception as e:
            print(f"Error in DBSCAN: {e}")
            return df.iloc[:0]

        df = df.assign(cluster_id=labels)

        mask = labels != -1
        pass_df = df.loc[mask].copy()
        drop_df = df.loc[~mask].copy()

        if not pass_df.empty:
            cluster_ranges = (pass_df.groupby("cluster_id")["Z"]
                              .agg(zmin="min", zmax="max")
                              .reset_index())

            merged = (drop_df.assign(key=1)
                      .merge(cluster_ranges.assign(key=1).drop("cluster_id", axis=1), on="key")
                      .drop("key", axis=1))

            drop_inrange = merged.query("Z >= zmin and Z <= zmax")
            drop_inrange = drop_inrange.drop_duplicates(subset=drop_df.columns)

            if not drop_inrange.empty:
                pass_df = pd.concat([pass_df, drop_inrange.drop(columns=["zmin", "zmax"])], axis=0)

        pass_df = (pass_df.groupby(["Z"], group_keys=False)
                        .apply(redistribute_energy, "cluster_id")
                        .reset_index(drop=True))
        pass_df = merge_NN_hits(pass_df)
        return pass_df

    return drop




scan_radius = 75 * units.mm
blob_radius = 50 * units.mm

topological_creator = track_blob_info_creator_extractor_altered((15 * units.mm, 15 * units.mm, 15 * units.mm),
                                                        False,
                                                        10 * units.keV,
                                                        3,
                                                        scan_radius,
                                                        blob_radius,
                                                        1000000
                                                        )


file_in = sys.argv[1]
file_out = sys.argv[2]

data = load_dst(file_in, 'RECO', 'Events')


# Apply drop isolated cluster function
drop_cluster_dim = 3
drop_nhits = 3
q_thr = 0

# Cluster dropping distances
if drop_cluster_dim == 2:
    dist = [16., 16.]
elif drop_cluster_dim == 3:
    dist = [16., 16., 4.]
else:
    raise SystemExit(f"--dim must be 2 or 3, got {drop_cluster_dim}")

dropper = drop_isolated_clusters(distance=dist, nhit=drop_nhits)

# Apply Q cut
data = data.groupby(["event", "npeak"], group_keys=False).apply(make_Q_cut, q_thr)

# Drop isolated clusters + energy redistribution
data = data.groupby(["event", "npeak"], group_keys=False).apply(dropper)

# Now apply the tracking reconstruction --- 
data = data[['event', 'npeak', 'X', 'Y', 'Z', 'Q', 'E', 'Ep']]
data['Ep'] = data['E'] # so this can work

print(data)
hits = hits_from_df(data)

hits_tracks = []
for index, (i, key) in enumerate(hits.items()):
    print("On index", index, "/", len(hits.items()), "|| event", i)
    df, track_hitc, out_of_map = topological_creator(key)
    hits_tracks.append(df)

hits_tracks = pd.concat(hits_tracks, ignore_index=True)
print(hits_tracks)

print("Saving events to file: ", sys.argv[2])
with pd.HDFStore(sys.argv[2], mode='w', complevel=5, complib='zlib') as store:
    store.put('MC/trackinfo', hits_tracks, format='table')
