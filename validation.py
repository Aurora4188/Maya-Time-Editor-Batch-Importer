"""Preflight checks for batch import."""

import os

import maya.cmds as cmds

from .models import ValidationReport
from . import time_editor


FBX_PLUGIN_NAMES = ("fbxmaya", "fbxmaya.mll", "fbxmaya.bundle", "fbxmaya.so")


def fbx_plugin_loaded():
    for name in FBX_PLUGIN_NAMES:
        try:
            if cmds.pluginInfo(name, query=True, loaded=True):
                return True
        except RuntimeError:
            continue
    return False


def validate(files, composition, track_name, start_frame, gap_frames, allow_create=False):
    report = ValidationReport()
    enabled = [item for item in files if item.enabled]
    if not enabled:
        report.errors.append("No enabled FBX files are queued.")
    for item in enabled:
        if not os.path.isfile(item.path):
            report.errors.append("File does not exist: {}".format(item.path))
        elif os.path.splitext(item.path)[1].lower() != ".fbx":
            report.errors.append("Not an FBX file: {}".format(item.path))
    if not fbx_plugin_loaded():
        report.errors.append("Maya FBX plug-in is not loaded (fbxmaya).")
    if not composition.strip():
        report.errors.append("Composition name is required.")
    if not track_name.strip():
        report.errors.append("Track name is required.")
    if gap_frames < 0:
        report.errors.append("Gap Frames must be zero or greater.")
    if not isinstance(start_frame, (int, float)):
        report.errors.append("Start Frame must be numeric.")
    if not cmds.ls(type="joint"):
        report.errors.append("No Source skeleton joints exist in the current scene.")

    if composition and time_editor.composition_exists(composition):
        try:
            track = time_editor.find_track(composition, track_name)
        except time_editor.TimeEditorError as error:
            report.errors.append(str(error))
        else:
            if track and time_editor.track_clip_ids(track[3]):
                report.warnings.append(
                    "Target Track already contains clips. Each imported range will be "
                    "checked; existing clips will never be moved or removed."
                )
            elif not track and not allow_create:
                report.errors.append("Target Track does not exist.")
    elif composition and not allow_create:
        report.errors.append("Target Composition does not exist.")
    return report
