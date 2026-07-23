"""Prompt 文件加载器：从 prompts/ 目录读取 .prompt 文件，支持热更新。"""
from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# prompts 目录：app/prompt/prompt_loader.py -> app/ 的父级是 backend/
_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def load_prompt(name: str) -> str:
    """加载指定名称的 prompt 文件。

    Args:
        name: prompt 文件名（不含 .prompt 后缀）

    Returns:
        prompt 文件内容

    Raises:
        FileNotFoundError: 文件不存在时抛出
    """
    prompt_path = _PROMPTS_DIR / f"{name}.prompt"
    if not prompt_path.exists():
        logger.error("Prompt 文件不存在: %s", prompt_path)
        raise FileNotFoundError(f"Prompt 文件不存在: {name}.prompt")
    return prompt_path.read_text(encoding="utf-8")
