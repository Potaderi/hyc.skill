# HYC

HYC 是一个运行在 Windows 桌面微信上的固定消息自动回复工具。启动并登录微信后，它会持续检查新消息，并对每条入站消息立即回复：

> 你以为这是真的？

它会忽略当前账号自己发送的消息、系统通知、撤回通知和时间分隔，避免产生自回复循环。

## 运行环境

- Windows 10 或 Windows 11
- Windows 桌面版微信（`WeChat.exe` 或 `Weixin.exe`）
- Python 3.10 或更高版本
- 首次运行时可访问 PyPI，以安装 `wxauto`

微信界面更新可能影响自动化库的兼容性。如果脚本无法连接微信，请先更新 `wxauto`，并确认当前微信版本受其支持。

## 快速开始

```powershell
git clone https://github.com/Potaderi/hyc.skill.git
cd hyc.skill
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

启动后：

1. 脚本会启动微信，或连接已经运行的微信。
2. 如果微信要求扫码或确认登录，请在微信窗口完成操作。
3. 终端显示 `HYC 已启动` 后，自动回复开始生效。
4. 在终端按 `Ctrl+C` 停止自动回复。

首次运行会在 `%LOCALAPPDATA%\hyc-skill\.venv` 创建独立 Python 环境并安装依赖，不会修改仓库内的文件。

## 启动参数

| 参数 | 作用 | 示例 |
| --- | --- | --- |
| `-PollInterval` | 设置消息检查间隔，单位为秒，最小值为 `0.1` | `-PollInterval 0.5` |
| `-NoInstall` | 禁止自动安装 `wxauto`；依赖不存在时直接报错 | `-NoInstall` |
| `-SelfTest` | 运行离线自测，不启动微信、不安装依赖 | `-SelfTest` |

例如，将检查间隔调整为 0.5 秒：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -PollInterval 0.5
```

## 离线自测

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1 -SelfTest
```

自测覆盖以下行为：

- 识别并处理入站消息
- 忽略本人消息和系统消息
- 对每条入站消息只生成一次固定回复
- 兼容 `wxauto` 的两种新消息轮询接口

自测不会打开微信，也不会真实发送消息。

## 工作方式

`scripts/start.ps1` 负责检查 Python、创建隔离环境、安装 `wxauto` 并启动工作进程。`scripts/wechat_auto_reply.py` 负责查找微信、等待登录、轮询消息、过滤非入站事件并发送固定回复。

默认每 0.3 秒检查一次新消息。私聊和群聊是否能被发现，取决于当前微信版本及 `wxauto` 暴露的消息列表。

## 注意事项

- 自动回复会以当前已登录微信账号的身份发送消息，请先确认账号和会话范围。
- 高频消息可能产生大量回复，也可能触发微信的频率限制或风控。
- 本项目不读取或保存微信密码，不绕过登录，也不使用进程注入或消息钩子。
- 微信与 `wxauto` 均可能更新界面或接口，因此无法保证所有客户端版本长期兼容。
- 请仅在你有权操作的账号和设备上使用，并自行遵守微信的使用规则。

## 项目结构

```text
.
|-- SKILL.md                       # Codex 技能说明
|-- agents/openai.yaml             # 技能界面元数据
`-- scripts/
    |-- start.ps1                  # Windows 启动器
    `-- wechat_auto_reply.py       # 自动回复工作进程
```

## 停止与清理

在运行终端按 `Ctrl+C` 即可停止。若不再使用，可在确认脚本已停止后删除 `%LOCALAPPDATA%\hyc-skill`，其中仅包含该工具创建的 Python 虚拟环境和依赖。
