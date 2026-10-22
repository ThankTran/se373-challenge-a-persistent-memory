# Hướng dẫn thực hiện Challenge A

## Bước 1 — Người 2: Copy agent có sẵn

Copy ứng dụng từ `Buổi 5/block-1-refund/stage-01-files` vào project này. Giữ các module hỗ trợ, tools, dữ liệu và cấu hình cần để chạy; không copy `.git`, `.venv`, `.env` hoặc log cũ.

## Bước 2 — Người 1: Thêm phần lưu memory

| File cần thêm | Dùng để làm gì |
| --- | --- |
| `memory_store.py` | Đọc/ghi JSON; cập nhật quy ước hiện hành; lưu lịch sử thay đổi kèm thời gian và session; tạo nội dung memory để nạp vào context. |
| `tools/memory.py` | Tạo tool `update_project_memory` để agent gọi khi cần ghi nhớ hoặc đổi quy ước. |
| `tests/test_memory.py` | Kiểm tra lưu/đọc lại, đổi quy ước, giữ các quy ước khác và không đưa quy ước cũ vào context hiện hành. |

File `memory/project_memory.json` tự tạo khi lưu lần đầu, gồm `current` (quy ước hiện hành) và `history` (lịch sử thay đổi).

Hai người thống nhất các hàm để ghép code:

- `load_memory()`: đọc dữ liệu đã lưu.
- `update_memory(key, value, source_session)`: cập nhật quy ước và lịch sử.
- `render_current_memory()`: trả văn bản chứa quy ước hiện hành.
- `make_memory_tool(session_id)`: tạo tool nhận `key`, `value`; session ID do ứng dụng truyền vào.

## Bước 3 — Người 2: Tích hợp vào agent

| File cần sửa | Công việc |
| --- | --- |
| `agent.py` | Nhận session ID, đăng ký tool từ `make_memory_tool(session_id)` và tạo agent với memory mới nhất mỗi lượt chat. |
| `prompts.py` | Ghép `render_current_memory()` vào system prompt; hướng dẫn agent gọi tool khi người dùng yêu cầu lưu hoặc đổi quy ước. |
| `app.py` | Truyền session ID vào agent; cập nhật danh sách tool hiển thị; giữ nút tạo hội thoại mới chỉ xóa chat, không xóa memory; dùng snapshot context sẵn có để xem memory đã nạp. |
| `.gitignore` | Bỏ qua `.env`, `.venv`, log và memory phát sinh khi chạy. |
| `README.md` | Ghi nguồn agent tái sử dụng, cách chạy và các bước demo. |

Dùng tool memory riêng để ghi `memory/project_memory.json`, vì tool `write_file` cũ chỉ ghi được trong `workspace/output/`.

## Cấu trúc thư mục sau khi hoàn thành

`[MỚI]`: Người 1 thêm. `[SỬA]`: Người 2 cập nhật. Các file còn lại giữ từ agent gốc hoặc project hiện tại. File dữ liệu, môi trường và log được tạo khi chạy; không cần tạo thủ công.

```text
se373-challenge-a-persistent-memory/
├── .env.example                     # Mẫu cấu hình model
├── .env                             # Tạo cục bộ, không commit
├── .gitignore                       # [SỬA] Bỏ qua dữ liệu cục bộ
├── .streamlit/
│   └── config.toml                  # Cấu hình giao diện Streamlit
├── pyproject.toml                   # Dependencies của ứng dụng
├── uv.lock                          # Sinh khi chạy uv sync
├── LICENSE
├── README.md                        # [SỬA] Hướng dẫn chạy và demo
├── HUONG_DAN_THUC_HIEN.md
├── agent.py                         # [SỬA] Đăng ký tool memory
├── app.py                           # [SỬA] Session và giao diện
├── prompts.py                       # [SỬA] Nạp memory vào prompt
├── memory_store.py                  # [MỚI] Đọc, ghi, cập nhật memory
├── config.py                        # Đọc cấu hình ứng dụng/model
├── paths.py                         # Đường dẫn workspace
├── observer.py                      # Chụp context và sự kiện
├── trace.py                         # Ghi trace ra đĩa
├── reset_workspace.py               # Khởi tạo/reset workspace
├── tools/
│   ├── __init__.py
│   ├── files.py                     # Tools đọc/ghi/liệt kê file
│   └── memory.py                    # [MỚI] Tool cập nhật quy ước
├── memory/
│   └── project_memory.json          # Tự tạo khi lưu memory lần đầu
├── fixtures/
│   └── data/
│       └── weekly_notes.md          # Dữ liệu mẫu để tạo workspace
├── workspace/
│   ├── .lab-workspace               # Dấu nhận diện workspace
│   ├── data/
│   │   ├── weekly_notes.md
│   │   └── policies/               # Dữ liệu có sẵn của bản nguồn
│   │       ├── policy-before-oct.md
│   │       └── policy-from-oct.md
│   └── output/                      # File do tool write_file tạo
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_agent.py
│   ├── test_app.py
│   ├── test_files.py
│   ├── test_observer.py
│   ├── test_project.py
│   └── test_memory.py               # [MỚI] Kiểm tra persistent memory
└── traces/                          # Log/snapshot sinh khi chạy
```

Cây trên không liệt kê `.git/`, `.venv/` và cache. `explainer.html` và `check_list_symlink.py` của bản nguồn là tài liệu/script phụ, không cần cho Challenge A.

## Bước 4 — Cả hai: Chạy và kiểm tra

1. Chạy `uv sync` trong thư mục project, tạo `.env` theo `.env.example` và điền cấu hình model.
2. Chạy kiểm tra memory bằng môi trường có `pytest`: `uv run --with pytest pytest tests/test_memory.py`.
3. Mở ứng dụng: `uv run streamlit run app.py`.
4. **Session 1:** yêu cầu ghi nhớ TypeScript, PostgreSQL và xác thực JWT. Kiểm tra file JSON đã lưu.
5. **Session 2:** tạo hội thoại mới, hỏi cách triển khai đăng nhập theo quy ước dự án, không nhắc lại quy ước. Kiểm tra agent dùng JWT và snapshot context có memory.
6. Trong session 2, yêu cầu đổi xác thực sang session cookie. Kiểm tra `current` đã đổi và `history` lưu JWT đã bị thay thế.
7. **Session 3:** tạo hội thoại mới, hỏi lại cách triển khai đăng nhập. Kiểm tra agent dùng session cookie, vẫn giữ TypeScript và PostgreSQL.
8. Khởi động lại ứng dụng để kiểm tra memory vẫn còn. Lưu ảnh câu trả lời, snapshot context và JSON trước/sau thay đổi làm bằng chứng.
