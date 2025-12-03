"""服务器管理API路由"""
import os
import json
import socket
import time
import asyncio
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException
from pytdx.hq import TdxHq_API

from config import TDX_SERVERS
from ..models.schemas import ServerConfig, ServersPayload, SelectPayload, TestPayload
from ..connection.pool import tdx_connection_pool
from ..connection.client import tdx_client

router = APIRouter(prefix="/api", tags=["servers"])
executor = ThreadPoolExecutor(max_workers=10)

# 获取缓存目录路径
def _get_cache_dir():
    return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "cache")

@router.get("/servers")
async def get_servers():
    """获取服务器列表"""
    cache_dir = _get_cache_dir()
    servers_path = os.path.join(cache_dir, "servers.json")
    try:
        if os.path.exists(servers_path):
            with open(servers_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {"servers": data.get("servers", TDX_SERVERS), "current": data.get("current", tdx_client.current_server)}
    except Exception:
        pass
    return {"servers": TDX_SERVERS, "current": tdx_client.current_server}


@router.post("/connect")
async def connect_server(server_index: int = 0):
    """连接到指定的TDX服务器"""
    if server_index >= len(TDX_SERVERS):
        raise HTTPException(status_code=400, detail="服务器索引超出范围")
    
    success = await asyncio.get_event_loop().run_in_executor(
        executor, tdx_client.connect, TDX_SERVERS[server_index]
    )
    
    return {"success": success, "server": TDX_SERVERS[server_index] if success else None}


@router.post("/server/config")
async def set_server_config(cfg: ServerConfig):
    """设置服务器配置"""
    if cfg.port < 1 or cfg.port > 65535:
        raise HTTPException(status_code=400, detail="端口不合法")
    server = {"ip": cfg.ip, "port": cfg.port, "name": cfg.name or "自定义"}
    
    def _apply():
        tdx_connection_pool.set_server(server)
        tdx_connection_pool.reset_pool()
        tdx_client.current_server = server
        try:
            cache_dir = _get_cache_dir()
            os.makedirs(cache_dir, exist_ok=True)
            servers_path = os.path.join(cache_dir, "servers.json")
            data = {"servers": [server], "current": server}
            try:
                if os.path.exists(servers_path):
                    with open(servers_path, "r", encoding="utf-8") as f:
                        old = json.load(f)
                        if isinstance(old, dict) and isinstance(old.get("servers"), list):
                            lst = old.get("servers")
                            found = False
                            for s in lst:
                                if s.get("ip") == server["ip"] and s.get("port") == server["port"]:
                                    s["name"] = server["name"]
                                    found = True
                                    break
                            if not found:
                                lst.append(server)
                            data = {"servers": lst, "current": server}
            except Exception:
                pass
            with open(servers_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
        return True
    
    success = await asyncio.get_event_loop().run_in_executor(executor, _apply)
    return {"success": success, "server": server}


@router.get("/server/current")
async def get_current_server():
    """获取当前服务器"""
    return {"current": tdx_client.current_server}


@router.post("/servers")
async def set_servers(payload: ServersPayload):
    """设置服务器列表"""
    if not payload.servers:
        raise HTTPException(status_code=400, detail="服务器列表为空")
    cache_dir = _get_cache_dir()
    servers_path = os.path.join(cache_dir, "servers.json")
    
    def _apply():
        data = {"servers": payload.servers, "current": None}
        old_current = None
        try:
            if os.path.exists(servers_path):
                with open(servers_path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                    if isinstance(old, dict):
                        old_current = old.get("current")
        except Exception:
            pass
        idx = payload.current_index if payload.current_index is not None else None
        if isinstance(idx, int) and 0 <= idx < len(payload.servers):
            data["current"] = payload.servers[idx]
        else:
            chosen = None
            try:
                if isinstance(old_current, dict):
                    for s in payload.servers:
                        if s.get("ip") == old_current.get("ip") and int(s.get("port")) == int(old_current.get("port")):
                            chosen = s
                            break
            except Exception:
                chosen = None
            data["current"] = chosen or payload.servers[0]
        try:
            os.makedirs(cache_dir, exist_ok=True)
            with open(servers_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except Exception:
            pass
        try:
            tdx_connection_pool.set_server(data["current"])
            tdx_connection_pool.reset_pool()
            tdx_client.current_server = data["current"]
        except Exception:
            pass
        return True
    
    ok = await asyncio.get_event_loop().run_in_executor(executor, _apply)
    return {"success": ok}


@router.post("/server/select")
async def select_server(payload: SelectPayload):
    """选择服务器"""
    cache_dir = _get_cache_dir()
    servers_path = os.path.join(cache_dir, "servers.json")

    def _apply():
        try:
            with open(servers_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                servers = data.get("servers", [])
                if not servers:
                    return False
                idx = payload.index
                if idx < 0 or idx >= len(servers):
                    idx = 0
                current = servers[idx]
                data["current"] = current
            with open(servers_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            tdx_connection_pool.set_server(current)
            tdx_connection_pool.reset_pool()
            tdx_client.current_server = current
            return True
        except Exception:
            return False

    ok = await asyncio.get_event_loop().run_in_executor(executor, _apply)
    return {"success": ok}


@router.post("/server/test")
async def test_server(payload: TestPayload):
    """测试服务器连接"""
    cache_dir = _get_cache_dir()

    def _resolve():
        srv = None
        if payload.ip and payload.port:
            srv = {"ip": payload.ip, "port": int(payload.port)}
        else:
            try:
                servers_path = os.path.join(cache_dir, "servers.json")
                with open(servers_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    servers = data.get("servers", [])
                    idx = payload.index or 0
                    if idx < 0 or idx >= len(servers):
                        idx = 0
                    srv = servers[idx]
            except Exception:
                pass
        return srv

    def _test():
        srv = _resolve()
        if not srv:
            return {"success": False, "error": "未找到服务器"}
        tcp_ok = False
        tcp_err = None
        t0 = time.time()
        try:
            with socket.create_connection((srv["ip"], int(srv["port"])), timeout=2):
                tcp_ok = True
        except Exception as e:
            tcp_err = str(e)
        tcp_ms = int((time.time() - t0) * 1000)
        if not tcp_ok:
            return {"success": False, "latency_ms": tcp_ms, "server": srv, "reason": "tcp_connect_failed", "error": tcp_err}
        api = TdxHq_API()
        t1 = time.time()
        ok = False
        tdx_err = None
        try:
            ok = api.connect(srv["ip"], int(srv["port"]))
        except Exception as e:
            tdx_err = str(e)
            ok = False
        try:
            api.disconnect()
        except Exception:
            pass
        ms = int((time.time() - t1) * 1000)
        return {"success": bool(ok), "latency_ms": ms, "server": srv, "reason": "ok" if ok else "tdx_handshake_failed", "error": tdx_err}

    rs = await asyncio.get_event_loop().run_in_executor(executor, _test)
    return rs


@router.get("/server/saved")
async def get_saved_server():
    """获取已保存的服务器配置"""
    try:
        cache_dir = _get_cache_dir()
        cfg_path = os.path.join(cache_dir, "server_config.json")
        if os.path.exists(cfg_path):
            with open(cfg_path, "r", encoding="utf-8") as f:
                return {"saved": json.load(f)}
    except Exception:
        pass
    return {"saved": None}


@router.get("/status")
async def get_status():
    """获取服务状态和连接池详情"""
    pool_status = tdx_connection_pool.get_status()

    return {
        "connected": True,
        "current_server": pool_status.get("current_server"),
        "connection_pool": {
            "max_connections_per_server": pool_status.get("max_connections_per_server"),
            "retry_times": pool_status.get("retry_times"),
            "servers": pool_status.get("servers", [])
        }
    }

