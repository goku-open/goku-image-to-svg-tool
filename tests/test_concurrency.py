"""并发保护测试：最多 2 个用户同时转换，第 3 个立即返回繁忙提示。"""
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest


def _slow_task(sem, result, idx):
    """模拟耗时转换任务，占用 semaphore 一段时间。"""
    acquired = sem.acquire(blocking=False)
    if not acquired:
        result[idx] = "busy"
        return
    try:
        time.sleep(0.5)  # 模拟转换耗时
        result[idx] = "ok"
    finally:
        sem.release()


class TestConcurrencyLimit:
    def test_semaphore_allows_two_concurrent(self):
        """2 个并发任务应全部成功。"""
        from utils import _TRACE_SEM
        result = [None] * 2
        threads = [
            threading.Thread(target=_slow_task, args=(_TRACE_SEM, result, i))
            for i in range(2)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=3)
        assert result == ["ok", "ok"]

    def test_semaphore_rejects_third_concurrent(self):
        """第 3 个并发任务应立即返回 busy。"""
        from utils import _TRACE_SEM
        result = [None] * 3
        # 先启动 2 个慢任务占住锁
        blockers = []
        for i in range(2):
            t = threading.Thread(target=_slow_task, args=(_TRACE_SEM, result, i))
            blockers.append(t)
            t.start()
        time.sleep(0.1)  # 确保 2 个都已拿到锁

        # 第 3 个任务立即尝试
        third = threading.Thread(target=_slow_task, args=(_TRACE_SEM, result, 2))
        third.start()
        third.join(timeout=1)

        for t in blockers:
            t.join(timeout=2)

        assert result[2] == "busy", "第 3 个并发调用应被拒绝"
        assert result[:2].count("ok") == 2

    def test_semaphore_releases_after_completion(self):
        """任务完成后其他用户可正常进入。"""
        from utils import _TRACE_SEM
        result = [None] * 2
        # 占满 2 个槽位
        blockers = []
        for i in range(2):
            t = threading.Thread(target=_slow_task, args=(_TRACE_SEM, [None]*2, 0))
            blockers.append(t)
            t.start()
        time.sleep(0.1)
        # 此时第 3 个被拒绝
        r3 = [None]
        threading.Thread(target=_slow_task, args=(_TRACE_SEM, r3, 0)).start()
        time.sleep(0.1)
        assert r3[0] == "busy"

        # 等 block 释放
        for t in blockers:
            t.join(timeout=2)

        # 第 4 个任务应成功
        r4 = [None]
        t4 = threading.Thread(target=_slow_task, args=(_TRACE_SEM, r4, 0))
        t4.start()
        t4.join(timeout=2)
        assert r4[0] == "ok"