import requests
from typing import Any, Dict, TypedDict

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

class State(TypedDict):
    symbol: str
    quote: Dict[str, Any]

client = HTTPMCPClient("http://localhost:6999/mcp")

def node_get_quote(state: State) -> State:
    q = client.call_tool("get_quote", {"symbol": state["symbol"]})
    s = dict(state)
    s["quote"] = q
    return s

if __name__ == "__main__":
    try:
        from langgraph.graph import StateGraph, END
        workflow = StateGraph(State)
        workflow.add_node("get_quote", node_get_quote)
        workflow.set_entry_point("get_quote")
        workflow.add_edge("get_quote", END)
        graph = workflow.compile()
        result = graph.invoke({"symbol": "sz000001"})
        print(result)
    except Exception as e:
        try:
            r = node_get_quote({"symbol": "sz000001", "quote": {}})
            print(r)
        except Exception as ee:
            print(str(ee))
