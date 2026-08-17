"""Batch orchestration for Time Editor FBX imports."""

import os

import maya.cmds as cmds

from .models import BatchResult, ImportFailure, Segment
from . import time_editor
from . import validation


class BatchImporter:
    def __init__(self, log_callback=None):
        self._log_callback = log_callback or (lambda message: None)

    def _log(self, message):
        self._log_callback(str(message))

    def run(
        self,
        files,
        composition,
        track_name,
        start_frame,
        gap_frames,
        set_playback_range=True,
        allow_create=False,
    ):
        report = validation.validate(
            files, composition, track_name, start_frame, gap_frames, allow_create
        )
        if not report.valid:
            raise ValueError("\n".join(report.errors))

        result = BatchResult()
        undo_open = False
        try:
            cmds.undoInfo(openChunk=True, chunkName="Time Editor Batch Import")
            undo_open = True
            composition = time_editor.ensure_composition(composition, allow_create)
            track = time_editor.ensure_track(composition, track_name, allow_create)
            current_start = float(start_frame)

            for item in [entry for entry in files if entry.enabled]:
                stage = "Import Animation Source and Clip"
                clip_id = None
                self._log("Importing: {}".format(item.path))
                try:
                    clip_name = os.path.splitext(os.path.basename(item.path))[0]
                    clip_node, clip_id, anim_source = time_editor.create_fbx_clip(
                        item.path, track, clip_name, current_start
                    )
                    stage = "Query Clip Timing"
                    start, end, maya_duration = time_editor.query_clip_timing(clip_id)

                    stage = "Check Existing Clip Conflicts"
                    conflicts = [
                        existing_id
                        for existing_id, existing_start, existing_end
                        in time_editor.existing_clip_ranges(track, exclude_ids=[clip_id])
                        if time_editor.ranges_overlap(start, end, existing_start, existing_end)
                    ]
                    if conflicts:
                        time_editor.remove_clip(clip_id)
                        raise time_editor.TimeEditorError(
                            "Range {}-{} overlaps existing clip IDs {}. The new clip was removed."
                            .format(start, end, conflicts)
                        )

                    duration = time_editor.inclusive_frame_count(start, end)
                    warning = time_editor.timing_warning(start, end, maya_duration)
                    segment = Segment(
                        name=clip_name,
                        source_file=item.path,
                        anim_source=anim_source,
                        clip_id=clip_id,
                        clip_node=clip_node,
                        start=start,
                        end=end,
                        duration=duration,
                        maya_duration=maya_duration,
                        gap_after=int(gap_frames),
                        warnings=[warning],
                    )
                    result.segments.append(segment)
                    item.status = "Imported"
                    self._log("Animation Source: {}".format(anim_source))
                    self._log(
                        "Clip {} (ID {}) range {}-{}, frames {}, Maya duration {}"
                        .format(clip_node, clip_id, start, end, duration, maya_duration)
                    )
                    self._log("Timing check: {}".format(warning))
                    current_start = time_editor.next_start(end, gap_frames)
                except Exception as error:
                    item.status = "Failed"
                    result.failures.append(ImportFailure(item.path, stage, str(error)))
                    self._log("FAILED [{}]: {}".format(stage, error))
                    if clip_id is not None and clip_id in time_editor.track_clip_ids(track):
                        result.stopped_early = True
                        self._log(
                            "Stopped: failed clip cleanup could not be proven safe. "
                            "No existing scene content was deleted."
                        )
                        break

            if result.segments and set_playback_range:
                result.playback_start = min(item.start for item in result.segments)
                result.playback_end = max(item.end for item in result.segments)
                cmds.playbackOptions(
                    minTime=result.playback_start,
                    maxTime=result.playback_end,
                    animationStartTime=result.playback_start,
                    animationEndTime=result.playback_end,
                )
        finally:
            if undo_open:
                cmds.undoInfo(closeChunk=True)

        self._log(
            "Finished: {} succeeded, {} failed."
            .format(len(result.segments), len(result.failures))
        )
        return result
