# Maya Time Editor FBX Importer

适用于 Maya 2022 的简易 Time Editor FBX 批量导入工具。

工具按选择顺序逐个导入 FBX，将 Clip 放入当前激活 Composition 的第一条 Track，并在相邻 Clip 之间保留指定的 Gap Frames。当前 Composition 没有 Track 时，工具会自动创建第一条 Animation Track。UI 负责文件选择、参数输入和结果报告，核心导入逻辑保留在 `time_editor_test.py` 中。

## 当前功能

- 一次选择多个 FBX；
- 设置非负 Gap Frames，默认值为 5；
- 支持 Custom Start Frame；
- 支持 Append After Existing Clips；
- Active Composition 没有 Track 时自动创建 Animation Track；
- 可选统一播放倍速，支持 `0.10x–10.00x`；
- 支持 Standard Generate 和 Connect Existing Skeleton 两种骨骼导入模式；
- 显示成功 Clip 的名称、Start 和 End；
- 显示失败文件、错误信息及未处理数量；
- 防止重复打开工具窗口。

## Maya 中运行

导入前，请在 Time Editor 中激活一个 Composition。没有 Track 时，工具会自动创建第一条 Animation Track；工具不会自动创建 Composition。

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

请明确导入 `time_editor_import_ui`。不要使用：

```python
from maya_time_editor_batch import ui
```

目录中的旧 `ui.py` 不是当前工具入口，不包含最新功能。可通过下面的代码确认实际加载路径：

```python
print(time_editor_import_ui.__file__)
```

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

2. 打开 Maya 2022，并在 Time Editor 中激活一个 Composition。

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
2. Time Editor 中已有激活的 Composition；
3. 多个 FBX 按选择顺序生成 Clip；
4. Clip 间隔符合 Gap Frames；
5. Report 中的成功数、失败数、Start 和 End 正确；
6. 开启 Playback Speed 后，Clip 使用修改后的 End 排列下一段；
7. 导入失败后窗口和已选文件仍然保留，可直接重试。

## 骨骼导入模式

### Standard (Generate)

默认模式，继续使用 Maya 2022 的 `tePerformImportAnimFiles()` MEL 流程。适用于 FBX 骨骼和场景目标层级一致的情况。Maya 会尝试生成 FBX 中不存在于场景的节点；名称冲突时可能弹出 Rename Namespaces 窗口。

### Connect Existing Skeleton

只连接场景中已经存在且名称能够匹配的对象，不创建 FBX 中多余或已从 Target 删除的 Joint。适用于 Maya Target 是 FBX 完整骨骼的删减版本，例如删除裙子、饰品等非必要骨骼。

该模式要求保留下来的 Joint 名称能够匹配。Namespace 不一致、重名歧义或完全没有可匹配对象时，仍可能无法创建 Clip。

Maya 2022 的 Connect 导入可能在内部访问错误的完整 Time Slider UI 路径，例如遗漏动态生成的 `formLayout#` 层级。工具会在 Connect 命令执行期间，将 `$gPlayBackSlider` 临时切换为唯一有效的短名称（例如 `timeControl1`），导入结束后再恢复原始完整路径。Standard 模式不会执行该兼容处理。

## 已知限制

- 当前只导入到第一条 Track；
- 工具不会自动创建 Composition；
- 每个 FBX 预期只生成一个 Clip；
- 核心导入器遇到第一个失败后会停止后续导入；
- 倍速处理失败后会停止当前批次，并保留已创建的场景节点；
- Connect 模式不会自动重命名、重映射或补建缺失 Joint；
- 工具不会修改 HumanIK 设置。

## 已验证环境

- Maya 2022；
- `tePerformImportAnimFiles()` 导入 FBX；
- 通过 `timeWarpCurve` 设置统一播放倍速；
- 2.00x 倍速可正确缩短 Clip，并使用最终 End 排列下一段。
- Target 删除全部裙子骨骼后，Connect Existing Skeleton 模式仍可成功导入 FBX 并创建 Clip；
- Maya 2022 中，完整 Time Slider 路径包含 `formLayout#` 时可能被内部错误拼接；使用唯一短名称后，Connect 测试返回 Clip ID `[2]`，成功创建 `timeEditorClip2`，范围为约 `148.0281 → 290.0563`；
- 直接通过单条 MEL 表达式声明并读取 `$gPlayBackSlider` 会产生语法错误；测试和工具使用 MEL 包装函数读取该全局变量；
- Standard 模式继续保留原有 MEL Generate 导入行为。
