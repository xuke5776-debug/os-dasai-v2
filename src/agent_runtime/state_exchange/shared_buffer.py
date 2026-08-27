"""向量传输缓冲区。

支持通过 `multiprocessing.shared_memory` 进行大向量零拷贝传输（系统层机制证据）；
在不支持或失败时自动降级为进程内拷贝，保证跨平台可用。务必调用 `close()` 释放
共享内存句柄，避免资源泄漏。
"""

from __future__ import annotations

import numpy as np


class SharedVectorBuffer:
    """向量缓冲区，可选共享内存后端。"""

    def __init__(self, use_shared_memory: bool = False) -> None:
        self.use_shared_memory = use_shared_memory
        self._inproc: dict[str, np.ndarray] = {}
        self._shm: dict[str, tuple] = {}  # key -> (SharedMemory, shape, dtype)
        self._degraded = False

    @property
    def degraded(self) -> bool:
        """是否发生过从共享内存到进程内的降级。"""
        return self._degraded

    def put(self, key: str, array: np.ndarray) -> int:
        """存入向量，返回字节数。"""
        array = np.ascontiguousarray(array)
        if self.use_shared_memory:
            try:
                from multiprocessing import shared_memory

                shm = shared_memory.SharedMemory(create=True, size=max(array.nbytes, 1))
                buf = np.ndarray(array.shape, dtype=array.dtype, buffer=shm.buf)
                buf[...] = array[...]
                self._shm[key] = (shm, array.shape, array.dtype)
                return int(array.nbytes)
            except Exception:  # noqa: BLE001 - 共享内存不可用则降级
                self._degraded = True
        self._inproc[key] = array.copy()
        return int(array.nbytes)

    def get(self, key: str) -> np.ndarray:
        """取出向量（返回拷贝）。"""
        if key in self._shm:
            shm, shape, dtype = self._shm[key]
            view = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
            return np.array(view)  # 拷贝，避免悬挂引用
        if key in self._inproc:
            return self._inproc[key].copy()
        raise KeyError(key)

    def exists(self, key: str) -> bool:
        return key in self._shm or key in self._inproc

    def close(self) -> None:
        """释放所有共享内存句柄。"""
        for shm, _, _ in self._shm.values():
            try:
                shm.close()
                shm.unlink()
            except Exception:  # noqa: BLE001
                pass
        self._shm.clear()
        self._inproc.clear()


__all__ = ["SharedVectorBuffer"]
