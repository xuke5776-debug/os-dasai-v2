"""pytest 公共配置：确保项目根目录在 sys.path 上（便于导入 scenarios 包）。"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
