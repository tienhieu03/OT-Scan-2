# OT Scan Manager

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Giới thiệu

OT Scan Manager là một ứng dụng desktop được thiết kế để quản lý và theo dõi thời gian làm thêm giờ (OT) của nhân viên một cách hiệu quả. Ứng dụng cung cấp giao diện người dùng đồ họa (GUI) thân thiện, cho phép quản lý thông tin nhân viên, ghi nhận thời gian OT (có thể thông qua thiết bị HID), và xuất báo cáo OT ra file Excel.

## Tính năng chính

*   **Quản lý Nhân viên:** Thêm, sửa, xóa thông tin nhân viên trong cơ sở dữ liệu (lưu trữ dưới dạng file Excel).
*   **Ghi nhận OT:** Ghi lại thời gian bắt đầu và kết thúc OT của nhân viên. Hỗ trợ nhập liệu thủ công hoặc thông qua thiết bị đọc thẻ HID (ví dụ: máy chấm công).
*   **Quản lý Log OT:** Lưu trữ lịch sử OT theo tháng, dễ dàng tra cứu và quản lý.
*   **Xuất Báo cáo:** Xuất dữ liệu log OT và danh sách nhân viên ra file Excel.
*   **Sao lưu Dữ liệu:** Tự động hoặc thủ công sao lưu cơ sở dữ liệu nhân viên và log OT để đảm bảo an toàn dữ liệu.
*   **Cấu hình Linh hoạt:** Cho phép tùy chỉnh các cài đặt của ứng dụng thông qua file `settings.json`.
*   **Giao diện Người dùng:** Giao diện đồ họa được xây dựng bằng customtkinter, dễ sử dụng.
*   **Ghi Log Ứng dụng:** Ghi lại các hoạt động và lỗi của ứng dụng để dễ dàng gỡ lỗi.

## Cấu trúc Project

```
.
├── .gitignore             # Cấu hình bỏ qua file cho Git
├── README.md              # File README này
├── LICENSE                # File giấy phép MIT
├── attendance_manager.py  # Module quản lý chấm công/OT
├── config.py              # Module xử lý cấu hình chung
├── employee_manager.py    # Module quản lý thông tin nhân viên
├── hid_handler.py         # Module xử lý giao tiếp với thiết bị HID thật
├── main.py                # Điểm khởi chạy chính của ứng dụng
├── ot_log_manager.py      # Module quản lý log OT
├── OTManager.spec         # File cấu hình cho PyInstaller
├── requirements.txt       # Danh sách các thư viện Python cần thiết
├── settings_manager.py    # Module quản lý cài đặt ứng dụng
├── settings.json          # File lưu trữ cài đặt của ứng dụng
├── simulator_hid_handler.py # Module giả lập thiết bị HID để test
├── ui_manager.py          # Module quản lý giao diện người dùng (GUI)
├── yeu_cau.txt            # (Có thể là file yêu cầu ban đầu)
├── app_logs/              # Thư mục chứa log hoạt động của ứng dụng
├── backup/                # Thư mục chứa các bản sao lưu
│   ├── db_backups/        # Sao lưu cơ sở dữ liệu nhân viên (.xlsx)
│   └── log_backups/       # Sao lưu log OT (.xlsx)
├── build/                 # Thư mục chứa kết quả build của PyInstaller
├── data/                  # Thư mục chứa dữ liệu chính
│   ├── employee_database.xlsx # Cơ sở dữ liệu nhân viên
│   └── logs/              # Thư mục chứa log OT hiện tại
│       └── OT_Log_Thang_MM_YYYY.xlsx # File log OT theo tháng
└── ... (các file khác do PyInstaller tạo ra)
```

## Cài đặt

1.  **Clone repository (Nếu có):**
    ```bash
    git clone <your-repository-url>
    cd <repository-folder>
    ```
2.  **Tạo môi trường ảo (Khuyến nghị):**
    ```bash
    python -m venv venv
    ```
    *   Trên Windows: `.\venv\Scripts\activate`
    *   Trên macOS/Linux: `source venv/bin/activate`
3.  **Cài đặt các thư viện cần thiết:**
    ```bash
    pip install -r requirements.txt
    ```

## Sử dụng

Để chạy ứng dụng, thực thi file `main.py`:

```bash
python main.py
```

Ứng dụng sẽ khởi động giao diện người dùng đồ họa.

## Đóng gói ứng dụng (Sử dụng PyInstaller)

Project đã được cấu hình để đóng gói thành file thực thi (.exe trên Windows) bằng PyInstaller. Sử dụng file `OTManager.spec`:

```bash
pyinstaller OTManager.spec
```

File thực thi sẽ được tạo trong thư mục `dist/OTManager`.

## Các thư viện sử dụng

*   [customtkinter](https://github.com/TomSchimansky/CustomTkinter): Tạo giao diện người dùng đồ họa hiện đại.
*   [pandas](https://pandas.pydata.org/): Xử lý và phân tích dữ liệu, đặc biệt là với file Excel.
*   [openpyxl](https://openpyxl.readthedocs.io/en/stable/): Đọc và ghi file Excel (.xlsx).
*   [pywinusb](https://github.com/pywinusb/pywinusb): Giao tiếp với thiết bị USB HID trên Windows.
*   [Pillow](https://python-pillow.org/): Xử lý hình ảnh (thường là dependency của customtkinter).
*   [pyinstaller](https://pyinstaller.org/en/stable/): Đóng gói ứng dụng Python thành file thực thi độc lập.

## Giấy phép

Project này được cấp phép dưới giấy phép MIT. Xem chi tiết tại file [LICENSE](LICENSE).
