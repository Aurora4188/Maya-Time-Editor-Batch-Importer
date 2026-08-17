"""Small Maya Time Editor adapter with version-sensitive calls isolated here."""

import math

import maya.cmds as cmds


EPSILON = 1e-4


class TimeEditorError(RuntimeError):
    pass


def list_compositions():
    return cmds.timeEditorComposition(query=True, allCompositions=True) or []


def composition_exists(name):
    return name in list_compositions()


def ensure_composition(name, allow_create=False):
    if composition_exists(name):
        return name
    if not allow_create:
        raise TimeEditorError("Composition does not exist: {}".format(name))
    cmds.timeEditorComposition(name)
    if not composition_exists(name):
        raise TimeEditorError("Maya did not create Composition: {}".format(name))
    return name


def _track_records(composition):
    records = []
    for token in cmds.timeEditorTracks(path=composition, query=True, allTracks=True) or []:
        tracks_node, index_text = token.rsplit(":", 1)
        index = int(index_text)
        name = cmds.timeEditorTracks(
            tracks_node, query=True, trackName=True, trackIndex=index
        )
        records.append((name, tracks_node, index, token))
    return records


def find_track(composition, track_name):
    matches = [record for record in _track_records(composition) if record[0] == track_name]
    if len(matches) > 1:
        raise TimeEditorError(
            "Track name is not unique in Composition '{}': {}".format(
                composition, track_name
            )
        )
    return matches[0] if matches else None


def ensure_track(composition, track_name, allow_create=False):
    record = find_track(composition, track_name)
    if record:
        return record[3]
    if not allow_create:
        raise TimeEditorError(
            "Track does not exist in '{}': {}".format(composition, track_name)
        )
    cmds.timeEditorTracks(path=composition, edit=True, addTrack=-1, trackType=0)
    records = _track_records(composition)
    if not records:
        raise TimeEditorError("Maya did not create a Track in {}".format(composition))
    created = records[-1]
    cmds.timeEditorTracks(
        created[1], edit=True, trackName=track_name, trackIndex=created[2]
    )
    record = find_track(composition, track_name)
    if not record:
        raise TimeEditorError("Maya did not name the new Track: {}".format(track_name))
    return record[3]


def track_clip_ids(track_token):
    return [int(value) for value in (
        cmds.timeEditorTracks(track_token, query=True, allClips=True) or []
    )]


def query_clip_timing(clip_id):
    clip_id = int(clip_id)
    start = float(cmds.timeEditorClip(clip_id, query=True, startTime=True, absolute=True))
    end = float(cmds.timeEditorClip(clip_id, query=True, endTime=True, absolute=True))
    duration = float(cmds.timeEditorClip(clip_id, query=True, duration=True, absolute=True))
    if end + EPSILON < start:
        raise TimeEditorError(
            "Clip {} returned an invalid range: {} to {}".format(clip_id, start, end)
        )
    return start, end, duration


def inclusive_frame_count(start, end):
    """Return occupied frame count for integral frame endpoints."""
    span = float(end) - float(start)
    if abs(span - round(span)) <= EPSILON:
        return float(round(span) + 1)
    return span


def next_start(end, gap_frames):
    if gap_frames < 0:
        raise ValueError("Gap Frames must be zero or greater.")
    return float(end) + float(gap_frames) + 1.0


def ranges_overlap(first_start, first_end, second_start, second_end):
    return not (
        float(first_end) < float(second_start) - EPSILON
        or float(second_end) < float(first_start) - EPSILON
    )


def existing_clip_ranges(track_token, exclude_ids=None):
    exclude_ids = set(exclude_ids or [])
    return [
        (clip_id,) + query_clip_timing(clip_id)[:2]
        for clip_id in track_clip_ids(track_token)
        if clip_id not in exclude_ids
    ]


def create_fbx_clip(fbx_path, track_token, clip_name, start_time):
    """Import via Time Editor connect mode; never falls back to scene import."""
    before = set(track_clip_ids(track_token))
    try:
        clip_node = cmds.timeEditorClip(
            clip_name,
            importFbx=fbx_path,
            importOption="connect",
            track=track_token,
            startTime=float(start_time),
        )
    except (RuntimeError, TypeError) as error:
        raise TimeEditorError(
            "timeEditorClip FBX connect import failed: {}".format(error)
        )
    after = set(track_clip_ids(track_token))
    created_ids = sorted(after - before)
    if not clip_node or len(created_ids) != 1:
        raise TimeEditorError(
            "Expected one new Time Editor clip; Maya returned node={!r}, ids={}. "
            "Check FBX name matching and import remapping.".format(clip_node, created_ids)
        )
    clip_id = created_ids[0]
    queried_node = cmds.timeEditorClip(clip_id, query=True, clipNode=True)
    if queried_node:
        clip_node = queried_node
    anim_source = cmds.timeEditorClip(clip_id, query=True, animSource=True)
    if not anim_source:
        raise TimeEditorError("Clip {} has no Animation Source.".format(clip_id))
    return clip_node, clip_id, anim_source


def remove_clip(clip_id):
    cmds.timeEditorClip(clipId=int(clip_id), edit=True, removeClip=True)


def timing_warning(start, end, maya_duration):
    frame_count = inclusive_frame_count(start, end)
    span = end - start
    if math.isclose(maya_duration, frame_count, abs_tol=EPSILON):
        return "Maya duration matches inclusive frame count."
    if math.isclose(maya_duration, span, abs_tol=EPSILON):
        return "Maya duration matches end-start; recorded duration uses inclusive frames."
    return (
        "Maya duration ({}) matches neither end-start ({}) nor inclusive frame count ({})."
        .format(maya_duration, span, frame_count)
    )
