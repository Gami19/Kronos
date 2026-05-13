"""API 用の小さな定数（ルート・ジョブ ID 等）。"""

from __future__ import annotations

import re

PREDICTION_RESULT_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
TRAIN_JOB_EXP_NAME = "workspace"
