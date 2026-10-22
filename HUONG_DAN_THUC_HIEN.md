# Challenge A — Persistent Memory

## 1. Mục tiêu

Tái sử dụng agent đã có để ghi nhớ quy ước dự án qua nhiều session và cập nhật khi quy ước thay đổi.

Theo slide buổi 7, trang 14–15, cần chứng minh:

1. Session mới vẫn áp dụng đúng quy ước đã thống nhất.
2. Sau khi đổi quy ước, các session tiếp theo áp dụng quy ước mới.
3. Hiển thị phần memory thực sự được inject vào context để kiểm chứng.

Timebox: **30 phút**. Nhóm gồm **2 người**.

## 2. Agent được tái sử dụng

- Nguồn: `../../Buổi 5/block-1-refund/stage-01-files/` tính từ thư mục project này.
- Đích: project `se373-challenge-a-persistent-memory` hiện tại.
- Công nghệ có sẵn: Python, LangChain và Streamlit.
- Thành phần tận dụng: vòng lặp agent, tools đọc/ghi/liệt kê file, giao diện chat, nút tạo hội thoại mới, observer và snapshot context.

Agent gốc chưa có cơ chế tự lưu và nạp quy ước dự án. Nhóm sẽ bổ sung cơ chế này, không cần xây lại toàn bộ ứng dụng.

## 3. Chuẩn bị chung — 5 phút

Chỉ định một người sao chép ứng dụng nguồn vào project hiện tại, sau đó cả hai làm trên cùng cấu trúc đã thống nhất.

- Sao chép các module Python của ứng dụng, thư mục `tools`, `tests`, `fixtures`, cấu hình Streamlit và các dữ liệu cần để khởi tạo workspace.
- Sao chép `pyproject.toml` và `.env.example` nếu có.
- Giữ lịch sử Git, LICENSE và README của project đích; cập nhật README để ghi nhận nguồn tái sử dụng.
- Không sao chép `.git`, `.venv`, cache, traces cũ hoặc file `.env` chứa API key.
- Bổ sung `.gitignore` cho `.env`, `.venv/`, cache, traces và memory phát sinh khi chạy. Nếu cần nộp dữ liệu minh họa, dùng file mẫu riêng không chứa thông tin nhạy cảm.
- Chạy project độc lập: dùng `uv sync` theo README nguồn, sau đó `uv run streamlit run app.py` trong thư mục project đích. Không dùng tùy chọn `--locked` khi chưa có lockfile phù hợp.
- Cấu hình API key và model hỗ trợ tool calling trong `.env` cục bộ theo `.env.example`.

Cấu trúc dưới đây chỉ liệt kê các file chính; vẫn giữ các module hỗ trợ mà ứng dụng gốc import:

```text
se373-challenge-a-persistent-memory/
├── agent.py
├── app.py
├── prompts.py
├── config.py
├── paths.py
├── observer.py
├── trace.py
├── reset_workspace.py
├── memory_store.py             # Người 1
├── tools/
│   ├── __init__.py
│   ├── files.py
│   └── memory.py               # Người 1
├── memory/
│   └── project_memory.json     # Tự tạo khi ghi lần đầu
├── tests/
│   └── test_memory.py          # Người 1
├── pyproject.toml
├── README.md                   # Người 2
└── HUONG_DAN_THUC_HIEN.md
```

## 4. Thống nhất giao diện trước khi chia việc

### API của module lưu trữ

```python
load_memory() -> dict

update_memory(
    key: str,
    value: str,
    source_session: str,
) -> dict

render_current_memory() -> str
```

- `load_memory`: đọc JSON; nếu chưa có file, trả cấu trúc rỗng.
- `update_memory`: lưu thay đổi và trả kết quả có `ok`, `changed`, `key`, `old_value`, `new_value`; lỗi phải có thông tin rõ ràng.
- `render_current_memory`: chỉ chuyển phần `current` thành văn bản để inject. Khi rỗng, trả thông báo chưa có quy ước đã lưu.
- Dùng đường dẫn cố định tương đối với `__file__`, ví dụ `Path(__file__).resolve().parent / "memory" / "project_memory.json"`.
- Phạm vi demo: một project, thao tác tuần tự; chưa cần xử lý nhiều người ghi đồng thời.

### Tool và session ID

Model chỉ cần truyền `key`, `value` cho tool `update_project_memory`. Session ID phải do chương trình cung cấp.

Một cách tích hợp đơn giản là Người 1 cung cấp factory:

```python
make_memory_tool(session_id: str)
```

Factory trả về tool đã giữ session ID trong closure. Người 2 truyền `conversation_id` hiện tại khi tạo agent. Không đặt `source_session` thành tham số để model tự bịa.

### Schema dữ liệu

```json
{
  "project_id": "demo-project",
  "current": {
    "language": "TypeScript",
    "database": "PostgreSQL",
    "authentication": "JWT"
  },
  "history": []
}
```

