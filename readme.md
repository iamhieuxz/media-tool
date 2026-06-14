# Media Scanner Pro

**Media Scanner Pro** là bộ công cụ quét và quản lý thư viện media trên Windows (và CLI đa nền tảng). Ứng dụng giúp bạn:

- Quét hàng loạt ảnh và video trong một hoặc nhiều thư mục / ổ đĩa
- Phát hiện file **bị hỏng** (corrupted) bằng nhiều lớp kiểm tra
- Tìm file **trùng lặp** theo hash chính xác hoặc perceptual hash (ảnh tương tự)
- Xem trước, so sánh, xóa hoặc cách ly file trực tiếp từ giao diện
- Xuất báo cáo CSV và lưu lịch sử quét vào SQLite

---

## Tính năng chính

| Tính năng | Mô tả |
|-----------|--------|
| Quét đa đường dẫn | Chọn nhiều thư mục hoặc thêm toàn bộ ổ đĩa Windows |
| Kiểm tra file lỗi | PIL + OpenCV cho ảnh; ffprobe cho video |
| Phát hiện trùng lặp | SHA256 / MD5 (exact) hoặc pHash / dHash (perceptual) |
| Giao diện Flet | Dark/Light theme, preview, zoom, so sánh cặp duplicate |
| Thao tác file | Xóa, cách ly (quarantine), mở thư mục |
| CLI headless | Quét không GUI, xuất CSV tự động |
| Đóng gói EXE | PyInstaller one-file, yêu cầu quyền Admin trên Windows |

### Định dạng media hỗ trợ

- **Ảnh:** `.jpg`, `.jpeg`, `.png`, `.webp`, `.bmp`, `.tif`, `.tiff`, `.gif`
- **Video:** `.mp4`, `.mkv`, `.avi`, `.mov`, `.wmv`, `.flv`, `.webm`, `.m4v`

---

## Yêu cầu hệ thống

- **Python** 3.10 trở lên (khuyến nghị 3.11+)
- **Windows** (GUI tối ưu; CLI chạy trên Linux/macOS)
- **FFmpeg** (tùy chọn nhưng khuyến nghị): cài `ffprobe` vào PATH để kiểm tra video chính xác hơn

---

## Cài đặt

```bash
# Clone repository
git clone https://github.com/iamhieuxz/media-tool.git
cd media-tool

# Tạo virtual environment (khuyến nghị)
python -m venv .venv

# Windows
.venv\Scripts\activate

# Cài dependencies
pip install -r requirements.txt
```

### Dependencies

| Gói | Mục đích |
|-----|----------|
| `flet` | Giao diện desktop |
| `Pillow` | Đọc / validate ảnh |
| `opencv-python` | Kiểm tra ảnh nâng cao |
| `imagehash` | Perceptual hash (pHash, dHash) |

Để build EXE, cài thêm PyInstaller:

```bash
pip install pyinstaller
```

---

## Hướng dẫn sử dụng

### 1. Chế độ GUI (khuyến nghị)

```bash
python main.py --gui
```

Hoặc chạy không tham số — mặc định mở GUI nếu bạn sửa entry point; hiện tại cần flag `--gui`:

```bash
python main.py --gui
```

**Quy trình quét:**

1. **Chọn đường dẫn** — nhập path, dùng *Browse* chọn thư mục, hoặc *Add Drive* để quét ổ đĩa.
2. **Start Scan** — ứng dụng chạy hai giai đoạn:
   - Kiểm tra file lỗi (corruption check)
   - Phát hiện trùng lặp (duplicate detection)
3. **Xem kết quả** — bảng hiển thị file lỗi và nhóm duplicate; dùng ô tìm kiếm để lọc.
4. **Preview** — chọn một dòng để xem thumbnail, metadata (kích thước, độ phân giải, codec…).
5. **Compare** — với file duplicate, so sánh side-by-side với file cùng nhóm.
6. **Thao tác hàng loạt** (footer):
   - *Export* / *Save Report* → `invalid_media.csv`, `duplicate_media.csv`
   - *Clean Duplicates* → giữ file đầu mỗi nhóm, xóa bản sao
   - *Clean Corrupted* → xóa toàn bộ file lỗi
   - *Delete Selected* → xóa các dòng đã chọn
   - *Quarantine* → di chuyển file lỗi vào thư mục `quarantine/`

**Điều khiển quét:** *Pause* / *Resume*, *Stop* (dừng an toàn sau file hiện tại).

### 2. Cài đặt (Settings)

Mở biểu tượng ⚙️ trên header:

