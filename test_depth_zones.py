#!/usr/bin/env python3
import os
import sys
import numpy as np

os.environ["GST_PLUGIN_FEATURE_RANK"] = "vaapidecodebin:NONE"

HAILO_APPS_DIR = "/home/khajni/hailo-apps"
if HAILO_APPS_DIR not in sys.path:
    sys.path.insert(0, HAILO_APPS_DIR)

import hailo
from hailo_apps.python.pipeline_apps.depth.depth_pipeline import GStreamerDepthApp
from hailo_apps.python.core.gstreamer.gstreamer_app import app_callback_class

class DepthZoneCallback(app_callback_class):
    def __init__(self):
        super().__init__()

def app_callback(element, buffer, user_data):
    if buffer is None:
        return

    roi = hailo.get_roi_from_buffer(buffer)
    depth_mat = roi.get_objects_typed(hailo.HAILO_DEPTH_MASK)

    if len(depth_mat) > 0:
        raw_data = depth_mat[0].get_data()
        mat = np.array(raw_data)
        h, w = mat.shape[:2]

        # Alsó 35% vizsgálata (ütközési sáv a talaj felett)
        ground_roi = mat[int(h * 0.65):, :]
        gh, gw = ground_roi.shape[:2]

        left_zone  = ground_roi[:, :int(gw * 0.35)]
        mid_zone   = ground_roi[:, int(gw * 0.35):int(gw * 0.65)]
        right_zone = ground_roi[:, int(gw * 0.65):]

        l_val = np.mean(left_zone)
        m_val = np.mean(mid_zone)
        r_val = np.mean(right_zone)

        print(f"\rBAL: {l_val:5.2f} | KÖZÉP: {m_val:5.2f} | JOBB: {r_val:5.2f} -> "
              f"{'AKADÁLY ELŐTTÜNK!' if m_val > 0.45 else 'TISZTA ÚT'}", end="", flush=True)

if __name__ == "__main__":
    user_data = DepthZoneCallback()
    app = GStreamerDepthApp(app_callback, user_data)
    app.run()
