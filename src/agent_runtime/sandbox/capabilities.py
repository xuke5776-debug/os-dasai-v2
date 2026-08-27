"""系统能力探测（用于沙箱后端选择与 openEuler 兼容报告）。"""

from __future__ import annotations

import os
import shutil
import socket


def has_rlimit() -> bool:
    """是否支持 resource.setrlimit（POSIX）。"""
    if os.name != "posix":
        return False
    try:
        import resource  # noqa: F401

        return True
    except ImportError:
        return False


def has_cgroup_v2() -> bool:
    """是否挂载了 cgroup v2。"""
    return os.path.isfile("/sys/fs/cgroup/cgroup.controllers")


def has_namespaces() -> bool:
    """是否支持 Linux namespace（粗略判断）。"""
    return os.path.isdir("/proc/self/ns")


def has_shared_memory() -> bool:
    """/dev/shm 是否可用可写。"""
    return os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK)


def has_unix_socket() -> bool:
    """是否支持 Unix Domain Socket。"""
    return hasattr(socket, "AF_UNIX")


def has_podman() -> bool:
    return shutil.which("podman") is not None


def has_bubblewrap() -> bool:
    return shutil.which("bwrap") is not None


def summary() -> dict[str, bool]:
    """返回能力概览。"""
    return {
        "rlimit": has_rlimit(),
        "cgroup_v2": has_cgroup_v2(),
        "namespaces": has_namespaces(),
        "shared_memory": has_shared_memory(),
        "unix_socket": has_unix_socket(),
        "podman": has_podman(),
        "bubblewrap": has_bubblewrap(),
    }


def select_backend(requested: str) -> str:
    """根据请求与可用能力选择实际后端（不可用时降级到 subprocess）。"""
    requested = (requested or "subprocess").lower()
    if requested == "podman" and has_podman():
        return "podman"
    if requested == "cgroup" and has_cgroup_v2() and has_rlimit():
        return "cgroup"
    return "subprocess"


__all__ = [
    "has_rlimit",
    "has_cgroup_v2",
    "has_namespaces",
    "has_shared_memory",
    "has_unix_socket",
    "has_podman",
    "has_bubblewrap",
    "summary",
    "select_backend",
]