Khi đổi JWT sang session cookie, thay giá trị trong `current.authentication` và thêm vào `history`:

```json
{
  "key": "authentication",
  "old_value": "JWT",
  "new_value": "session cookie",
  "status": "superseded",
  "source_session": "session-id-do-ung-dung-cap",
  "changed_at": "thoi-gian-ISO-8601-thuc-te"
}
```

Hai giá trị ví dụ cuối phải được thay bằng session ID và thời gian thật khi chạy.

## 5. Người 1 — Lưu trữ và tool memory

**Phạm vi file:** `memory_store.py`, `tools/memory.py`, `tests/test_memory.py`.

### Công việc

1. Viết `load_memory()` đọc JSON UTF-8 và trả cấu trúc rỗng khi file chưa tồn tại.
2. Viết `update_memory()`:
   - Kiểm tra key/value hợp lệ; thống nhất các key demo là `language`, `database`, `authentication`.
   - Thêm quy ước mới vào `current`.
   - Nếu giá trị thay đổi, ghi giá trị cũ/mới, session và thời gian vào `history`, đánh dấu giá trị cũ đã bị thay thế.
   - Nếu giá trị giống hiện tại, trả `changed: false`, không thêm lịch sử trùng.
   - Giữ nguyên các quy ước không liên quan.
   - Ghi qua file tạm cùng thư mục rồi thay thế file đích để hạn chế file bị ghi dở.
   - Nếu file hỏng hoặc ghi thất bại, báo lỗi; không âm thầm xóa dữ liệu.
3. Viết `render_current_memory()` chỉ xuất quy ước hiện hành.
4. Viết `make_memory_tool(session_id)` tạo tool `update_project_memory`, gọi lớp lưu trữ và trả kết quả thật.
5. Viết kiểm tra dùng thư mục tạm, tránh sửa memory demo:
   - Chưa có file.
   - Ghi và đọc lại dữ liệu từ ổ đĩa.
   - Đổi JWT sang session cookie.
   - Giữ TypeScript/PostgreSQL sau khi đổi xác thực.
   - Không tạo lịch sử khi giá trị không đổi.
   - JWT không còn trong phần context hiện hành sau khi đổi.
   - File JSON hỏng được báo lỗi và không bị ghi đè.

### Bàn giao

- API đúng thỏa thuận ở mục 4.
- Tool có thể đăng ký vào agent.
- Các kiểm tra bộ nhớ chạy đạt.
- Ví dụ dữ liệu trước/sau cập nhật để Người 2 đối chiếu.

## 6. Người 2 — Agent, context, giao diện và tài liệu

**Phạm vi file:** `agent.py`, `prompts.py`, `app.py`, `README.md`; cập nhật cấu hình hoặc exports nếu cần. Không sửa các file Người 1 đang phụ trách.

### Công việc

1. Sửa `build_agent()` nhận session ID và thêm tool từ `make_memory_tool(session_id)` vào danh sách tools hiện có.
2. Trong `app.py`, truyền `st.session_state.conversation_id` khi tạo agent. Đồng bộ danh sách tools trong phần capabilities/schema hiển thị để tool memory xuất hiện đúng.
3. Trong `prompts.py`, thêm chỉ dẫn:
   - Khi người dùng yêu cầu ghi nhớ hoặc cập nhật quy ước, gọi tool memory.
   - Chỉ nói đã lưu sau khi tool thành công.
   - Áp dụng quy ước hiện hành khi trả lời yêu cầu liên quan.
   - Không coi giá trị đã bị thay thế là quy ước còn hiệu lực.
4. Đọc `render_current_memory()` và ghép vào system prompt khi tạo agent mỗi lượt chat. Ứng dụng gốc tạo agent trong `run_turn()`, nên đây là điểm tích hợp thuận tiện.
5. Giữ nút **Cuộc trò chuyện mới**: tạo ID mới, xóa lịch sử chat và state hội thoại; không xóa file memory.
6. Hiển thị memory hiện hành và dùng snapshot request đã có để kiểm chứng context thực tế:
   - Nội dung file đang hiển thị chỉ là dữ liệu trên đĩa.
   - Snapshot trước model call mới là bằng chứng nội dung đã được đưa vào context.
7. Cập nhật README: nguồn tái sử dụng, cài đặt/chạy, cơ chế memory, demo và kết quả kiểm chứng thật.

### Lưu ý tích hợp

- Tool `write_file` cũ chỉ ghi trong `workspace/output/`. Dùng tool memory chuyên dụng cho `memory/project_memory.json`; không cần mở rộng quyền ghi của tool cũ.
- Với cách nạp lúc tạo agent mỗi lượt, thay đổi được phản ánh trong system prompt từ lượt chat tiếp theo. Trong lượt cập nhật, model nhận kết quả mới qua tool result. Không tuyên bố system prompt tự đổi ngay giữa cùng một lượt.
- Không hard-code TypeScript, PostgreSQL, JWT hoặc session cookie vào system prompt. Các giá trị phải đến từ memory lưu trên đĩa.
- Chỉ inject `current`; giữ `history` để tra cứu. Không nạp toàn bộ chat cũ vào session mới.

