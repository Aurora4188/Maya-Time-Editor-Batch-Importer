# Time Editor Batch Importer — MVP1

Batch-import FBX animation files as Maya Time Editor clips, keep them on one
chosen track, and arrange them in queue order using each clip's queried range.

## Scope and safety

This version does not create or edit HumanIK definitions/connections, bake
retargeting, export animation, process root motion, or delete existing Time
Editor content. It never falls back to `cmds.file(..., i=True)`.

FBX import uses `maya.cmds.timeEditorClip` with `importFbx`. Maya's documented
default import mode is `connect`: it targets matching nodes already in the scene
and does not request generation of a new skeleton. The adapter intentionally
does not pass the version-sensitive `importOption` flag during clip creation.
Windows paths are converted to forward slashes before Maya 2022 hands them to
its internal MEL procedures. A failed name match is reported as an import
failure.

## Install and launch

Place the `Projects` folder on `MAYA_SCRIPT_PATH`, or add its absolute path to
`sys.path`, then run in Maya's Python Script Editor:

```python
import sys

projects_path = r"D:/path/to/CharacterTA_Lab/Projects"
if projects_path not in sys.path:
    sys.path.insert(0, projects_path)

import TimeEditorBatchImporter
TimeEditorBatchImporter.show()
```

Repeated `show()` calls close the existing window before opening a replacement.

## Workflow

1. Prepare the Source and Target HumanIK setup manually.
2. Add FBX files or a folder, enable/reorder items, and set Composition, Track,
   Start Frame, and Gap Frames.
3. Enable **Create missing Composition / Track** only when creation is wanted.
4. Click **Validate**. Existing clips produce a warning and are never moved.
5. Click **Import and Arrange**, review any warning, then inspect the log.

For a clip with queried absolute range `0-30`, the tool records 31 occupied
frames. With Gap Frames `5`, the next clip starts at `36`, leaving `31-35`
empty. Arrangement uses queried absolute `end`, not an assumed FBX length.

## Required Maya smoke test

The current repository has no Maya executable, FBX fixtures, or configured
Source skeleton, so the Time Editor calls have not been executed in a real Maya
session. Before a production batch, use one representative FBX:

```python
from TimeEditorBatchImporter import maya_smoke_test

result = maya_smoke_test.run(r"D:/Animations/AS_Idle.fbx")
print(result)
```

Verify all of the following manually:

- exactly one Animation Source and one clip were created;
- the existing Source skeleton is driven and no second skeleton appeared;
- `start`, `end`, `maya_duration`, and `inclusive_frame_count` describe the
  expected animation without an off-by-one error;
- `next_start_gap_5` leaves exactly five empty frames;
- the current HumanIK Source/Target connection is unchanged.

The log records both Maya's raw `duration` and the inclusive occupied frame
count. Maya documentation calls duration a relative duration, but this tool does
not assume whether a particular Maya/FBX combination reports a time difference
or an inclusive frame count.

## Version notes and known limitations

- UI import prefers PySide2/shiboken2 and safely falls back to
  PySide6/shiboken6.
- Time Editor command behavior must be checked in the target Maya release.
- Namespace/name mismatches are not guessed or automatically remapped in MVP1.
- A target track containing clips requires confirmation. Each new queried range
  is checked against existing clip ranges; on conflict only the newly created
  clip is removed and that file is reported failed.
- FBX/Time Editor operations may not be completely undoable in every Maya/FBX
  plug-in version. The batch is grouped in one Undo Chunk, but do not treat Undo
  as the only recovery plan; save the scene first.
- Folder scanning is intentionally non-recursive.
- Composition/Track creation is explicit; same-named existing content is never
  deleted or overwritten.

## Development checks outside Maya

The timing math can be checked without Maya:

```bash
python -m unittest discover Projects/TimeEditorBatchImporter/tests
```

Full import validation still requires Maya and representative FBX files.
