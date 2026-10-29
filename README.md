# FPGA Competition Delivery

把 FPGA 参赛作品从"想法"推到"可提交、可验证、可复现"的交付流水线。

提炼自一个真实完成的参赛作品（XC7A35T，纯 RTL，16 项特性，LUT 37.91%、WNS +0.613ns、31 页技术文档、88 条沉淀经验、26 条证据索引）。

## 它解决什么

**这个项目里所有代价大的坑，根因都不是"没想到某个功能"，而是"某个结论从来没人独立验证过"。**

三例，都真实发生过：

| 现象 | 表象 | 真因 | 潜伏 |
|---|---|---|---|
| LUT 100.14% 无法布线 | 以为功能太多 | 波形缓存读口带异步复位 → 放弃块 RAM 推断 → 32768 位全铺 FDRE，单项吃 86% LUT | 25 天 |
| 锁相读数从未显示 | 以为算法错 | 该帧校验和含帧头（`5A+A5=0xFF≡−1`），上位机每帧判失败并**静默丢弃** | 从界面诞生起 |
| 两个功能"有按钮没反应" | 以为没写完 | 实例化漏接两端口，Verilog 当无驱动网络，**综合器零警告** | 从写成那天起 |

所以本流水线的每道门都设计成**可机械判定**：能跑脚本就别靠眼睛，能反抽下游产物就别只查源文件。

## 快速开始

```bash
# 1. 交付目录体检（缺件 / 空文件 / 中文名 / 过程文档残留）
python scripts/check_deliverables.py <交付目录> --required examples/required.example.json

# 2. 全库过期数字扫描
python scripts/audit_stale_numbers.py <仓库根> --map examples/stale_map.example.json

# 3. 从 PDF 反抽文字做合规扫描（禁项 / 过期值 / 近空白页）
python scripts/check_pdf_text.py <技术文档.pdf> \
    --banned examples/banned.example.txt --stale examples/stale.example.txt
```

三个脚本 exit code 全 0 才算过。**第 3 步不能用"查源文件"替代** —— 评委看的是 PDF。

依赖：Python 3.8+，第 3 个脚本需要 `pip install pdfplumber`。

## 目录

```
SKILL.md                         主文档：10 个阶段 + 判定阈值速查表
references/stage-gates.md        每道门的判据 + 不通过时的排查顺序
references/pitfalls.md           20 条可迁移的踩坑铁律
assets/audit-report-template.md  终审报告模板
examples/                        示例映射表、清单、填好的报告
scripts/                         三个可直接运行的检查脚本
```

## 边界

**它不管你做什么功能**，只管"你做的每个结论有没有被验证过、每份交付物有没有被查过"。

查不出来的东西：照片背景里的文字、图内嵌字、版式问题、现场表现、评委主观判断。这些必须在报告里写明"未覆盖"。

## License

MIT