### Bàn giao

- Ứng dụng chạy được với tool memory đã đăng ký.
- Session mới có lịch sử rỗng và context chứa memory từ file.
- README hướng dẫn đủ để người khác tái hiện demo.

## 7. Kịch bản kiểm thử chung — 10 phút cuối

Trước demo, dùng memory rỗng dành riêng cho kiểm thử. Không xóa dữ liệu người dùng thật để tạo trạng thái demo.

| Bước | Thao tác hoặc prompt | Kết quả cần kiểm chứng |
| --- | --- | --- |
| 1 — Session 1 | “Ghi nhớ: dự án dùng TypeScript, PostgreSQL và xác thực JWT.” | Tool lưu thành công; JSON có đủ ba quy ước. |
| 2 | Bấm “Cuộc trò chuyện mới”. | Session ID đổi; lịch sử hội thoại rỗng; file memory vẫn còn. |
| 3 — Session 2 | “Hãy đề xuất cách triển khai đăng nhập theo quy ước dự án.” | Context và câu trả lời áp dụng TypeScript, PostgreSQL, JWT. |
| 4 — Session 2 | “Chuyển xác thực sang session cookie, giữ nguyên các quy ước khác.” | `current` cập nhật; lịch sử ghi JWT đã bị thay thế. |
| 5 | Tạo session mới lần nữa. | Không mang lịch sử session 2 sang session 3. |
| 6 — Session 3 | “Hãy đề xuất cách triển khai đăng nhập theo quy ước dự án.” | Context hiện hành dùng session cookie; câu trả lời áp dụng quy ước mới. |
| 7 | Dừng và chạy lại ứng dụng, mở hội thoại mới rồi hỏi lại. | Dữ liệu vẫn được nạp từ file trên ổ đĩa. |

Không nhắc đáp án trong câu hỏi kiểm tra session mới, ví dụ không hỏi “Dự án dùng JWT đúng không?”. Việc nhắc lại có thể khiến model trả lời đúng dù memory chưa hoạt động.

### Bằng chứng cần lưu

- JSON sau lần ghi ban đầu.
- Snapshot context và câu trả lời của session 2.
- JSON sau thay đổi, gồm `current` và `history`.
- Snapshot context và câu trả lời của session 3.
- Kết quả kiểm tra module memory và kết quả khởi động lại ứng dụng.

Chỉ ghi “đã kiểm chứng” cho thao tác thực sự chạy thành công. Kiểm tra module JSON đạt chưa đủ chứng minh agent đã áp dụng quy ước; cần cả demo với model.

## 8. Tiến độ và tiêu chí hoàn thành

| Thời gian | Người 1 | Người 2 |
| --- | --- | --- |
| 0–5 phút | Cùng chuẩn bị code và thống nhất API/schema. | Cùng chuẩn bị code và thống nhất API/schema. |
| 5–20 phút | Module memory, tool và kiểm tra. | Tích hợp agent/context/UI theo API đã thống nhất, viết README. |
| 20–30 phút | Ghép tool, kiểm tra dữ liệu và lịch sử thay đổi. | Chạy demo ba session, xem snapshot và lưu bằng chứng. |

Checklist hoàn thành:

- [ ] Tái sử dụng agent Buổi 5 và ghi rõ nguồn trong README.
- [ ] Memory tồn tại trên ổ đĩa sau khi đóng ứng dụng.
- [ ] Agent có tool lưu/cập nhật quy ước và báo đúng kết quả.
- [ ] Session mới không có chat cũ nhưng vẫn áp dụng quy ước đã lưu.
- [ ] Quy ước mới thay thế quy ước cũ; không làm mất quy ước khác.
- [ ] Có lịch sử thay đổi với nguồn session và thời gian.
- [ ] Có snapshot context chứng minh memory được inject.
- [ ] Có hướng dẫn chạy và bằng chứng kiểm thử thật.

## 9. Lời trình bày ngắn khi demo

**Người 1:** “Nhóm tái sử dụng agent file tools của Buổi 5. Em phụ trách lưu quy ước vào JSON và tool cập nhật. Khi đổi quy ước, giá trị mới được đưa vào `current`, còn giá trị cũ được lưu trong lịch sử với session và thời gian thay thế.”

**Người 2:** “Em phụ trách nạp quy ước hiện hành vào context mỗi lượt và kiểm chứng qua snapshot. Em sẽ tạo session mới để chứng minh agent vẫn nhớ, sau đó đổi JWT sang session cookie và tạo session tiếp theo để kiểm tra agent áp dụng quy ước mới.”
