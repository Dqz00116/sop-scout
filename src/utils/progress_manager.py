"""
进度管理器

用于跟踪和查询工作流的执行进度
"""
import threading
import time
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ProgressInfo:
    """进度信息"""
    run_id: str
    total_files: int           # 总文件数
    processed_files: int       # 已处理文件数
    extracted_sops: int        # 已提取SOP数
    status: str                # 当前状态: running, paused, completed, cancelled, error
    current_batch: int         # 当前批次号
    total_batches: int         # 总批次数
    start_time: float          # 开始时间戳
    last_update_time: float    # 最后更新时间戳
    error_message: Optional[str] = None  # 错误信息（如果有）

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        # 计算进度百分比
        if self.total_files > 0:
            data['progress_percent'] = round((self.processed_files / self.total_files) * 100, 2)
        else:
            data['progress_percent'] = 0.0

        # 计算预计剩余时间（秒）
        if self.processed_files > 0:
            elapsed_time = self.last_update_time - self.start_time
            avg_time_per_file = elapsed_time / self.processed_files
            remaining_files = self.total_files - self.processed_files
            data['estimated_remaining_time'] = round(avg_time_per_file * remaining_files, 2)
        else:
            data['estimated_remaining_time'] = None

        # 格式化时间
        data['start_time_formatted'] = datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')
        data['last_update_time_formatted'] = datetime.fromtimestamp(self.last_update_time).strftime('%Y-%m-%d %H:%M:%S')
        data['elapsed_time'] = round(self.last_update_time - self.start_time, 2)

        return data


class ProgressManager:
    """进度管理器"""

    def __init__(self):
        self.progress: Dict[str, ProgressInfo] = {}
        self.lock = threading.Lock()

    def init_progress(self, run_id: str, total_files: int, batch_size: int = 10):
        """初始化进度"""
        with self.lock:
            total_batches = (total_files + batch_size - 1) // batch_size
            self.progress[run_id] = ProgressInfo(
                run_id=run_id,
                total_files=total_files,
                processed_files=0,
                extracted_sops=0,
                status="running",
                current_batch=0,
                total_batches=total_batches,
                start_time=time.time(),
                last_update_time=time.time()
            )

    def update_progress(
        self,
        run_id: str,
        processed_files: int,
        extracted_sops: int,
        current_batch: int
    ):
        """更新进度"""
        with self.lock:
            if run_id in self.progress:
                self.progress[run_id].processed_files = processed_files
                self.progress[run_id].extracted_sops = extracted_sops
                self.progress[run_id].current_batch = current_batch
                self.progress[run_id].last_update_time = time.time()

    def update_status(self, run_id: str, status: str, error_message: Optional[str] = None):
        """更新状态"""
        with self.lock:
            if run_id in self.progress:
                self.progress[run_id].status = status
                self.progress[run_id].last_update_time = time.time()
                if error_message:
                    self.progress[run_id].error_message = error_message

    def get_progress(self, run_id: str) -> Optional[Dict]:
        """获取进度"""
        with self.lock:
            if run_id in self.progress:
                # 更新last_update_time
                self.progress[run_id].last_update_time = time.time()
                return self.progress[run_id].to_dict()
            return None

    def clear(self, run_id: str):
        """清除进度"""
        with self.lock:
            self.progress.pop(run_id, None)


# 全局单例
progress_manager = ProgressManager()
