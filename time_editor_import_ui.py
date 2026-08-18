"""Compact PySide2 UI for the existing Time Editor FBX sequence importer."""

import os

from PySide2 import QtCore, QtWidgets
from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.OpenMayaUI as omui


WINDOW_OBJECT_NAME = "timeEditorFbxImporterWindow"
_window = None


def maya_main_window():
    """Return Maya's main window as a QWidget."""
    pointer = omui.MQtUtil.mainWindow()
    if pointer is None:
        return None
    return wrapInstance(int(pointer), QtWidgets.QWidget)


def _load_core_module():
    """Import the existing core module without relying on an absolute path."""
    try:
        from . import time_editor_test
    except (ImportError, ValueError):
        import time_editor_test
    return time_editor_test


def _format_number(value):
    """Avoid displaying integral frame values with an unnecessary .0 suffix."""
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


class TimeEditorFbxImporterWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(TimeEditorFbxImporterWindow, self).__init__(
            parent or maya_main_window()
        )
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("Time Editor FBX Importer")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.setMinimumSize(440, 460)
        self.resize(520, 540)

        self.fbx_files = []

        self.create_widgets()
        self.create_layout()
        self.create_connections()
        self.refresh_file_list()

    def create_widgets(self):
        self.select_button = QtWidgets.QPushButton("Select FBX Files")
        self.clear_button = QtWidgets.QPushButton("Clear")
        self.file_count_label = QtWidgets.QLabel("Selected: 0")

        self.file_list = QtWidgets.QListWidget()
        self.file_list.setSelectionMode(
            QtWidgets.QAbstractItemView.NoSelection
        )
        self.file_list.setAlternatingRowColors(True)

        self.gap_spinbox = QtWidgets.QSpinBox()
        self.gap_spinbox.setRange(0, 1000000)
        self.gap_spinbox.setValue(5)

        self.custom_start_radio = QtWidgets.QRadioButton(
            "Custom Start Frame"
        )
        self.append_radio = QtWidgets.QRadioButton(
            "Append After Existing Clips"
        )
        self.start_mode_group = QtWidgets.QButtonGroup(self)
        self.start_mode_group.addButton(self.custom_start_radio)
        self.start_mode_group.addButton(self.append_radio)
        self.custom_start_radio.setChecked(True)

        self.start_spinbox = QtWidgets.QSpinBox()
        self.start_spinbox.setRange(-1000000, 1000000)
        self.start_spinbox.setValue(0)

        self.import_button = QtWidgets.QPushButton("Import to Time Editor")
        self.import_button.setMinimumHeight(36)

        self.report_edit = QtWidgets.QPlainTextEdit()
        self.report_edit.setReadOnly(True)
        self.report_edit.setPlaceholderText("Import results will appear here.")

    def create_layout(self):
        file_actions = QtWidgets.QHBoxLayout()
        file_actions.addWidget(self.select_button)
        file_actions.addWidget(self.clear_button)
        file_actions.addStretch()
        file_actions.addWidget(self.file_count_label)

        files_layout = QtWidgets.QVBoxLayout()
        files_layout.addLayout(file_actions)
        files_layout.addWidget(self.file_list)
        files_group = QtWidgets.QGroupBox("FBX Files")
        files_group.setLayout(files_layout)

        settings_layout = QtWidgets.QGridLayout()
        settings_layout.addWidget(self.custom_start_radio, 0, 0)
        settings_layout.addWidget(self.start_spinbox, 0, 1)
        settings_layout.addWidget(self.append_radio, 1, 0, 1, 2)
        settings_layout.addWidget(QtWidgets.QLabel("Gap Frames:"), 2, 0)
        settings_layout.addWidget(self.gap_spinbox, 2, 1)
        settings_layout.setColumnStretch(2, 1)
        settings_group = QtWidgets.QGroupBox("Import Settings")
        settings_group.setLayout(settings_layout)

        report_layout = QtWidgets.QVBoxLayout()
        report_layout.addWidget(self.report_edit)
        report_group = QtWidgets.QGroupBox("Report")
        report_group.setLayout(report_layout)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(files_group, 2)
        layout.addWidget(settings_group)
        layout.addWidget(self.import_button)
        layout.addWidget(report_group, 3)

    def create_connections(self):
        self.select_button.clicked.connect(self.select_fbx_files)
        self.clear_button.clicked.connect(self.clear_fbx_files)
        self.import_button.clicked.connect(self.import_to_time_editor)
        self.custom_start_radio.toggled.connect(
            self.start_spinbox.setEnabled
        )

    def select_fbx_files(self):
        selected_files = cmds.fileDialog2(
            dialogStyle=2,
            fileMode=4,
            fileFilter="FBX Files (*.fbx)",
            caption="Select FBX Files",
        )
        if not selected_files:
            return

        files = []
        known = set()
        for file_path in selected_files:
            normalized = os.path.normpath(file_path).replace("\\", "/")
            key = os.path.normcase(normalized)
            if normalized.lower().endswith(".fbx") and key not in known:
                files.append(normalized)
                known.add(key)

        self.fbx_files = files
        self.refresh_file_list()

    def clear_fbx_files(self):
        self.fbx_files[:] = []
        self.refresh_file_list()

    def refresh_file_list(self):
        self.file_list.clear()
        for file_path in self.fbx_files:
            item = QtWidgets.QListWidgetItem(os.path.basename(file_path))
            item.setToolTip(file_path)
            self.file_list.addItem(item)
        self.file_count_label.setText("Selected: {}".format(len(self.fbx_files)))

    def _show_warning(self, title, message):
        self.report_edit.setPlainText(message)
        QtWidgets.QMessageBox.warning(self, title, message)

    def _append_start_time(self, track_index=0):
        tracks_node = cmds.timeEditorComposition(query=True, active=True)
        if not tracks_node:
            raise RuntimeError("No active Time Editor Composition.")

        tracks = cmds.timeEditorTracks(
            tracks_node,
            query=True,
            allTracks=True,
        ) or []

        if track_index < 0 or track_index >= len(tracks):
            raise RuntimeError(
                "Invalid track index {}. Available: {}".format(
                    track_index,
                    tracks,
                )
            )

        clip_ids = cmds.timeEditorTracks(
            tracks[track_index],
            query=True,
            allClips=True,
        ) or []

        if not clip_ids:
            return 0

        max_end = max(
            cmds.timeEditorClip(
                clip_id,
                query=True,
                endTime=True,
                absolute=True,
            )
            for clip_id in clip_ids
        )
        return max_end + self.gap_spinbox.value() + 1

    def import_to_time_editor(self):
        if not self.fbx_files:
            self._show_warning(
                "No FBX Files",
                "No FBX files selected. Please select one or more FBX files.",
            )
            return

        try:
            core = _load_core_module()
        except Exception as error:
            self._show_warning(
                "Core Module Error",
                "Failed to import the core module:\n{}".format(error),
            )
            return

        import_function = getattr(core, "import_fbx_sequence", None)
        if not callable(import_function):
            self._show_warning(
                "Core Function Missing",
                "The core module does not define import_fbx_sequence().",
            )
            return

        self.import_button.setEnabled(False)
        self.report_edit.setPlainText("Importing...\n")
        QtWidgets.QApplication.processEvents()

        try:
            if self.append_radio.isChecked():
                start_time = self._append_start_time(track_index=0)
            else:
                start_time = self.start_spinbox.value()

            segments = import_function(
                fbx_paths=list(self.fbx_files),
                track_index=0,
                start_time=start_time,
                gap_frames=self.gap_spinbox.value(),
            )
        except Exception as error:
            self._show_warning(
                "Import Failed",
                "Import failed:\n{}".format(error),
            )
            return
        finally:
            self.import_button.setEnabled(True)

        if not isinstance(segments, (list, tuple)):
            self._show_warning(
                "Invalid Import Result",
                "import_fbx_sequence() returned an invalid result: {}".format(
                    type(segments).__name__
                ),
            )
            return

        successful = [
            segment for segment in segments
            if isinstance(segment, dict) and segment.get("status") == "success"
        ]
        failed = [
            segment for segment in segments
            if isinstance(segment, dict) and segment.get("status") != "success"
        ]

        lines = [
            "Import completed.",
            "",
            "Selected: {}".format(len(self.fbx_files)),
            "Successful: {}".format(len(successful)),
            "Failed: {}".format(len(failed)),
            "",
        ]

        for segment in successful:
            lines.append(
                "[SUCCESS] {} | {} -> {}".format(
                    segment.get("node", "<unknown clip>"),
                    _format_number(segment.get("start", "?")),
                    _format_number(segment.get("end", "?")),
                )
            )

        for segment in failed:
            lines.append(
                "[FAILED] {} | {}".format(
                    segment.get("source_file", "<unknown file>"),
                    segment.get("error", "Unknown error"),
                )
            )

        unprocessed_count = len(self.fbx_files) - len(segments)
        if unprocessed_count > 0:
            lines.extend([
                "",
                "Not processed: {} (the core importer stopped after a failure)".format(
                    unprocessed_count
                ),
            ])

        report = "\n".join(lines)
        self.report_edit.setPlainText(report)

        if failed or unprocessed_count:
            QtWidgets.QMessageBox.warning(
                self,
                "Import Completed with Errors",
                "{} succeeded, {} failed, {} not processed.".format(
                    len(successful), len(failed), unprocessed_count
                ),
            )
        else:
            QtWidgets.QMessageBox.information(
                self,
                "Import Completed",
                "All {} FBX files imported successfully.".format(
                    len(successful)
                ),
            )


def show():
    """Show one instance of the importer window."""
    global _window

    parent = maya_main_window()
    if parent:
        existing = parent.findChild(QtWidgets.QDialog, WINDOW_OBJECT_NAME)
        if existing:
            existing.close()
            existing.deleteLater()

    if _window:
        try:
            _window.close()
            _window.deleteLater()
        except RuntimeError:
            pass

    _window = TimeEditorFbxImporterWindow(parent)
    _window.show()
    _window.raise_()
    _window.activateWindow()
    return _window
