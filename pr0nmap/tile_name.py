from pr0nmap import gmap
from pr0nmap import groupxiv

def mk_get_tile_name(which):
    return {
        'gmap': gmap.GMap.get_tile_name,
        'groupxiv': groupxiv.GroupXIV.get_tile_name,
        }[which]

def str_get_tile_name(which):
    return {
        gmap.GMap.get_tile_name: 'gmap',
        groupxiv.GroupXIV.get_tile_name: 'groupxiv',
        }[which]
