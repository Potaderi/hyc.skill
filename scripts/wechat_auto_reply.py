#!/usr/bin/env python3
"""Reply to every incoming desktop WeChat message with a fixed phrase."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any


REPLY_TEXT = "你以为这是真的？"
IGNORED_TYPES = {
    "self",
    "sys",
    "system",
    "time",
    "recall",
    "recalled",
    "notice",
}
WECHAT_EXECUTABLES = ("Weixin.exe", "WeChat.exe")


@dataclass(frozen=True)
class IncomingMessage:
    conversation: Any
    message: Any


def _get_value(item: Any, *names: str) -> Any:
    if isinstance(item, Mapping):
        for name in names:
            if name in item:
                return item[name]
        return None
    for name in names:
        value = getattr(item, name, None)
        if value is not None:
            return value
    return None


def _message_type(message: Any) -> str:
    value = _get_value(message, "type", "attr", "kind")
    if value is None and isinstance(message, (list, tuple)) and message:
        value = message[0]
    return str(value or "").strip().lower()


def is_incoming(message: Any) -> bool:
    """Return false only for message classes known not to be inbound chat data."""
    return _message_type(message) not in IGNORED_TYPES


def _as_message_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, (str, bytes, Mapping)):
        return [value]
    if isinstance(value, Iterable):
        return list(value)
    return [value]


def normalize_batches(raw: Any) -> list[IncomingMessage]:
    """Normalize the mapping and chat-batch shapes returned by wxauto 3.x."""
    if not raw:
        return []

    normalized: list[IncomingMessage] = []
    if isinstance(raw, Mapping):
        batches = raw.items()
    else:
        conversation = _get_value(raw, "chat", "conversation", "who")
        batches = [(conversation, raw)]

    for conversation, messages in batches:
        batch_conversation = _get_value(messages, "chat", "conversation") or conversation
        for message in _as_message_list(messages):
            if is_incoming(message):
                normalized.append(IncomingMessage(batch_conversation, message))
    return normalized


def _send_with_chat(conversation: Any) -> bool:
    for method_name in ("SendMsg", "send_msg", "send"):
        method = getattr(conversation, method_name, None)
        if callable(method):
            try:
                method(REPLY_TEXT)
            except TypeError:
                method(msg=REPLY_TEXT)
            return True
    return False


def send_reply(client: Any, conversation: Any) -> None:
    if conversation is not None and _send_with_chat(conversation):
        return

    target = _get_value(conversation, "who", "name") or conversation
    if target is None:
        raise RuntimeError("wxauto returned a message without a reply target")

    method = getattr(client, "SendMsg", None)
    if not callable(method):
        raise RuntimeError("wxauto does not expose a supported SendMsg method")
    try:
        method(msg=REPLY_TEXT, who=target)
    except TypeError:
        method(REPLY_TEXT, target)


def _process_is_running() -> bool:
    command = ["tasklist", "/NH", "/FO", "CSV"]
    try:
        result = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except OSError:
        return False
    output = result.stdout.lower()
    return "wechat.exe" in output or "weixin.exe" in output


def _registry_install_paths() -> list[Path]:
    try:
        import winreg
    except ImportError:
        return []

    paths: list[Path] = []
    keys = (
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\WeChat"),
        (winreg.HKEY_CURRENT_USER, r"Software\Tencent\Weixin"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Tencent\Weixin"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Tencent\WeChat"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Tencent\Weixin"),
    )
    for hive, key_name in keys:
        try:
            with winreg.OpenKey(hive, key_name) as key:
                value, _ = winreg.QueryValueEx(key, "InstallPath")
                paths.append(Path(value))
        except OSError:
            continue
    return paths


def _candidate_executables() -> Iterable[Path]:
    roots = [
        os.environ.get("ProgramFiles"),
        os.environ.get("ProgramFiles(x86)"),
        os.environ.get("LOCALAPPDATA"),
    ]
    install_paths = _registry_install_paths()
    install_paths.extend(Path(root) / "Tencent" / "WeChat" for root in roots if root)
    install_paths.extend(Path(root) / "Tencent" / "Weixin" for root in roots if root)
    for install_path in install_paths:
        if install_path.suffix.lower() == ".exe":
            yield install_path
            continue
        for executable in WECHAT_EXECUTABLES:
            yield install_path / executable


def launch_wechat() -> None:
    if _process_is_running():
        return
    for executable in _candidate_executables():
        if executable.is_file():
            subprocess.Popen([str(executable)], close_fds=True)
            return
    try:
        os.startfile("weixin://")  # type: ignore[attr-defined]
    except OSError:
        print("未找到微信。请手动启动 Windows 桌面微信。", flush=True)


def connect_wechat() -> Any:
    try:
        from wxauto import WeChat
    except ImportError as exc:
        raise RuntimeError("wxauto is not installed; run scripts/start.ps1") from exc

    print("请在微信窗口完成登录；HYC 正在等待主界面...", flush=True)
    last_error: Exception | None = None
    while True:
        try:
            return WeChat()
        except Exception as exc:  # wxauto raises UI-backend-specific errors.
            last_error = exc
            time.sleep(2.0)
            if not _process_is_running():
                launch_wechat()
        if last_error and not _process_is_running():
            print(f"仍在等待微信登录：{last_error}", flush=True)


def poll_messages(client: Any) -> list[IncomingMessage]:
    all_new = getattr(client, "GetAllNewMessage", None)
    if callable(all_new):
        return normalize_batches(all_new())

    next_new = getattr(client, "GetNextNewMessage", None)
    if callable(next_new):
        collected: list[IncomingMessage] = []
        while True:
            batch = next_new()
            if not batch:
                break
            collected.extend(normalize_batches(batch))
        return collected

    raise RuntimeError(
        "This wxauto build exposes neither GetAllNewMessage nor GetNextNewMessage"
    )


def run_worker(poll_interval: float) -> None:
    if sys.platform != "win32":
        raise RuntimeError("HYC requires Windows desktop WeChat")
    launch_wechat()
    client = connect_wechat()
    print(f"HYC 已启动：收到消息将立即回复“{REPLY_TEXT}”。按 Ctrl+C 停止。", flush=True)

    while True:
        try:
            for incoming in poll_messages(client):
                send_reply(client, incoming.conversation)
            time.sleep(poll_interval)
        except KeyboardInterrupt:
            print("\nHYC 已停止。", flush=True)
            return
        except Exception as exc:
            print(f"处理消息失败，将继续重试：{exc}", file=sys.stderr, flush=True)
            time.sleep(max(1.0, poll_interval))


class _FakeMessage:
    def __init__(self, message_type: str) -> None:
        self.type = message_type


class _FakeChat:
    def __init__(self) -> None:
        self.sent: list[str] = []

    def SendMsg(self, text: str) -> None:
        self.sent.append(text)


class _FakeClient:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def SendMsg(self, msg: str, who: str) -> None:
        self.sent.append((msg, who))


class _FakeAllNewClient(_FakeClient):
    def __init__(self, batches: Mapping[Any, Any]) -> None:
        super().__init__()
        self.batches = batches

    def GetAllNewMessage(self) -> Mapping[Any, Any]:
        return self.batches


class _FakeNextNewClient(_FakeClient):
    def __init__(self, batches: list[Any]) -> None:
        super().__init__()
        self.batches = iter(batches)

    def GetNextNewMessage(self) -> Any:
        return next(self.batches, None)


def self_test() -> None:
    chat = _FakeChat()
    batches = {
        chat: [
            _FakeMessage("friend"),
            _FakeMessage("image"),
            _FakeMessage("self"),
            _FakeMessage("sys"),
            _FakeMessage("time"),
        ]
    }
    incoming = normalize_batches(batches)
    assert len(incoming) == 2, incoming
    assert len(poll_messages(_FakeAllNewClient(batches))) == 2
    assert len(poll_messages(_FakeNextNewClient([batches, None]))) == 2
    for item in incoming:
        send_reply(_FakeClient(), item.conversation)
    assert chat.sent == [REPLY_TEXT, REPLY_TEXT], chat.sent

    client = _FakeClient()
    send_reply(client, "测试会话")
    assert client.sent == [(REPLY_TEXT, "测试会话")], client.sent
    print("HYC self-test passed.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--poll-interval", type=float, default=0.3)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.poll_interval < 0.1:
        parser.error("--poll-interval must be at least 0.1 seconds")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test:
        self_test()
        return 0
    try:
        run_worker(args.poll_interval)
    except RuntimeError as exc:
        print(f"HYC error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
