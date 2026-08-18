import os
import maya.cmds as cmds
import maya.mel as mel


def select_multiple_fbx_files():
    """pop up window for user to select multiple fbx files"""

    selected_files = cmds.fileDialog2(
        dialogStyle=2,
        fileMode=4,
        caption="Select Animation FBX Files",
        fileFilter="FBX Files (*.fbx)"
    )

    if not selected_files:
        print("FBX selection cancelled.")
        return []

    fbx_files = []

    for file_path in selected_files:
        normalized_path = os.path.normpath(
            file_path
        ).replace("\\", "/")

        if not normalized_path.lower().endswith(".fbx"):
            cmds.warning("Skipped non-FBX file: {}".format(normalized_path) )
            continue

        if not os.path.isfile(normalized_path):
            cmds.warning("FBX file does not exist: {}".format(normalized_path ))
            continue

        if normalized_path not in fbx_files:
            fbx_files.append(normalized_path)

    return fbx_files


def import_one_fbx_clip(
    fbx_path,
    track_index=0,
    start_time=0
):

    fbx_path = os.path.normpath(fbx_path).replace("\\", "/")

    if not os.path.isfile(fbx_path):
        raise RuntimeError(
            "FBX file does not exist: {}".format(fbx_path)
        )

    # check active Composition/Tracks Node
    tracks_node = cmds.timeEditorComposition(query=True, active=True)

    if not tracks_node:
        raise RuntimeError("No active Time Editor Composition.")

    # check Track
    tracks = cmds.timeEditorTracks(
        tracks_node,
        query=True,
        allTracks=True
    ) or []

    if track_index < 0 or track_index >= len(tracks):
        raise RuntimeError(
            "Invalid track index {}. Available: {}".format(
                track_index,
                tracks
            )
        )

    target_track = tracks[track_index]

### record existing clips
    clips_before = set(
        cmds.ls(type="timeEditorClip") or []
    )

    safe_path = fbx_path.replace('"', '\\"')
    safe_track = target_track.replace('"', '\\"')

    mel.eval(
        'if (!`exists tePerformImportAnimFiles`) '
        'source teImportOptions.mel;'
    )

    command = (
        'tePerformImportAnimFiles('
        '2, '
        '{{"{fbx_path}"}}, '
        '"{target_track}", '
        '{start_time}, '
        '0'
        ');'
    ).format(
        fbx_path=safe_path,
        target_track=safe_track,
        start_time=float(start_time)
    )
    print("Importing:", fbx_path)
    print("Target track:", target_track)
    print("Start time:", start_time)

    mel_result = mel.eval(command)

    # record new Clip
    clips_after = set(cmds.ls(type="timeEditorClip") or [] )

    new_clips = sorted(clips_after - clips_before)

    if not new_clips:
        raise RuntimeError(
            "Import finished, but no new Time Editor Clip was found."
        )

    print("MEL result:", mel_result)
    print("New clips:", new_clips)

    return new_clips



def get_clip_time_info(clip_node):
    """check Time Editor Clip ID & info """

    if not cmds.objExists(clip_node):
        raise RuntimeError(
            "Clip node does not exist: {}".format(clip_node)
        )

    clip_id = cmds.timeEditorClip(clip_node, query=True, clipIdFromNodeName=True)

    clip_path = cmds.timeEditorClip( clip_id, query=True, clipPath=True)

    start_time = cmds.timeEditorClip( clip_id, query=True, startTime=True, absolute=True)

    end_time = cmds.timeEditorClip( clip_id, query=True, endTime=True, absolute=True)

    duration = cmds.timeEditorClip( clip_id, query=True, duration=True, absolute=True)

    clip_info = {
        "node": clip_node,
        "id": clip_id,
        "path": clip_path,
        "start": start_time,
        "end": end_time,
        "duration": duration,
    }

    print("Clip node:", clip_info["node"])
    print("Clip ID:", clip_info["id"])
    print("Clip path:", clip_info["path"])
    print("Start:", clip_info["start"])
    print("End:", clip_info["end"])
    print("Duration:", clip_info["duration"])

    return clip_info


def import_fbx_sequence(
    fbx_paths = None,
    track_index=0,
    start_time=0,
    gap_frames=5
):
    """
    按列表顺序导入任意数量的FBX Animation Clips，
    并在相邻Clip之间保留指定间隔。
    """
    if fbx_paths is None:
        fbx_paths = select_multiple_fbx_files()

    if not fbx_paths:
        raise ValueError("No FBX files were provided.")

    if gap_frames < 0:
        raise ValueError("gap_frames cannot be negative.")

    current_start = float(start_time)
    imported_segments = []

    print("\n========================================")
    print("FBX Sequence Import")
    print("File count:", len(fbx_paths))
    print("Track index:", track_index)
    print("Start time:", start_time)
    print("Gap frames:", gap_frames)
    print("========================================")

    for index, fbx_path in enumerate(fbx_paths):
        sequence_number = index + 1

        print(
            "\n===== Import {}/{} =====".format(
                sequence_number,
                len(fbx_paths)
            )
        )

        print("FBX:", fbx_path)
        print("Target start:", current_start)

        try:
            new_clips = import_one_fbx_clip(
                fbx_path,
                track_index=track_index,
                start_time=current_start
            )

            # 当前Pipeline约定每个FBX只包含一个Take
            if len(new_clips) != 1:
                raise RuntimeError(
                    "Expected one clip from FBX, but got {}: {}".format(
                        len(new_clips),
                        new_clips
                    )
                )

            clip_node = new_clips[0]
            clip_info = get_clip_time_info(clip_node)

            segment = {
                "index": index,
                "source_file": fbx_path,
                "node": clip_info["node"],
                "id": clip_info["id"],
                "path": clip_info["path"],
                "start": clip_info["start"],
                "end": clip_info["end"],
                "duration": clip_info["duration"],
                "gap_after": gap_frames,
                "status": "success",
            }

            imported_segments.append(segment)

            print(
                "Imported range: {} -> {}".format(
                    clip_info["start"],
                    clip_info["end"]
                )
            )

            # calculate the start frame for next clip
            current_start = (clip_info["end"] + gap_frames + 1)

            print("Next target start:", current_start)

        except Exception as error:
            cmds.warning( "Failed to import FBX: {}\n{}".format(fbx_path, error ))

            failed_segment = { "index": index, "source_file": fbx_path, "status": "failed", "error": str(error), }

            imported_segments.append(failed_segment)

            # MVP测试阶段遇到失败就停止，避免后续位置错误
            break

    print("\n========================================")
    print("Import Summary")
    print("========================================")

    for segment in imported_segments:
        if segment["status"] == "success":
            print(
                "[SUCCESS] {} | {} -> {}".format(
                    segment["node"],
                    segment["start"],
                    segment["end"]
                )
            )
        else:
            print(
                "[FAILED] {} | {}".format(
                    segment["source_file"],
                    segment["error"]
                )
            )

    successful_segments = [
        segment
        for segment in imported_segments
        if segment["status"] == "success"
    ]

    if successful_segments:
        first_start = successful_segments[0]["start"]
        final_end = successful_segments[-1]["end"]

        print("----------------------------------------")
        print("Full range:", first_start, "->", final_end)
        print("Successful:", len(successful_segments))
        print(
            "Failed:",
            len(imported_segments) - len(successful_segments)
        )

    return imported_segments