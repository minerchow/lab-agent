"""知识库向量检索

流程：扫描 data/kb 下的 Markdown -> 递归切块 -> 硅基流动 bge-m3 向量化 -> Chroma(余弦)。
支持基于文件内容 hash 的增量同步（新增/修改/删除文件均生效），并提供 rebuild() 全量重建。
"""

import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path

import chromadb

from config.upload_config import BASE_DIR
from config.chroma_config import (
    KB_CHUNK_SIZE,
    KB_CHUNK_OVERLAP,
    KB_SYNC_INTERVAL,
    KB_SEARCH_TOP_K,
    KB_FINAL_TOP_K,
    KB_SCORE_THRESHOLD,
    get_embedding_function,
)

logger = logging.getLogger(__name__)

KB_DIR = BASE_DIR / "data" / "kb"
CHROMA_DIR = BASE_DIR / "data" / "chroma"
MANIFEST_PATH = CHROMA_DIR / "kb_manifest.json"
COLLECTION_NAME = "lab_kb"

# 递归切分时依次使用的分隔符（从语义强到弱）
_DELIMITERS = ["\n## ", "\n# ", "\n\n", "\n", "。", "！", "？", "；", ""]

_collection = None
_embedding_fn = None
_lock = threading.Lock()
_last_sync = 0.0


# ---------------------------------------------------------------- 切块

def _split_by_delimiter(text: str, delimiter: str, max_size: int) -> list[str]:
    """按分隔符切分并贪心合并到 max_size 以内，仍超限则用下一级分隔符递归切分。"""
    if not text:
        return []
    if len(text) <= max_size:
        return [text]

    if delimiter == "":
        # 所有分隔符都无效时，定长硬切（带 overlap 重叠）
        step = max(1, max_size - KB_CHUNK_OVERLAP)
        return [text[i:i + max_size] for i in range(0, len(text), step)]

    if delimiter in ("\n## ", "\n# "):
        # 保留标题前缀：把分隔符重新拼回后面各段
        parts = text.split(delimiter)
        parts = [parts[0]] + [delimiter + p for p in parts[1:] if p.strip()]
    else:
        parts = [p for p in text.split(delimiter) if p.strip()]

    merged: list[str] = []
    buf = ""
    for part in parts:
        candidate = f"{buf}{delimiter}{part}" if buf else part
        if len(candidate) <= max_size:
            buf = candidate
        else:
            if buf:
                merged.append(buf)
            if len(part) > max_size:
                idx = _DELIMITERS.index(delimiter) + 1
                merged.extend(_split_by_delimiter(part, _DELIMITERS[idx], max_size))
                buf = ""
            else:
                buf = part
    if buf:
        merged.append(buf)
    return merged


