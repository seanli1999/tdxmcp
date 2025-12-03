"""Pydantic数据模型"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """服务器配置"""
    ip: str
    port: int
    name: Optional[str] = None


class ServersPayload(BaseModel):
    """服务器列表请求"""
    servers: List[Dict[str, Any]]
    current_index: Optional[int] = None


class SelectPayload(BaseModel):
    """选择服务器请求"""
    index: int


class TestPayload(BaseModel):
    """测试服务器请求"""
    ip: Optional[str] = None
    port: Optional[int] = None
    index: Optional[int] = None


class BatchHistoryRequest(BaseModel):
    """批量历史数据请求"""
    symbols: List[str]
    period: int = 9
    count: int = 100
    batch_size: int = 10

