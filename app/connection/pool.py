"""TDX连接池管理 - 支持多服务器、失败重试和自动切换"""
import queue
import time
import threading
from threading import Thread, Lock
from typing import Dict, Any, Optional, List, Tuple

from pytdx.hq import TdxHq_API

from config import TDX_SERVERS


class ServerStatus:
    """服务器状态"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TDXConnectionPool:
    """TDX连接池，支持多服务器管理、失败重试和自动切换"""

    def __init__(
        self,
        servers: List[Dict[str, Any]] = None,
        max_connections: int = 5,
        connect_timeout: int = 3,
        retry_times: int = 3,
        health_check_interval: int = 60,
        unhealthy_threshold: int = 3,
        recovery_time: int = 300
    ):
        """
        初始化连接池

        Args:
            servers: 服务器列表
            max_connections: 每个服务器的最大连接数
            connect_timeout: 连接超时时间(秒)
            retry_times: 单次操作重试次数
            health_check_interval: 健康检查间隔(秒)
            unhealthy_threshold: 连续失败多少次标记为不健康
            recovery_time: 不健康服务器恢复检查间隔(秒)
        """
        self.servers = servers or TDX_SERVERS.copy()
        self.max_connections = max_connections
        self.connect_timeout = connect_timeout
        self.retry_times = retry_times
        self.health_check_interval = health_check_interval
        self.unhealthy_threshold = unhealthy_threshold
        self.recovery_time = recovery_time

        # 当前主服务器索引
        self._current_server_index = 0

        # 服务器状态: {ip: {"status": status, "fail_count": n, "last_fail_time": t}}
        self._server_status: Dict[str, Dict[str, Any]] = {}
        for server in self.servers:
            self._server_status[server["ip"]] = {
                "status": ServerStatus.UNKNOWN,
                "fail_count": 0,
                "last_fail_time": 0,
                "last_success_time": 0
            }

        # 连接池 (每个服务器一个队列)
        self._pools: Dict[str, queue.Queue] = {}
        for server in self.servers:
            self._pools[server["ip"]] = queue.Queue(maxsize=max_connections)

        # 锁
        self._lock = Lock()

        # 启动后台线程
        self._health_check_thread = Thread(target=self._health_check_worker, daemon=True)
        self._health_check_thread.start()

        # 预热连接池
        self._warmup_pool()

    @property
    def server(self) -> Dict[str, Any]:
        """获取当前主服务器"""
        with self._lock:
            return self.servers[self._current_server_index]

    def set_server(self, server: Dict[str, Any]):
        """手动设置当前服务器"""
        with self._lock:
            for i, s in enumerate(self.servers):
                if s["ip"] == server["ip"]:
                    self._current_server_index = i
                    print(f"[连接池] 手动切换到服务器: {server.get('name', server['ip'])}")
                    return
            # 如果是新服务器，添加到列表
            self.servers.append(server)
            self._server_status[server["ip"]] = {
                "status": ServerStatus.UNKNOWN,
                "fail_count": 0,
                "last_fail_time": 0,
                "last_success_time": 0
            }
            self._pools[server["ip"]] = queue.Queue(maxsize=self.max_connections)
            self._current_server_index = len(self.servers) - 1
            print(f"[连接池] 添加并切换到新服务器: {server.get('name', server['ip'])}")

    def _warmup_pool(self):
        """预热连接池 - 为当前服务器创建初始连接"""
        server = self.server
        print(f"[连接池] 预热连接池，服务器: {server.get('name', server['ip'])}")
        for _ in range(min(2, self.max_connections)):
            api = self._create_connection_to_server(server)
            if api:
                self._pools[server["ip"]].put(api)
                self._mark_server_healthy(server["ip"])

    def _create_connection_to_server(self, server: Dict[str, Any]) -> Optional[TdxHq_API]:
        """创建到指定服务器的连接"""
        api = TdxHq_API()
        try:
            ok = api.connect(server["ip"], server["port"], time_out=self.connect_timeout)
            if ok:
                return api
        except Exception as e:
            print(f"[连接池] 连接服务器失败 {server.get('name', server['ip'])}: {e}")

        try:
            api.disconnect()
        except Exception:
            pass
        return None

    def _mark_server_healthy(self, ip: str):
        """标记服务器为健康状态"""
        with self._lock:
            if ip in self._server_status:
                self._server_status[ip]["status"] = ServerStatus.HEALTHY
                self._server_status[ip]["fail_count"] = 0
                self._server_status[ip]["last_success_time"] = time.time()

    def _mark_server_failed(self, ip: str):
        """记录服务器失败，超过阈值则标记为不健康"""
        with self._lock:
            if ip in self._server_status:
                self._server_status[ip]["fail_count"] += 1
                self._server_status[ip]["last_fail_time"] = time.time()

                if self._server_status[ip]["fail_count"] >= self.unhealthy_threshold:
                    self._server_status[ip]["status"] = ServerStatus.UNHEALTHY
                    print(f"[连接池] 服务器 {ip} 标记为不健康 (连续失败 {self._server_status[ip]['fail_count']} 次)")

    def _is_server_available(self, ip: str) -> bool:
        """检查服务器是否可用"""
        with self._lock:
            status = self._server_status.get(ip, {})
            if status.get("status") == ServerStatus.UNHEALTHY:
                # 检查是否到了恢复检查时间
                last_fail = status.get("last_fail_time", 0)
                if time.time() - last_fail < self.recovery_time:
                    return False
            return True

    def _get_available_servers(self) -> List[Dict[str, Any]]:
        """获取所有可用的服务器列表，按优先级排序"""
        available = []
        current = self.server

        # 当前服务器优先
        if self._is_server_available(current["ip"]):
            available.append(current)

        # 添加其他可用服务器
        for server in self.servers:
            if server["ip"] != current["ip"] and self._is_server_available(server["ip"]):
                available.append(server)

        # 如果没有可用服务器，返回所有服务器（强制重试）
        if not available:
            print("[连接池] 所有服务器都不可用，将尝试所有服务器")
            return self.servers.copy()

        return available

    def _switch_to_next_server(self) -> bool:
        """切换到下一个可用服务器"""
        with self._lock:
            original_index = self._current_server_index

            for i in range(1, len(self.servers)):
                next_index = (self._current_server_index + i) % len(self.servers)
                next_server = self.servers[next_index]

                if self._is_server_available(next_server["ip"]):
                    self._current_server_index = next_index
                    print(f"[连接池] 自动切换到服务器: {next_server.get('name', next_server['ip'])}")
                    return True

            # 没有其他可用服务器
            print("[连接池] 没有其他可用服务器可切换")
            return False

    def get_connection(self) -> Tuple[Optional[TdxHq_API], Optional[Dict[str, Any]]]:
        """
        获取连接，支持自动重试和服务器切换

        Returns:
            (api, server): 连接对象和对应的服务器信息，失败返回 (None, None)
        """
        available_servers = self._get_available_servers()

        for server in available_servers:
            pool = self._pools.get(server["ip"])

            # 尝试从池中获取
            if pool and not pool.empty():
                try:
                    api = pool.get_nowait()
                    # 验证连接是否有效
                    if self._test_connection(api):
                        self._mark_server_healthy(server["ip"])
                        return api, server
                    else:
                        # 连接无效，断开并继续
                        try:
                            api.disconnect()
                        except Exception:
                            pass
                except queue.Empty:
                    pass

            # 池中没有可用连接，创建新连接
            for attempt in range(self.retry_times):
                api = self._create_connection_to_server(server)
                if api:
                    self._mark_server_healthy(server["ip"])
                    # 更新当前服务器索引
                    for i, s in enumerate(self.servers):
                        if s["ip"] == server["ip"]:
                            with self._lock:
                                self._current_server_index = i
                            break
                    return api, server

                # 连接失败，短暂等待后重试
                if attempt < self.retry_times - 1:
                    time.sleep(0.5)

            # 该服务器所有重试都失败
            self._mark_server_failed(server["ip"])

        print("[连接池] 所有服务器连接失败")
        return None, None

    def _test_connection(self, api: TdxHq_API) -> bool:
        """测试连接是否有效"""
        try:
            # 简单的心跳检测
            result = api.get_security_count(0)
            return result is not None and result > 0
        except Exception:
            return False

    def return_connection(self, api: TdxHq_API, server: Dict[str, Any] = None):
        """归还连接到池"""
        if api is None:
            return

        server_ip = server["ip"] if server else self.server["ip"]
        pool = self._pools.get(server_ip)

        try:
            if pool and not pool.full():
                pool.put_nowait(api)
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

    def _health_check_worker(self):
        """后台健康检查线程"""
        while True:
            try:
                time.sleep(self.health_check_interval)
                self._do_health_check()
            except Exception as e:
                print(f"[连接池] 健康检查异常: {e}")
                time.sleep(10)

    def _do_health_check(self):
        """执行健康检查"""
        for server in self.servers:
            ip = server["ip"]
            status = self._server_status.get(ip, {})

            # 对不健康的服务器尝试恢复
            if status.get("status") == ServerStatus.UNHEALTHY:
                last_fail = status.get("last_fail_time", 0)
                if time.time() - last_fail >= self.recovery_time:
                    print(f"[连接池] 尝试恢复服务器: {server.get('name', ip)}")
                    api = self._create_connection_to_server(server)
                    if api:
                        self._mark_server_healthy(ip)
                        self._pools[ip].put(api)
                        print(f"[连接池] 服务器已恢复: {server.get('name', ip)}")

            # 为健康的服务器维护连接池
            elif status.get("status") == ServerStatus.HEALTHY:
                pool = self._pools.get(ip)
                if pool and pool.qsize() < 2:
                    api = self._create_connection_to_server(server)
                    if api:
                        try:
                            pool.put_nowait(api)
                        except queue.Full:
                            api.disconnect()

    def close_all(self):
        """关闭所有连接"""
        for ip, pool in self._pools.items():
            while not pool.empty():
                try:
                    api = pool.get_nowait()
                    api.disconnect()
                except Exception:
                    pass

    def reset_pool(self, server_ip: str = None):
        """重置连接池"""
        if server_ip:
            pool = self._pools.get(server_ip)
            if pool:
                while not pool.empty():
                    try:
                        api = pool.get_nowait()
                        api.disconnect()
                    except Exception:
                        pass
        else:
            self.close_all()

    def get_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        with self._lock:
            current = self.servers[self._current_server_index]

            servers_status = []
            for server in self.servers:
                ip = server["ip"]
                status = self._server_status.get(ip, {})
                pool = self._pools.get(ip)
                servers_status.append({
                    "name": server.get("name", ip),
                    "ip": ip,
                    "port": server["port"],
                    "status": status.get("status", ServerStatus.UNKNOWN),
                    "fail_count": status.get("fail_count", 0),
                    "pool_size": pool.qsize() if pool else 0,
                    "is_current": ip == current["ip"]
                })

            return {
                "current_server": {
                    "name": current.get("name", current["ip"]),
                    "ip": current["ip"],
                    "port": current["port"]
                },
                "max_connections_per_server": self.max_connections,
                "retry_times": self.retry_times,
                "servers": servers_status
            }


# 全局连接池实例
tdx_connection_pool = TDXConnectionPool(
    servers=TDX_SERVERS,
    max_connections=5,
    connect_timeout=3,
    retry_times=3,
    health_check_interval=60,
    unhealthy_threshold=3,
    recovery_time=300
)