def _merge_with_overlap(units: list[str], max_size: int, overlap: int) -> list[str]:
    """把语义单元贪心拼接成块；超长单元按句读对齐滑动窗口，保证相邻块有重叠。"""
    if max_size <= 0 or overlap >= max_size:
        overlap = max(0, min(overlap, max_size // 2))
    step = max(1, max_size - overlap)
    sentence_ends = "。！？；\n"

    chunks: list[str] = []
    tail = ""  # 上一块末尾，用于块间重叠
    buf = ""

    def flush():
        nonlocal buf, tail
        text = buf.strip()
        if not text:
            return
        if tail and text.startswith(tail):
            chunks.append(text)
        else:
            chunks.append((tail + "\n" + text) if tail else text)
        tail = text[-overlap:] if overlap > 0 else ""
        buf = ""

    for unit in units:
        if len(unit) > max_size:
            flush()
            for i in range(0, len(unit), step):
                # 窗口右端向后对齐到句读，避免硬截断句子
                end = len(unit) if i + max_size >= len(unit) else i + max_size
                while end < len(unit) and unit[end] not in sentence_ends:
                    end += 1
                seg = unit[i:end].strip()
                if seg:
                    chunks.append((tail + "\n" + seg) if tail else seg)
                    tail = seg[-overlap:] if overlap > 0 else ""
            buf = ""
            continue
        candidate = f"{buf}\n{unit}" if buf else unit
        if len(candidate) <= max_size:
            buf = candidate
        else:
            flush()
            buf = unit
    flush()
    return [c for c in chunks if c.strip()]


def chunk_text(text: str, chunk_size: int = KB_CHUNK_SIZE, overlap: int = KB_CHUNK_OVERLAP) -> list[str]:
    """递归切分成 chunk_size 字左右的块（标题 > 段落 > 行 > 句读），相邻块保留 overlap 字重叠。"""
    text = text.replace("\r\n", "\n").strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    units = _split_by_delimiter(text, _DELIMITERS[0], chunk_size)
    return _merge_with_overlap(units, chunk_size, overlap)


# ---------------------------------------------------------------- 文件扫描 & manifest

def _file_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def _scan_files() -> dict[str, dict]:
    """递归扫描 KB 目录下所有 .md 文件（含子目录，排除隐藏目录）。

    返回 {相对路径: {"hash": ..., "chunks": [块内容, ...]}}，相对路径统一用 "/" 分隔。
    """
    result: dict[str, dict] = {}
    if not KB_DIR.exists():
        return result
    for path in sorted(KB_DIR.rglob("*.md")):
        if any(part.startswith(".") for part in path.relative_to(KB_DIR).parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as e:
            logger.error(f"读取知识库文件失败 {path}: {e}")
            continue
        rel = path.relative_to(KB_DIR).as_posix()
        result[rel] = {"hash": _file_hash(path), "chunks": chunk_text(text)}
    return result


def _load_manifest() -> dict:
    if MANIFEST_PATH.exists():
        try:
            return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"manifest 读取失败，将重建: {e}")
    return {}


def _save_manifest(manifest: dict) -> None:
    tmp = MANIFEST_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, MANIFEST_PATH)


# ---------------------------------------------------------------- 集合初始化 & 同步

def _sync_collection(col) -> int:
    """增量同步：文件 hash 变化时对该文件的块执行 delete + upsert，删除已下线文件。

    返回实际写入的块数（无变化返回 0）。
    """
    global _last_sync
    files = _scan_files()
    manifest = _load_manifest()

    changed = 0
    for rel, info in files.items():
        old = manifest.get(rel)
        if old and old.get("hash") == info["hash"]:
            continue
        if old and old.get("ids"):
            col.delete(ids=old["ids"])
        ids = [f"{rel}#{i}" for i in range(len(info["chunks"]))]
        if ids:
            col.upsert(
                ids=ids,
                documents=info["chunks"],
                metadatas=[{"source": rel, "chunk": i} for i in range(len(ids))],
            )
        manifest[rel] = {"hash": info["hash"], "ids": ids}
        changed += len(ids)
        logger.info(f"知识库文件已同步: {rel} ({len(ids)} 块)")

    # 清理已删除文件遗留的向量
    for rel in list(manifest.keys()):
        if rel not in files:
            stale_ids = manifest[rel].get("ids", [])
            if stale_ids:
                col.delete(ids=stale_ids)
            del manifest[rel]
            logger.info(f"知识库文件已移除: {rel}")

    _save_manifest(manifest)
    _last_sync = time.time()
    return changed


def _build_collection():
    """创建客户端与集合（余弦空间），并做首次增量同步。失败时抛异常。"""
    global _collection, _embedding_fn
    KB_DIR.mkdir(parents=True, exist_ok=True)
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    _embedding_fn = get_embedding_function()
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    try:
        col = client.get_or_create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        # 集合由旧模型/旧 embedding 创建，元数据冲突时删除重建
        logger.warning(f"集合元数据与当前配置不兼容（可能更换了向量模型），自动重建: {e}")
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        MANIFEST_PATH.unlink(missing_ok=True)
        col = client.create_collection(
            name=COLLECTION_NAME,
            embedding_function=_embedding_fn,
            metadata={"hnsw:space": "cosine"},
        )
    _sync_collection(col)
    _collection = col
    return col


def get_collection():
    """获取向量集合（双检锁保证线程安全，多线程只初始化一次）。"""
    global _collection, _last_sync
    if _collection is not None:
        # 节流增量同步：超过间隔后才重新扫描文件
        if KB_SYNC_INTERVAL > 0 and time.time() - _last_sync >= KB_SYNC_INTERVAL:
            with _lock:
                if _collection is not None and time.time() - _last_sync >= KB_SYNC_INTERVAL:
                    try:
                        _sync_collection(_collection)
                    except Exception as e:
                        # 同步失败不影响已有索引的检索，但要刷新时间避免频繁重试
                        logger.error(f"知识库增量同步失败: {e}")
                        _last_sync = time.time()
        return _collection
    with _lock:
        if _collection is None:
            return _build_collection()
        return _collection


# 兼容旧调用名
get_collcetion = get_collection


def rebuild():
    """显式全量重建：清空集合并重新切块入库。"""
    with _lock:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:
            pass
        global _collection
        _collection = None
        if MANIFEST_PATH.exists():
            MANIFEST_PATH.unlink(missing_ok=True)
        col = _build_collection()
        logger.info(f"知识库重建完成，共 {col.count()} 块")
        return col.count()


def health_check() -> dict:
    """启动时的健康检查：验证目录可写、模型可调用、集合可创建。"""
    try:
        col = _build_collection()
        return {"ok": True, "chunks": col.count(), "error": None}
    except Exception as e:
        logger.error(f"知识库健康检查失败: {e}")
        return {"ok": False, "chunks": 0, "error": str(e)}


# ---------------------------------------------------------------- 检索

def search(query: str, top_k: int = KB_SEARCH_TOP_K, threshold: float = KB_SCORE_THRESHOLD) -> list[dict]:
    """向量检索，返回结构化的相关块列表（按分数降序）。

    返回值: [{"source": 相对路径, "score": 余弦相似度(0~1), "content": 块文本}, ...]
    由调用方决定如何拼装 prompt。
    """
    if not query or not query.strip():
        return []
    try:
        col = get_collection()
        total = col.count()
        if total == 0:
            logger.warning("知识库为空，请检查 data/kb 目录下的 Markdown 文档")
            return []

        # 查询向量单独计算，按 bge 建议加检索前缀
        query_emb = _embedding_fn.embed_queries([query.strip()])[0]
        n_results = min(top_k, total)
        res = col.query(query_embeddings=[query_emb], n_results=n_results)
    except Exception as e:
        logger.error(f"知识库检索失败: {e}")
        return []

    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    distances = (res.get("distances") or [[]])[0]

    results = []
    for doc, meta, dist in zip(docs, metas, distances):
        # 余弦距离 -> 余弦相似度，越接近 1 越相关
        score = 1 - dist
        if score < threshold:
            continue
        results.append({
            "source": (meta or {}).get("source", ""),
            "score": round(float(score), 4),
            "content": doc,
        })
    results.sort(key=lambda x: x["score"], reverse=True)
    logger.info(f"检索 '{query[:30]}' 命中 {len(results)} 块（阈值 {threshold}）")
    return results


def build_context(query: str, final_top_k: int = KB_FINAL_TOP_K) -> str:
    """检索并把最相关的若干块拼成上下文文本，供上层组装 prompt。"""
    results = search(query)[:final_top_k]
    parts = [f"[{r['source']}]\n{r['content']}" for r in results]
    return "\n\n".join(parts)
