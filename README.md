# findRightGuy Skill

通过分析与前任的聊天记录，识别触发你正向情绪的对话特征，跨前任聚合提炼"理想对象画像"。

## 功能

| 命令 | 功能 |
|------|------|
| `/analyze-ex` | 导入新前任聊天记录，更新理想画像 |
| `/ideal-chat` | 与理想对象 AI 对话（持续学习） |
| `/export-template` | 导出最新恋爱模版 |
| `/advisor` | 恋爱顾问模式（分析新对象/主动咨询） |
| `/show-profile` | 查看当前理想对象画像摘要 |
| `/list-exes` | 查看所有已录入前任及贡献图谱 |
| `/rollback {version}` | 回滚到历史版本的理想画像 |

## 安装

```bash
# 安装到全局
npx skills add <owner/repo@findRightGuy> -g -y

# 安装 Python 依赖
pip install -r requirements.txt
```

## 快速开始

1. 导出微信或 QQ 聊天记录
2. 运行 `/analyze-ex`，按提示上传聊天记录
3. 分析完成后，运行 `/ideal-chat` 开始对话
4. 随时运行 `/export-template` 导出最新恋爱模版

## 数据安全

所有数据仅存储在本地 `data/` 目录，不上传任何服务器。
