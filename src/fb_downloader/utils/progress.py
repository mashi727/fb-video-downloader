"""
Progress tracking utility
"""


class ProgressTracker:
    """Download progress management class"""
    
    def __init__(self, total_size: int):
        self.total_size = total_size
        self.downloaded = 0
    
    def update(self, chunk_size: int) -> None:
        """Update progress"""
        self.downloaded += chunk_size
        if self.total_size > 0:
            progress = (self.downloaded / self.total_size) * 100
            print(f"\rProgress: {progress:.1f}% "
                  f"({self.downloaded:,}/{self.total_size:,} bytes)", end='')
    
    def complete(self) -> None:
        """Handle completion"""
        print()  # New line