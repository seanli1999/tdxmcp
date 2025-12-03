"""缓存服务"""
import os
import json
from datetime import datetime
from typing import Any, Optional


class CacheService:
    """缓存服务，管理文件缓存"""
    
    def __init__(self, cache_dir: str):
        self.cache_dir = cache_dir
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception:
            pass
    
    def load_cache(self, name: str, max_age: int = 86400) -> Optional[Any]:
        """
        加载缓存数据
        
        Args:
            name: 缓存文件名
            max_age: 最大缓存年龄（秒），默认24小时
        
        Returns:
            缓存数据，如果缓存不存在或过期则返回None
        """
        try:
            self.ensure_cache_dir()
            p = os.path.join(self.cache_dir, name)
            if not os.path.exists(p):
                return None
            with open(p, "r", encoding="utf-8") as f:
                obj = json.load(f)
            ts = obj.get("cached_at")
            data = obj.get("data")
            if not ts or data is None:
                return None
            try:
                t0 = datetime.fromisoformat(ts)
                if (datetime.now() - t0).total_seconds() > max_age:
                    return None
            except Exception:
                return None
            return data
        except Exception:
            return None
    
    def save_cache(self, name: str, data: Any) -> bool:
        """
        保存缓存数据
        
        Args:
            name: 缓存文件名
            data: 要缓存的数据
        
        Returns:
            是否保存成功
        """
        try:
            self.ensure_cache_dir()
            p = os.path.join(self.cache_dir, name)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({
                    "cached_at": datetime.now().isoformat(),
                    "data": data
                }, f, ensure_ascii=False)
            return True
        except Exception:
            return False
    
    def get_servers_config(self, default_servers: list) -> tuple:
        """
        获取服务器配置
        
        Args:
            default_servers: 默认服务器列表
        
        Returns:
            (servers, current) 元组
        """
        servers_path = os.path.join(self.cache_dir, "servers.json")
        current = None
        servers = None
        
        if os.path.exists(servers_path):
            try:
                with open(servers_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        servers = data.get("servers")
                        current = data.get("current")
            except Exception:
                pass
        
        if not servers:
            servers = default_servers
            try:
                self.ensure_cache_dir()
                with open(servers_path, "w", encoding="utf-8") as f:
                    json.dump({"servers": servers, "current": servers[0]}, f, ensure_ascii=False)
                current = servers[0]
            except Exception:
                current = servers[0]
        
        if not current and servers:
            current = servers[0]
        
        return servers, current
    
    def save_servers_config(self, servers: list, current: dict) -> bool:
        """保存服务器配置"""
        try:
            self.ensure_cache_dir()
            servers_path = os.path.join(self.cache_dir, "servers.json")
            with open(servers_path, "w", encoding="utf-8") as f:
                json.dump({"servers": servers, "current": current}, f, ensure_ascii=False)
            return True
        except Exception:
            return False

