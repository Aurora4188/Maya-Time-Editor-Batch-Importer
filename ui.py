"""PySide2/PySide6 UI for the Time Editor batch importer."""

import os

try:
    from PySide2 import QtCore, QtWidgets
    from shiboken2 import wrapInstance
except ImportError:
    from PySide6 import QtCore, QtWidgets
    from shiboken6 import wrapInstance

import maya.OpenMayaUI as omui

from .importer import BatchImporter
from .models import AnimationFile
from . import validation


WINDOW_OBJECT_NAME = "timeEditorBatchImporterWindow"


def maya_main_window():
    pointer = omui.MQtUtil.mainWindow()
    if pointer is None:
        return None
    return wrapInstance(int(pointer), QtWidgets.QWidget)


class BatchImporterWindow(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent or maya_main_window())
        self.setObjectName(WINDOW_OBJECT_NAME)
        self.setWindowTitle("Time Editor Batch Importer - MVP1")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.resize(860, 650)
        self.files = []
        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.add_files_button = QtWidgets.QPushButton("Add Files")
        self.add_folder_button = QtWidgets.QPushButton("Add Folder")
        self.remove_button = QtWidgets.QPushButton("Remove Selected")
        self.clear_button = QtWidgets.QPushButton("Clear List")
        self.move_up_button = QtWidgets.QPushButton("Move Up")
        self.move_down_button = QtWidgets.QPushButton("Move Down")
        self.sort_button = QtWidgets.QPushButton("Sort by Name")

        self.file_table = QtWidgets.QTableWidget(0, 4)
        self.file_table.setHorizontalHeaderLabels(["Enabled", "FBX File", "Path", "Status"])
        self.file_table.horizontalHeader().setStretchLastSection(False)
        self.file_table.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.file_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.file_table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.composition_edit = QtWidgets.QLineEdit("Main_Animation")
        self.track_edit = QtWidgets.QLineEdit("Source_Animations")
        self.start_spin = QtWidgets.QSpinBox()
        self.start_spin.setRange(-1000000, 1000000)
        self.gap_spin = QtWidgets.QSpinBox()
        self.gap_spin.setRange(0, 1000000)
        self.gap_spin.setValue(5)
        self.set_playback_check = QtWidgets.QCheckBox("Set Playback Range")
        self.set_playback_check.setChecked(True)
        self.create_missing_check = QtWidgets.QCheckBox("Create missing Composition / Track")
        self.validate_button = QtWidgets.QPushButton("Validate")
        self.import_button = QtWidgets.QPushButton("Import and Arrange")
        self.import_button.setMinimumHeight(34)
        self.log_edit = QtWidgets.QPlainTextEdit()
        self.log_edit.setReadOnly(True)
        self.status_label = QtWidgets.QLabel("Add FBX files, then validate.")
        self.status_label.setWordWrap(True)

    def create_layout(self):
        file_buttons = QtWidgets.QHBoxLayout()
        for button in (
            self.add_files_button, self.add_folder_button, self.remove_button,
            self.clear_button, self.move_up_button, self.move_down_button, self.sort_button,
        ):
            file_buttons.addWidget(button)
        files_layout = QtWidgets.QVBoxLayout()
        files_layout.addLayout(file_buttons)
        files_layout.addWidget(self.file_table)
        files_group = QtWidgets.QGroupBox("Animation Files")
        files_group.setLayout(files_layout)

        settings = QtWidgets.QGridLayout()
        settings.addWidget(QtWidgets.QLabel("Composition"), 0, 0)
        settings.addWidget(self.composition_edit, 0, 1)
        settings.addWidget(QtWidgets.QLabel("Track"), 0, 2)
        settings.addWidget(self.track_edit, 0, 3)
        settings.addWidget(QtWidgets.QLabel("Start Frame"), 1, 0)
        settings.addWidget(self.start_spin, 1, 1)
        settings.addWidget(QtWidgets.QLabel("Gap Frames"), 1, 2)
        settings.addWidget(self.gap_spin, 1, 3)
        settings.addWidget(self.set_playback_check, 2, 0, 1, 2)
        settings.addWidget(self.create_missing_check, 2, 2, 1, 2)
        settings_group = QtWidgets.QGroupBox("Time Editor Settings")
        settings_group.setLayout(settings)

        actions = QtWidgets.QHBoxLayout()
        actions.addStretch()
        actions.addWidget(self.validate_button)
        actions.addWidget(self.import_button)

        log_layout = QtWidgets.QVBoxLayout()
        log_layout.addWidget(self.log_edit)
        log_group = QtWidgets.QGroupBox("Log")
        log_group.setLayout(log_layout)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(files_group, 3)
        layout.addWidget(settings_group)
        layout.addLayout(actions)
        layout.addWidget(log_group, 2)
        layout.addWidget(self.status_label)

    def create_connections(self):
        self.add_files_button.clicked.connect(self.add_files)
        self.add_folder_button.clicked.connect(self.add_folder)
        self.remove_button.clicked.connect(self.remove_selected)
        self.clear_button.clicked.connect(self.clear_files)
        self.move_up_button.clicked.connect(self.move_up)
        self.move_down_button.clicked.connect(self.move_down)
        self.sort_button.clicked.connect(self.sort_files)
        self.validate_button.clicked.connect(self.validate_inputs)
        self.import_button.clicked.connect(self.import_and_arrange)
        self.file_table.itemChanged.connect(self._enabled_changed)

    def _add_paths(self, paths):
        known = {os.path.normcase(os.path.abspath(item.path)) for item in self.files}
        for path in paths:
            normalized = os.path.abspath(path)
            key = os.path.normcase(normalized)
            if key not in known and normalized.lower().endswith(".fbx"):
                self.files.append(AnimationFile(normalized))
                known.add(key)
        self.refresh_table()

    def add_files(self):
        paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self, "Add Animation FBX Files", "", "FBX Files (*.fbx)"
        )
        self._add_paths(paths)

    def add_folder(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Add FBX Folder")
        if folder:
            self._add_paths(
                os.path.join(folder, name) for name in os.listdir(folder)
                if name.lower().endswith(".fbx")
            )

    def selected_rows(self):
        return sorted({index.row() for index in self.file_table.selectedIndexes()})

    def remove_selected(self):
        for row in reversed(self.selected_rows()):
            del self.files[row]
        self.refresh_table()

    def clear_files(self):
        self.files[:] = []
        self.refresh_table()

    def move_up(self):
        rows = self.selected_rows()
        for row in rows:
            if row > 0 and row - 1 not in rows:
                self.files[row - 1], self.files[row] = self.files[row], self.files[row - 1]
        self.refresh_table()

    def move_down(self):
        rows = self.selected_rows()
        for row in reversed(rows):
            if row < len(self.files) - 1 and row + 1 not in rows:
                self.files[row + 1], self.files[row] = self.files[row], self.files[row + 1]
        self.refresh_table()

    def sort_files(self):
        self.files.sort(key=lambda item: os.path.basename(item.path).lower())
        self.refresh_table()

    def refresh_table(self):
        self.file_table.blockSignals(True)
        self.file_table.setRowCount(len(self.files))
        for row, item in enumerate(self.files):
            enabled = QtWidgets.QTableWidgetItem()
            enabled.setFlags(enabled.flags() | QtCore.Qt.ItemIsUserCheckable)
            enabled.setCheckState(QtCore.Qt.Checked if item.enabled else QtCore.Qt.Unchecked)
            self.file_table.setItem(row, 0, enabled)
            self.file_table.setItem(row, 1, QtWidgets.QTableWidgetItem(os.path.basename(item.path)))
            self.file_table.setItem(row, 2, QtWidgets.QTableWidgetItem(item.path))
            self.file_table.setItem(row, 3, QtWidgets.QTableWidgetItem(item.status))
        self.file_table.blockSignals(False)

    def _enabled_changed(self, item):
        if item.column() == 0 and 0 <= item.row() < len(self.files):
            self.files[item.row()].enabled = item.checkState() == QtCore.Qt.Checked

    def _report(self):
        return validation.validate(
            self.files,
            self.composition_edit.text().strip(),
            self.track_edit.text().strip(),
            self.start_spin.value(),
            self.gap_spin.value(),
            self.create_missing_check.isChecked(),
        )

    def validate_inputs(self):
        report = self._report()
        lines = ["Validation: {}".format("READY" if report.valid else "BLOCKED")]
        lines += ["ERROR: {}".format(value) for value in report.errors]
        lines += ["WARNING: {}".format(value) for value in report.warnings]
        self.log_edit.setPlainText("\n".join(lines))
        self.status_label.setText(lines[0])
        return report

    def append_log(self, message):
        self.log_edit.appendPlainText(message)
        QtWidgets.QApplication.processEvents()

    def import_and_arrange(self):
        report = self.validate_inputs()
        if not report.valid:
            QtWidgets.QMessageBox.warning(self, "Validation Blocked", "\n".join(report.errors))
            return
        if report.warnings:
            response = QtWidgets.QMessageBox.warning(
                self, "Import Warnings", "\n".join(report.warnings) + "\n\nContinue?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No,
            )
            if response != QtWidgets.QMessageBox.Yes:
                return
        self.import_button.setEnabled(False)
        self.append_log("--- Import started ---")
        try:
            result = BatchImporter(self.append_log).run(
                self.files,
                self.composition_edit.text().strip(),
                self.track_edit.text().strip(),
                self.start_spin.value(),
                self.gap_spin.value(),
                self.set_playback_check.isChecked(),
                self.create_missing_check.isChecked(),
            )
        except Exception as error:
            self.append_log("BATCH FAILED: {}".format(error))
            QtWidgets.QMessageBox.critical(self, "Batch Import Failed", str(error))
        else:
            self.status_label.setText(
                "Finished: {} succeeded, {} failed.".format(
                    len(result.segments), len(result.failures)
                )
            )
        finally:
            self.import_button.setEnabled(True)
            self.refresh_table()


def show():
    parent = maya_main_window()
    if parent:
        existing = parent.findChild(QtWidgets.QDialog, WINDOW_OBJECT_NAME)
        if existing:
            existing.close()
            existing.deleteLater()
    window = BatchImporterWindow(parent)
    window.show()
    window.raise_()
    window.activateWindow()
    return window
