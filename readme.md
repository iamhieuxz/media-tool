# Media Scanner Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)](https://github.com/iamhieuxz/media-tool)

**Media Scanner Pro** — công cụ mã nguồn mở giúp dọn dẹp thư viện ảnh và video trên máy tính. Chỉ cần một lần quét, bạn có thể phát hiện file hỏng, tìm bản sao trùng lặp, xem trước trực tiếp và giải phóng dung lượng ổ đĩa.

> Quét media · phát hiện file lỗi · tìm và xoá trùng lặp

---

## Vì sao dùng Media Scanner Pro?

Thư viện ảnh/video lớn thường chứa file tải lại nhiều lần, bản backup trùng nhau, hoặc file bị hỏng do copy không hoàn chỉnh. Media Scanner Pro gom ba việc quan trọng vào một luồng xử lý duy nhất:

| Vấn đề | Giải pháp |
|--------|-----------|
| Không biết file nào bị hỏng | Kiểm tra đa lớp: **PIL**, **OpenCV**, **ffprobe** |
| Nhiều file giống hệt nhau | Hash chính xác **SHA256 / MD5** |
| Ảnh gần giống (resize, nén khác) | Perceptual hash **pHash / dHash** |
| Khó quản lý thủ công | Giao diện desktop trực quan + chế độ **CLI** tự động |

**Khởi chạy nhanh** — mặc định mở giao diện đồ họa:

```bash
git clone https://github.com/iamhieuxz/media-tool.git
cd media-tool
pip install -r requirements.txt
python main.py
```

---

## Tính năng

- **Quét đa đường dẫn** — nhiều thư mục hoặc toàn bộ ổ đĩa Windows
- **Phát hiện file lỗi** — ảnh và video, phân loại mức độ nghiêm trọng
- **Tìm trùng lặp** — exact hash hoặc perceptual similarity (tuỳ chọn)
- **Preview & Compare** — xem thumbnail, metadata, so sánh cặp duplicate
- **Thao tác file** — xóa, cách ly (`quarantine/`), xuất CSV
- **Lịch sử quét** — lưu thống kê vào SQLite
- **Đóng gói EXE** — build one-file Windows bằng PyInstaller

### Định dạng hỗ trợ

| Loại | Extension |
|------|-----------|
| Ảnh | `.jpg` `.jpeg` `.png` `.webp` `.bmp` `.tif` `.tiff` `.gif` |
| Video | `.mp4` `.mkv` `.avi` `.mov` `.wmv` `.flv` `.webm` `.m4v` |

---

## Yêu cầu

| Thành phần | Ghi chú |
|------------|---------|
| Python 3.10+ | Khuyến nghị 3.11 trở lên |
| Windows | GUI tối ưu nhất; CLI chạy trên Linux/macOS |
| FFmpeg | Tuỳ chọn — cài `ffprobe` vào PATH để kiểm tra video tốt hơn |

---

## Cài đặt

```bash
git clone https://github.com/iamhieuxz/media-tool.git
cd media-tool

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux / macOS

pip install -r requirements.txt
```

**Dependencies chính:** `flet` · `Pillow` · `opencv-python` · `imagehash`

Build EXE (tuỳ chọn):

```bash
pip install pyinstaller
python build_exe.py
# → dist/MediaTool.exe
```

---

## Hướng dẫn sử dụng

### Giao diện đồ họa (mặc định)

```bash
python main.py
```

1. Chọn thư mục (*Browse*) hoặc thêm ổ đĩa (*Add Drive*)
2. Nhấn **Start Scan** — quét lỗi rồi tìm duplicate trong một pipeline
3. Lọc kết quả bằng ô tìm kiếm; chọn dòng để **Preview**
4. Với file duplicate: dùng **Compare** để xem side-by-side
5. Footer: **Export**, **Clean Duplicates**, **Clean Corrupted**, **Quarantine**

Có thể **Pause / Resume / Stop** trong lúc quét.

#### Settings (⚙️)

| Tuỳ chọn | Mô tả |
|----------|-------|
| Hash Level | Level 1: MD5/SHA256 · Level 2: Perceptual (pHash) |
| Similarity Threshold | Ngưỡng % cho perceptual hash (mặc định 95) |
| Worker Count | Luồng song song (`0` = tự động) |
| Auto Save Results | Lưu vào `data/app.db` |

### Dòng lệnh (CLI)

```bash
# Quét thư mục hiện tại
python main.py --cli

# Quét nhiều path
python main.py --cli --path "D:\Photos" "E:\Backup\videos"
```

Kết quả:

- `invalid_media.csv` — file lỗi
- `duplicate_media.csv` — nhóm trùng lặp

---

## Kiến trúc

```
Scan paths → MediaFileScanner
                ↓
         MediaChecker (PIL / OpenCV / ffprobe)
                ↓
         DuplicateFinder (size → hash / pHash)
                ↓
         GUI + CSV + SQLite
```

```
media-tool/
├── main.py              # Entry point — GUI mặc định, --cli cho CLI
├── LICENSE              # MIT
├── requirements.txt
├── build_exe.py
└── src/
    ├── core/            # Checker, deduplicator, hash engines
    ├── services/        # MediaInspector, DuplicateService
    ├── gui/             # Flet UI
    ├── db/              # SQLite settings & history
    └── utils/           # ffmpeg, thumbnails, file ops
```

---

## Lưu ý

1. **Windows Admin** — ứng dụng có thể yêu cầu quyền nâng cao khi xóa/di chuyển file hệ thống.
2. **Sao lưu trước khi xóa** — thao tác xóa và dọn duplicate **không thể hoàn tác**.
3. **FFmpeg** — không có `ffprobe` thì kiểm tra video sẽ hạn chế.
4. **Hiệu năng** — quét ổ lớn + perceptual hash tốn CPU; giảm Worker Count nếu cần.

---

## Giấy phép

Phát hành theo [MIT License](LICENSE) — © 2026 [iamhieuxz](https://github.com/iamhieuxz).

---

## Liên hệ

- Repository: [github.com/iamhieuxz/media-tool](https://github.com/iamhieuxz/media-tool)
- Issues & đóng góp: mở Issue hoặc Pull Request trên GitHub
