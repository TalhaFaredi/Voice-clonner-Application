# Mellifon · 声音克隆与语音生成平台

[English](../../README.md) · [所有文档语言](README.md)

Mellifon 是独立运行的声音克隆 SaaS 项目，全部应用代码位于 `Voice-clonner-Application/`。它不导入或调用原有的 YouTube 应用。

## 功能与状态

- 注册、登录、密码重置、个人资料和私人声音库。
- 上传声音样本、保存克隆声音、文字转语音、音频试听、WAV 下载和生成历史。
- 独立的后台任务进程、SQLite 数据库、积分预扣、失败退款和用量记录。
- Stripe 订阅、结账、客户门户和签名验证的 webhook 集成。

本地声音克隆和语音生成已经通过真实 GPU 测试。正式开放服务前，仍需配置并验证 Stripe、SMTP 邮件、HTTPS、备份和监控。不能将模拟支付测试视为真实支付验证。

## 安装与启动（Windows / PowerShell）

需要 Python 3.12、uv，以及适合 CUDA 的 NVIDIA GPU。模型首次启动时下载；请为模型和 PyTorch 预留数 GB 的磁盘空间。推荐安装方式：

```powershell
git clone https://github.com/TalhaFaredi/Voice-clonner-Application.git
cd Voice-clonner-Application
uv sync --extra worker --extra dev
if (-not (Test-Path backend/.env)) { Copy-Item backend/.env.example backend/.env }
```

在项目目录下打开三个独立的 PowerShell 终端，分别运行以下一条命令：

```powershell
./scripts/start.ps1 api
./scripts/start.ps1 worker
./scripts/start.ps1 frontend
```

打开 **http://localhost:5173**，自行注册账号。API 地址为 `http://localhost:8010/api/health`。免费账户获得一次性的 5,000 积分；每个文字字符消耗 1 积分，每次声音克隆消耗 1,000 积分。前端和 API 应使用相同主机名。

## GPU 与语言

默认 `TTS_DEVICE=cuda:0` 使用第一块 NVIDIA GPU。已在具有 48 GB 显存的 NVIDIA RTX A6000 上验证；这不是最低硬件要求或速度保证。使用 `nvidia-smi` 检查 GPU。也可在 `backend/.env` 中设置 `TTS_DEVICE=cpu`，但速度较慢。更改设置后重启 worker，并等待 `/api/studio/options` 中的 `worker.status` 变为 `ready`。

支持中文、英语、日语、韩语、德语、法语、俄语、葡萄牙语、西班牙语和意大利语。`auto` 可自动识别脚本语言。语言选项用于生成语音，不会翻译脚本。界面目前为英语。

## 验证与部署

13 项后端测试以及桌面和移动端浏览器检查已通过，并已完成真实的预设语音 → 保存克隆 → 生成语音流程。声音引擎使用本地 Qwen3-TTS，不需要第三方语音 API 密钥。Stripe 与 SMTP 仍需单独配置。不要提交 `.env`、私人音频或数据库。

[完整说明](../../README.md) · [部署与配置](../setup.md) · [API](../api.md) · [验证记录](../verification.md)