| Tuỳ chọn | Ý nghĩa |
|----------|---------|
| **Hash Level** | Level 1: MD5/SHA256 (trùng byte); Level 2: Perceptual (ảnh giống nhau) |
| **Similarity Threshold** | Ngưỡng % cho perceptual hash (mặc định 95) |
| **Worker Count** | Số luồng song song (`0` = tự động theo CPU) |
| **Auto Save Results** | Lưu thống kê quét vào SQLite (`data/app.db`) |

### 3. Chế độ CLI

Quét thư mục hiện tại:

```bash
python main.py
```

Quét một hoặc nhiều path:

```bash
python main.py --path "D:\Photos" "E:\Backup\videos"
```

Kết quả ghi ra:

- `invalid_media.csv` — danh sách file lỗi
- `duplicate_media.csv` — các nhóm file trùng lặp

Log CLI ghi vào `app.log` (hoặc file log cấu hình trong `src/utils/logging_config.py`).

### 4. Build file EXE (Windows)

```bash
python build_exe.py
```

File đầu ra: `dist/MediaTool.exe` (one-file, windowed, UAC Admin).

---

## Cấu trúc dự án

```
media-tool/
├── main.py                 # Entry point CLI / GUI
├── requirements.txt
├── build_exe.py            # PyInstaller wrapper
├── src/
│   ├── constants.py        # Hằng số, extension media
│   ├── core/               # Checker, deduplicator, hash engines
│   ├── db/                 # SQLite settings & scan history
│   ├── gui/                # Flet UI components
│   ├── models/             # Serializers, duplicate group manager
│   ├── services/           # MediaInspector, DuplicateService
│   └── utils/              # File ops, ffmpeg, thumbnails, logging
├── logs/                   # Log phiên quét (tạo khi chạy)
├── data/                   # SQLite DB, thumbnail cache
└── quarantine/             # File lỗi được cách ly
```

---

## Kiến trúc xử lý

```
Scan paths → MediaFileScanner → danh sách file + size
                    ↓
         MediaChecker (PIL / OpenCV / ffprobe)
                    ↓
         invalid_media.csv + UI tab "Corrupted"
                    ↓
         DuplicateFinder (size bucket → hash / pHash)
                    ↓
         duplicate_media.csv + UI tab "Duplicates"
```

- **Exact duplicate:** nhóm theo kích thước file → hash SHA256/MD5 toàn file.
- **Perceptual duplicate:** pHash/dHash trên ảnh, gom nhóm theo Hamming distance và ngưỡng similarity.
- **Corruption:** ảnh qua PIL verify + OpenCV decode; video qua ffprobe (nếu có).

---

## Lưu ý quan trọng

1. **Quyền Admin (Windows):** ứng dụng tự yêu cầu elevation để xóa/di chuyển file hệ thống hoặc trên ổ đĩa bảo vệ.
2. **Sao lưu trước khi xóa:** thao tác *Clean Duplicates* và *Clean Corrupted* **không thể hoàn tác**.
3. **FFmpeg:** nếu không có `ffprobe`, kiểm tra video sẽ hạn chế hơn.
4. **Hiệu năng:** quét ổ đĩa lớn + perceptual hash tốn CPU/RAM; giảm worker count nếu máy chậm.

---

## Đánh giá nhanh (Product Review)

**Điểm mạnh**

- Pipeline quét thống nhất: một lần quét vừa tìm lỗi vừa tìm duplicate.
- UI hoàn chỉnh: progress ETA, stat cards, preview/compare, dark mode.
- Kiến trúc tách lớp rõ (`core` / `services` / `gui`), dễ mở rộng.
- Hỗ trợ multi-root scan và cache thumbnail.
- Có CLI cho automation và PyInstaller cho phân phối.

**Hạn chế / cải tiến có thể**

- Một số nhãn UI còn tiếng Anh, code comment tiếng Việt — có thể thống nhất i18n.
- `HashLevel.VIDEO_SIMILARITY` / `NEAR_DUPLICATE` đã định nghĩa nhưng chưa expose đầy đủ trong Settings.
- Chưa có unit test tự động trong repo.
- CLI mặc định quét `cwd` nếu không truyền `--path`; cần `--gui` rõ ràng cho GUI.

---

## Giấy phép

Dự án mã nguồn mở — thêm file `LICENSE` nếu bạn chọn giấy phép cụ thể (MIT, Apache-2.0, …).

---

## Liên hệ & Repository

- GitHub: [https://github.com/iamhieuxz/media-tool](https://github.com/iamhieuxz/media-tool)
