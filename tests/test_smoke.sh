#!/bin/bash
# Smoke tests: verify all core modules import without error
set -e

echo "=== YT-DLP Studio Smoke Tests ==="

echo "Testing core imports..."
python -c "from src.utils.constants import APP_NAME, APP_VERSION; print(f'App: {APP_NAME} v{APP_VERSION}')"
python -c "from src.utils.validators import Validators; print('Validators: OK')"
python -c "from src.utils.file_helper import FileHelper; print('FileHelper: OK')"
python -c "from src.utils.error_handler import ErrorHandler, ErrorCategory; print('ErrorHandler: OK')"
python -c "from src.utils.playlist_detector import PlaylistDetector; print('PlaylistDetector: OK')"

echo "Testing model imports..."
python -c "from src.models.download_task import DownloadTask, TaskStatus; print('DownloadTask: OK')"
python -c "from src.models.video_info import VideoInfo; print('VideoInfo: OK')"
python -c "from src.models.download_history import DownloadHistory, HistoryEntry; print('DownloadHistory: OK')"
python -c "from src.models.app_config import AppConfig; print('AppConfig: OK')"

echo "Testing backend imports..."
python -c "from src.backend.format_handler import FormatHandler; print('FormatHandler: OK')"
python -c "from src.backend.progress_handler import ProgressHandler; print('ProgressHandler: OK')"

echo "Testing basic validation..."
python -c "
from src.utils.validators import Validators
v, e = Validators.is_valid_url('https://youtube.com/watch?v=test')
assert v, f'URL validation failed: {e}'
print('URL validation: OK')
"

python -c "
from src.models.download_task import DownloadTask, TaskStatus
t = DownloadTask(url='https://example.com', output_directory='/tmp', quality='Best Quality')
assert t.status == TaskStatus.PENDING
t.start()
assert t.status == TaskStatus.DOWNLOADING
t.complete('video.mp4')
assert t.status == TaskStatus.COMPLETED
print('Task lifecycle: OK')
"

echo ""
echo "=== All smoke tests passed! ==="
