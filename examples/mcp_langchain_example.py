import requests
import asyncio
from typing import Any, Dict, List

class HTTPMCPClient:
    def __init__(self, base_url: str = "http://localhost:6999/mcp", timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()

    def _api_base(self) -> str:
        if self.base_url.endswith("/mcp"):
            return self.base_url[:-4]
        return self.base_url

    def call_tool(self, name: str, args: Dict[str, Any]) -> Any:
        api_base = self._api_base()
        if name == "get_quote":
            symbol = args["symbol"]
            r = self.session.get(f"{api_base}/api/quote/{symbol}", timeout=self.timeout)
            return r.json()
        if name == "get_quotes":
            symbols = args.get("symbols", [])
            r = self.session.post(f"{api_base}/api/quotes", json=symbols, timeout=self.timeout)
            return r.json()
        if name == "get_history":
            symbol = args["symbol"]
            period = int(args.get("period", 9))
            count = int(args.get("count", 50))
            r = self.session.get(f"{api_base}/api/history/{symbol}", params={"period": period, "count": count}, timeout=self.timeout)
            return r.json()
        if name == "get_history_batch":
            payload = {
                "symbols": args.get("symbols", []),
                "period": int(args.get("period", 9)),
                "count": int(args.get("count", 50)),
            }
            if "batch_size" in args:
                payload["batch_size"] = int(args["batch_size"])
            r = self.session.post(f"{api_base}/api/history/batch", json=payload, timeout=self.timeout)
            return r.json()
        if name == "get_finance":
            symbol = args["symbol"]
            r = self.session.get(f"{api_base}/api/finance/{symbol}", timeout=self.timeout)
            return r.json()
        if name == "get_stock_info":
            symbol = args["symbol"]
            r = self.session.get(f"{api_base}/api/stock/{symbol}", timeout=self.timeout)
            return r.json()
        if name == "get_blocks":
            r = self.session.get(f"{api_base}/api/blocks", timeout=self.timeout)
            return r.json()
        if name == "get_industries":
            r = self.session.get(f"{api_base}/api/industries", timeout=self.timeout)
            return r.json()
        raise ValueError("unknown tool")

def build_langchain_tools(client: HTTPMCPClient):
    try:
        from pydantic import BaseModel, Field
        from langchain_core.tools import StructuredTool
    except Exception:
        return []

    class GetQuoteArgs(BaseModel):
        symbol: str = Field(...)

    class GetQuotesArgs(BaseModel):
        symbols: List[str] = Field(...)

    class GetHistoryArgs(BaseModel):
        symbol: str = Field(...)
        period: int = Field(default=9)
        count: int = Field(default=50)

    class GetHistoryBatchArgs(BaseModel):
        symbols: List[str] = Field(...)
        period: int = Field(default=9)
        count: int = Field(default=50)
        batch_size: int = Field(default=10)

    class GetFinanceArgs(BaseModel):
        symbol: str = Field(...)

    class GetStockInfoArgs(BaseModel):
        symbol: str = Field(...)

    def make_tool(name: str, args_schema):
        def _run(**kwargs):
            return client.call_tool(name, kwargs)
        return StructuredTool.from_function(_run, name=name, args_schema=args_schema, description=name)

    tools = [
        make_tool("get_quote", GetQuoteArgs),
        make_tool("get_quotes", GetQuotesArgs),
        make_tool("get_history", GetHistoryArgs),
        make_tool("get_history_batch", GetHistoryBatchArgs),
        make_tool("get_finance", GetFinanceArgs),
        make_tool("get_stock_info", GetStockInfoArgs),
        make_tool("get_blocks", None),
        make_tool("get_industries", None),
    ]
    return tools

if __name__ == "__main__":
    client = HTTPMCPClient("http://localhost:6999/mcp")
    try:
        result = client.call_tool("get_quote", {"symbol": "sz000001"})
        print(result)
    except Exception as e:
        print(str(e))
    try:
        tools = build_langchain_tools(client)
        if tools:
            t = [t for t in tools if t.name == "get_quote"][0]
            print(t.invoke({"symbol": "sz000001"}))
    except Exception as e:
        print(str(e))
