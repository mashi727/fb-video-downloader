"""
Progress tracking utility
"""

import time
import sys
from typing import Optional


class ProgressTracker:
    """Download progress management class"""

    def __init__(self, total_size: int) -> None:
        self.total_size = total_size
        self.downloaded = 0
        self.start_time = time.time()
        self.last_update_time = self.start_time

    def update(self, chunk_size: int) -> None:
        """Update progress with download speed"""
        self.downloaded += chunk_size
        current_time = time.time()

        # Update display at most once per 0.1 seconds to reduce overhead
        if current_time - self.last_update_time < 0.1:
            return

        self.last_update_time = current_time

        if self.total_size > 0:
            progress = (self.downloaded / self.total_size) * 100
            elapsed = current_time - self.start_time
            speed = self.downloaded / elapsed if elapsed > 0 else 0

            # Format speed
            speed_str = self._format_speed(speed)

            # Estimate remaining time
            eta = self._estimate_time(elapsed, progress)

            # Create progress bar
            bar_length = 30
            filled_length = int(bar_length * progress / 100)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)

            # Print progress
            sys.stdout.write(
                f"\r[{bar}] {progress:.1f}% "
                f"({self._format_bytes(self.downloaded)}/{self._format_bytes(self.total_size)}) "
                f"{speed_str} {eta}"
            )
            sys.stdout.flush()

    def complete(self) -> None:
        """Handle completion"""
        elapsed = time.time() - self.start_time
        avg_speed = self.downloaded / elapsed if elapsed > 0 else 0
        print(f"\n✓ Download complete in {elapsed:.1f}s (avg: {self._format_speed(avg_speed)})")

    @staticmethod
    def _format_bytes(size: int) -> str:
        """Format bytes to human readable format"""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.1f}{unit}"
            size /= 1024.0
        return f"{size:.1f}TB"

    @staticmethod
    def _format_speed(speed: float) -> str:
        """Format download speed"""
        if speed < 1024:
            return f"{speed:.0f} B/s"
        elif speed < 1024 * 1024:
            return f"{speed/1024:.1f} KB/s"
        else:
            return f"{speed/(1024*1024):.1f} MB/s"

    @staticmethod
    def _estimate_time(elapsed: float, progress: float) -> str:
        """Estimate remaining time"""
        if progress <= 0:
            return "ETA: --:--"

        total_time = elapsed * 100 / progress
        remaining = total_time - elapsed

        if remaining < 60:
            return f"ETA: {remaining:.0f}s"
        elif remaining < 3600:
            minutes = remaining // 60
            seconds = remaining % 60
            return f"ETA: {minutes:.0f}m {seconds:.0f}s"
        else:
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            return f"ETA: {hours:.0f}h {minutes:.0f}m"
