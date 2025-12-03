"""TDX连接池管理"""
import queue
import time
from threading import Thread
from typing import Dict, Any, Optional

from pytdx.hq import TdxHq_API

from config import TDX_SERVERS


class TDXConnectionPool:
    """TDX连接池，管理与TDX服务器的连接"""
    
    def __init__(
        self,
        max_connections: int = 10,
        timeout: int = 2,
        test_interval: int = 300,
        default_server: Optional[Dict[str, Any]] = None
    ):
        self.max_connections = max_connections
        self.timeout = timeout
        self.test_interval = test_interval
        self._connection_pool = queue.Queue(maxsize=max_connections)
        self.server = default_server or TDX_SERVERS[0]
        self._connection_worker = Thread(target=self._connection_worker_thread, daemon=True)
        self._connection_worker.start()

    def set_server(self, server: Dict[str, Any]):
        """设置当前服务器"""
        self.server = server

    def _create_connection(self) -> Optional[TdxHq_API]:
        """创建新连接"""
        api = TdxHq_API()
        ok = False
        try:
            ok = api.connect(self.server["ip"], self.server["port"])
        except Exception:
            ok = False
        if ok:
            return api
        try:
            api.disconnect()
        except Exception:
            pass
        return None

    def _connection_worker_thread(self):
        """后台连接维护线程"""
        while True:
            try:
                if self._connection_pool.qsize() < self.max_connections:
                    api = self._create_connection()
                    if api is not None:
                        try:
                            self._connection_pool.put(api)
                        except Exception:
                            try:
                                api.disconnect()
                            except Exception:
                                pass
                time.sleep(self.test_interval)
            except Exception:
                time.sleep(5)

    def get_connection(self) -> Optional[TdxHq_API]:
        """获取连接"""
        try:
            if not self._connection_pool.empty():
                return self._connection_pool.get_nowait()
            api = self._create_connection()
            return api
        except Exception:
            return None

    def return_connection(self, api: TdxHq_API):
        """归还连接"""
        try:
            if api and not self._connection_pool.full():
                self._connection_pool.put_nowait(api)
            else:
                try:
                    api.disconnect()
                except Exception:
                    pass
        except Exception:
            try:
                api.disconnect()
            except Exception:
                pass

    def close_all(self):
        """关闭所有连接"""
        while not self._connection_pool.empty():
            try:
                api = self._connection_pool.get_nowait()
                try:
                    api.disconnect()
                except Exception:
                    pass
            except Exception:
                pass

    def reset_pool(self):
        """重置连接池"""
        try:
            while not self._connection_pool.empty():
                api = self._connection_pool.get_nowait()
                try:
                    api.disconnect()
                except Exception:
                    pass
        except Exception:
            pass


# 全局连接池实例
tdx_connection_pool = TDXConnectionPool(
    max_connections=5,
    timeout=2,
    default_server=TDX_SERVERS[0]
)

