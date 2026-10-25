"""Machine-specific dataset locations for iteration 2. Override with environment variables; nothing else in iter2 hard-codes a path."""
import os
from pathlib import Path

CARLA_KIT = Path(os.environ.get("CSCI408_CARLA_KIT", r"C:\carla_multicam_kit"))
CARLA_V2 = Path(os.environ.get("CSCI408_CARLA_V2", CARLA_KIT / "output" / "carla_dataset_v2_low2m_3to6cams_hd"))
CARLA_V3 = Path(os.environ.get("CSCI408_CARLA_V3", CARLA_KIT / "output" / "carla_dataset_v3_ids"))
REAL_WORLD_CORE = Path(os.environ.get("CSCI408_REAL_WORLD", CARLA_KIT / "output" / "real_world_astana_3phones_sync_v1" / "core"))
