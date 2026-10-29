# 安装说明

这是一个 WorkBuddy / Claude Code 风格的 skill（一个目录 + `SKILL.md` + 可选 `scripts/`）。

## 方式一：手动拷贝（最稳，推荐）

skill 的本质就是一个目录，放到 skills 目录下即可。

**WorkBuddy（用户级，所有项目可用）**

```bash
# Windows Git Bash
git clone https://github.com/2478483557-ship-it/fpga-competition-delivery.git \
  ~/.workbuddy/skills/fpga-competition-delivery
```

```powershell
# Windows PowerShell
git clone https://github.com/2478483557-ship-it/fpga-competition-delivery.git `
  "$env:USERPROFILE\.workbuddy\skills\fpga-competition-delivery"
```

**Claude Code（用户级）**

```bash
git clone https://github.com/2478483557-ship-it/fpga-competition-delivery.git \
  ~/.claude/skills/fpga-competition-delivery
```

**只想用不追踪更新**：下载 zip 解压到同名目录也可以，去不去掉 `.git` 都行。

### 装完要重启

WorkBuddy 在启动时扫描 skills 目录，并把结果写进 `~/.workbuddy/.skill-list-cache.json`。
**新装完必须重启应用**（或打开「设置 → 技能」页面触发重新扫描），否则当前会话看不到它。

验证：设置 → 技能，列表里应出现 `fpga-competition-delivery`。

## 方式二：项目级安装（只在某个项目里生效）

放到项目根目录：

```
<你的项目>/.workbuddy/skills/fpga-competition-delivery/
```

适合"这套流水线只给这个工程用"，不会污染全局。

## 依赖

- Python 3.8+
- 只有 `scripts/check_pdf_text.py` 需要额外装：

```bash
pip install pdfplumber
```

另外两个脚本纯标准库，无依赖。

## 装完怎么用

直接说话就行，skill 描述里写了触发词：

```
帮我检查一下提交物齐不齐
文档里的数字和实际对不对，帮我把旧数据都清一遍
整理一下打包，顺便核一下 md5
这个 FPGA 工程 LUT 用到 90% 了还能加功能吗
```

也可以显式调用：`/fpga-competition-delivery`

## 三个脚本也可以单独用

不装 skill 也能直接跑：

```bash
python scripts/check_deliverables.py <交付目录> --required examples/required.example.json
python scripts/audit_stale_numbers.py <仓库根> --map examples/stale_map.example.json
python scripts/check_pdf_text.py <技术文档.pdf> \
    --banned examples/banned.example.txt --stale examples/stale.example.txt
```

退出码 0 = 全绿。第 3 个脚本**必须对生成的 PDF 跑**，不要对源文件跑。
