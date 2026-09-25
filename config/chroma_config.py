"""向量库配置与远程 Embedding 函数

- 向量化模型：硅基流动 (SiliconFlow) 的 BAAI/bge-m3，走 OpenAI 兼容的 /v1/embeddings 接口
- 检索相关参数（切块、阈值、TopK 等）统一从 .env 读取，便于跨环境调整
"""

import os
from typing import Any, Optional

import httpx
from dotenv import load_dotenv

# 根据 APP_ENV 加载对应的 .env 文件（与 llm_config 保持一致）
_app_env = os.getenv("APP_ENV", "development")
_env_file = f".env.{_app_env}" if _app_env != "development" else ".env"
load_dotenv(_env_file)

# ---- 向量化模型配置 ----
EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", "")
EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", "https://api.siliconflow.cn/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
EMBEDDING_TIMEOUT = int(os.getenv("EMBEDDING_TIMEOUT", 30))

# ---- 知识库检索配置 ----
KB_CHUNK_SIZE = int(os.getenv("KB_CHUNK_SIZE", 500))
KB_CHUNK_OVERLAP = int(os.getenv("KB_CHUNK_OVERLAP", 50))
KB_SYNC_INTERVAL = int(os.getenv("KB_SYNC_INTERVAL", 60))
KB_QUERY_PREFIX_ENABLED = os.getenv("KB_QUERY_PREFIX_ENABLED", "true").lower() == "true"
KB_SEARCH_TOP_K = int(os.getenv("KB_SEARCH_TOP_K", 5))
KB_FINAL_TOP_K = int(os.getenv("KB_FINAL_TOP_K", 2))
KB_SCORE_THRESHOLD = float(os.getenv("KB_SCORE_THRESHOLD", 0.5))

# bge 系列官方推荐：检索场景下给「查询句」加前缀（文档侧不加）可提升召回
KB_QUERY_PREFIX = os.getenv(
    "KB_QUERY_PREFIX",
    "为这个句子生成表示以用于检索相关文章：",
)


class SiliconFlowEmbeddingFunction:
    """基于硅基流动 OpenAI 兼容接口的向量化函数。

    实现 ChromaDB 的 EmbeddingFunction 协议：__call__ / name / get_config /
    build_from_config，从而可随 collection 持久化并在重启后正确还原。
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        api_key: str = EMBEDDING_API_KEY,
        base_url: str = EMBEDDING_BASE_URL,
        timeout: int = EMBEDDING_TIMEOUT,
    ) -> None:
        self.model_name = model_name
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            raise RuntimeError(
                "未配置 EMBEDDING_API_KEY，无法调用硅基流动人口向量模型"
            )
        url = f"{self.base_url}/embeddings"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        payload = {"model": self.model_name, "input": texts, "encoding_format": "float"}
        with httpx.Client(timeout=self.timeout) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"向量模型请求失败 status={resp.status_code} body={resp.text[:200]}"
                )
            data = resp.json()
        # 按 index 排序，保证与输入顺序一致
        items = sorted(data.get("data", []), key=lambda x: x.get("index", 0))
        vectors = [it["embedding"] for it in items]
        if len(vectors) != len(texts):
            raise RuntimeError(
                f"向量返回数量({len(vectors)})与输入文本数量({len(texts)})不一致"
            )
        return vectors

    def __call__(self, input: list[str]) -> list[list[float]]:
        """文档入库时的向量化（不加 query 前缀）。"""
        if isinstance(input, str):
            input = [input]
        return self._embed(list(input))

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        """查询时的向量化：按 bge 建议为检索场景加前缀。"""
        if isinstance(queries, str):
            queries = [queries]
        if KB_QUERY_PREFIX_ENABLED:
            queries = [f"{KB_QUERY_PREFIX}{q}" for q in queries]
        return self._embed(list(queries))

    # ---- 供 ChromaDB 持久化 / 还原使用 ----
    def name(self) -> str:
        return "siliconflow-embedding"

    def get_config(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "base_url": self.base_url,
        }

    @classmethod
    def build_from_config(cls, config: dict[str, Any]) -> "SiliconFlowEmbeddingFunction":
        return cls(
            model_name=config.get("model_name") or EMBEDDING_MODEL,
            base_url=config.get("base_url") or EMBEDDING_BASE_URL,
        )

    def default_config(self) -> dict[str, Optional[Any]]:
        return {"model_name": self.model_name, "base_url": self.base_url}


def get_embedding_function() -> SiliconFlowEmbeddingFunction:
    """返回全局复用的向量化函数实例。"""
    return SiliconFlowEmbeddingFunction(
        model_name=EMBEDDING_MODEL,
        api_key=EMBEDDING_API_KEY,
        base_url=EMBEDDING_BASE_URL,
        timeout=EMBEDDING_TIMEOUT,
    )
