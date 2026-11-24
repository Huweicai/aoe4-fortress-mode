# AoE4 mods

| Folder | What |
|---|---|
| `fortress_mode/` | Fortress Mode game mode: co-op defence against AI siege waves |
| `maps/fortress_pass/` | Fortress Pass generated map: walled basins with narrow gaps |
| `maps/fortress_h/` | Fortress H generated map: defenders back to back on the crossbar of an H, attackers on both uprights |
| `tools/sga.py` | Lists and extracts AoE4 SGA v10 archives, e.g. the official map scripts in `Data.sga` |

Preview a map layout without the game (library extracted from `Data.sga`, `scar/terrainlayout/library`):

    lua maps/tests/preview.lua maps/fortress_pass/fortress_pass.lua <library dir> 640 1,1,2,2,2,2
