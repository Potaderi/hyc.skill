---
name: hyc
description: Start and operate a Windows desktop WeChat auto-reply worker that answers every incoming chat message immediately with the fixed Chinese text "你以为这是真的？". Use when the user asks to run HYC, launch WeChat and enable the fixed reply, or automate this exact response after WeChat login.
---

# HYC

Run a local Windows worker that opens or attaches to desktop WeChat, waits for the user to finish login, and replies once to each incoming message with `你以为这是真的？`.

## Start the worker

1. Confirm the host is Windows and that desktop WeChat is installed.
2. Run from this skill directory:

   ```powershell
   powershell -ExecutionPolicy Bypass -File scripts/start.ps1
   ```

3. Tell the user to complete WeChat login if a QR code or login confirmation appears.
4. Keep the process running. Stop it with `Ctrl+C`.

The launcher creates an isolated environment under `%LOCALAPPDATA%\hyc-skill`, installs a compatible `wxauto` release on first use, and then starts `scripts/wechat_auto_reply.py`.

## Preserve the fixed behavior

- Keep the reply exactly `你以为这是真的？` unless the user explicitly requests a different message.
- Reply once per incoming message, including non-text messages exposed by WeChat automation.
- Ignore messages sent by the logged-in account, system notices, recalled-message notices, and timeline separators to prevent feedback loops.
- Poll every 0.3 seconds by default. Use `-PollInterval <seconds>` only when the user requests a different latency or CPU tradeoff.
- Do not bypass WeChat login, collect credentials, or use injection and process-hooking techniques.

## Verify without sending messages

Run the offline self-test after changing the worker:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start.ps1 -SelfTest
```

The self-test does not open WeChat and does not install `wxauto`.

## Troubleshoot

- If Python is missing, install Python 3.10 or newer and rerun the launcher.
- If WeChat cannot be found, start desktop WeChat manually and rerun the launcher.
- If `wxauto` cannot attach, update `wxauto` first. Current WeChat UI releases can change their accessibility controls; a newly released client may require a matching automation-library update.
- If installation fails, check access to PyPI and rerun. Do not silently replace the automation library with an untrusted WeChat hook.
