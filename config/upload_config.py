from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent  # 后端项目的根路径
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip",
}

# 前端访问上传文件的 URL 前缀，需与 main.py 中 StaticFiles 挂载路径一致
UPLOAD_URL_PREFIX = "/uploads"


def get_upload_path() -> Path:
    """返回上传文件存储的目录路径"""
    return UPLOAD_DIR


def get_upload_url() -> str:
    """返回上传文件的 URL 前缀"""
    return UPLOAD_URL_PREFIX


def get_upload_file_path(filename: str) -> Path:
    """返回指定文件名在磁盘上的完整存储路径"""
    return UPLOAD_DIR / filename


def get_upload_file_url(filename: str) -> str:
    """返回指定文件名的可访问 URL"""
    return f"{UPLOAD_URL_PREFIX}/{filename}"