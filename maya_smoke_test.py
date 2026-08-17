"""Run one explicit FBX import in Maya before trusting batch operation."""

import os

from . import time_editor


def run(fbx_path, composition="Main_Animation", track="Source_Animations", start=0):
    if not os.path.isfile(fbx_path) or not fbx_path.lower().endswith(".fbx"):
        raise ValueError("Provide an existing FBX path.")
    composition = time_editor.ensure_composition(composition, allow_create=True)
    track_token = time_editor.ensure_track(composition, track, allow_create=True)
    clip_node, clip_id, anim_source = time_editor.create_fbx_clip(
        fbx_path, track_token, os.path.splitext(os.path.basename(fbx_path))[0], start
    )
    queried_start, queried_end, maya_duration = time_editor.query_clip_timing(clip_id)
    return {
        "clip_node": clip_node,
        "clip_id": clip_id,
        "anim_source": anim_source,
        "start": queried_start,
        "end": queried_end,
        "maya_duration": maya_duration,
        "inclusive_frame_count": time_editor.inclusive_frame_count(
            queried_start, queried_end
        ),
        "timing_interpretation": time_editor.timing_warning(
            queried_start, queried_end, maya_duration
        ),
        "next_start_gap_5": time_editor.next_start(queried_end, 5),
    }
