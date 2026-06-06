"""Prompt 文件加载器。

将所有 Prompt 提取到 prompts/ 目录，便于迭代和版本管理。
"""
from __future__ import annotations

from pathlib import Path

# Prompt 文件目录（相对于项目根目录）
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name: str) -> str:
    """加载指定名称的 Prompt 文件。

    Args:
        name: Prompt 文件名（不含 .prompt 后缀）

    Returns:
        Prompt 文本内容

    Raises:
        FileNotFoundError: 如果 Prompt 文件不存在
    """
    prompt_path = _PROMPTS_DIR / f"{name}.prompt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Prompt 文件不存在: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8")
