# Maya Time Editor FBX Importer

适用于 Maya 2022 的简易 Time Editor FBX 批量导入工具。

工具按选择顺序逐个导入 FBX，将 Clip 放入当前激活 Composition 的第一条 Track，并在相邻 Clip 之间保留指定的 Gap Frames。UI 仅负责文件选择、参数输入和结果报告，核心导入逻辑保留在 `time_editor_test.py` 中。

## 当前功能

- 一次选择多个 FBX；
- 设置非负 Gap Frames，默认值为 5；
- 固定使用 `track_index=0`、`start_time=0`；
- 显示成功 Clip 的名称、Start 和 End；
- 显示失败文件、错误信息及未处理数量；
- 防止重复打开工具窗口。

## Maya 中运行

导入前，请在 Time Editor 中激活一个 Composition，并确保其中至少有一条 Track。

在 Maya Script Editor 的 **Python** 页签执行：

```python
import sys
import importlib

tools_path = r"D:\tools"
if tools_path not in sys.path:
    sys.path.insert(0, tools_path)

from maya_time_editor_batch import time_editor_import_ui
importlib.reload(time_editor_import_ui)

window = time_editor_import_ui.show()
```

`sys.path` 的修改只在当前 Maya 会话中有效。

## ZIP 包内容

ZIP 包应包含以下目录：

```text
maya_time_editor_batch/
├── __init__.py
├── time_editor_test.py
├── time_editor_import_ui.py
└── README.md
```

ZIP 包不包含 `__pycache__`、`.pyc` 文件、测试 FBX 或个人工程文件。

## ZIP 使用方式

1. 将 ZIP 解压到一个固定位置，例如：

   ```text
   D:\maya_tools\maya_time_editor_batch
   ```

2. 打开 Maya 2022，并在 Time Editor 中激活一个 Composition，确保其中至少有一条 Track。

3. 打开 Maya Script Editor，切换到 **Python** 页签。

4. 将 `package_parent` 设置为 `maya_time_editor_batch` 文件夹的上一级目录，然后运行：

```python
import sys

package_parent = r"D:\maya_tools"
if package_parent not in sys.path:
    sys.path.insert(0, package_parent)

from maya_time_editor_batch import time_editor_import_ui
time_editor_import_ui.show()
```

这里应加入的是包的上一级目录，例如包位于 `D:\maya_tools\maya_time_editor_batch`，则填写 `D:\maya_tools`。

该设置只在当前 Maya 会话中有效。重新启动 Maya 后，需要再次运行上述代码。

## 使用检查项

首次使用前建议保存场景，并确认：

1. Maya 版本为 2022，FBX 可正常读取；
2. Time Editor 中已有激活的 Composition 和至少一条 Track；
3. 多个 FBX 按选择顺序生成 Clip；
4. Clip 间隔符合 Gap Frames；
5. Report 中的成功数、失败数、Start 和 End 正确；
6. 导入失败后窗口和已选文件仍然保留，可直接重试。

## 已知限制

- 核心导入器遇到第一个失败后会停止后续导入；
- 工具不会创建 Composition、Track，也不会修改 HumanIK 设置。
