# Challenge A — Persistent Memory

Tái sử dụng `Buổi 5/block-1-refund/stage-01-files` (LangChain + Streamlit).

## Chạy ứng dụng

Cần Python 3.11+ và uv. Chạy trong thư mục project:

```powershell
uv sync
Copy-Item .env.example .env
# Điền OPENAI_API_KEY, MODEL_NAME và OPENAI_BASE_URL (nếu cần) vào .env.
uv run streamlit run app.py
```

Chỉ copy `.env.example` khi chưa có `.env`. Model phải hỗ trợ tool calling.

## Memory hoạt động thế nào

- Tool `update_project_memory` lưu quy ước vào `memory/project_memory.json`.
- Session ID do ứng dụng truyền vào tool, không do model cung cấp.
- `current` lưu quy ước hiện hành; `history` lưu thay đổi kèm session và thời gian.
- Mỗi lượt chat, agent đọc lại `current` và ghép vào system prompt. Thay đổi trong một lượt được đưa vào system prompt từ lượt tiếp theo.
- Nút **Cuộc trò chuyện mới** xóa lịch sử chat và tạo ID mới, giữ memory trên đĩa.
- Xem **State & Context → Snapshot: system prompt** để kiểm tra context thực sự đã gửi model. Phần “Context cấu hình” trước lượt gọi đầu tiên chỉ là bản xem trước.

## Demo

1. Session 1: “Ghi nhớ dự án dùng TypeScript, PostgreSQL và xác thực JWT.”
2. Tạo hội thoại mới. Hỏi: “Đề xuất triển khai đăng nhập theo quy ước dự án.” Kiểm tra snapshot có quy ước đã lưu.
3. Yêu cầu: “Chuyển xác thực sang session cookie, giữ nguyên các quy ước khác.”
4. Tạo hội thoại mới, hỏi lại câu ở bước 2. Snapshot phải chứa session cookie thay JWT.
5. Khởi động lại app và kiểm tra memory vẫn còn.

## Kiểm tra

```powershell
uv run pytest -q
```

Tests dùng model giả để kiểm tra tool, session và context thực tế qua Streamlit; không gọi API. Demo với model thật cần chạy riêng theo các bước trên.

Nếu memory bị hỏng hoặc không đọc được, ứng dụng báo lỗi và dừng chat; tool trả MEMORY_READ_FAILED, không ghi đè file. Sửa file hoặc khôi phục bản sao lưu rồi chạy lại.
