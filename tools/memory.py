"""Tool `update_project_memory` để agent ghi nhớ / đổi quy ước dự án."""

from __future__ import annotations

import json

from langchain_core.tools import BaseTool, tool

import memory_store


def _error(code: str, message: str) -> str:
    return json.dumps(
        {"ok": False, "error": {"code": code, "message": message}}, ensure_ascii=False
    )


def make_memory_tool(session_id: str) -> BaseTool:
    """Tạo tool memory khép kín `session_id` của hội thoại hiện tại."""

    @tool("update_project_memory")
    def update_project_memory(key: str, value: str) -> str:
        """Ghi nhớ hoặc đổi MỘT quy ước của dự án (ngôn ngữ, database, cách xác thực, kiểu API...).

        Chỉ gọi khi người dùng yêu cầu "nhớ / ghi nhớ / từ giờ dùng / đổi sang".
        KHÔNG gọi khi người dùng chỉ hỏi.

        Args:
            key: slug tiếng Anh, chữ thường, gạch dưới. Ví dụ: language, database, auth.
            value: quy ước mới, ngắn gọn, một dòng. Khi đổi quy ước hãy truyền GIÁ TRỊ MỚI
                (giá trị mới thay thế giá trị cũ). Chưa hỗ trợ xóa: nếu bỏ quy ước,
                ghi giá trị mô tả "không dùng nữa".
        """
        try:
            result = memory_store.update_memory(key, value, session_id)
        except memory_store.InvalidKeyError as exc:
            return _error("MEMORY_KEY_INVALID", str(exc))
        except memory_store.InvalidValueError as exc:
            return _error("MEMORY_VALUE_INVALID", str(exc))
        except OSError as exc:
            return _error("MEMORY_WRITE_FAILED", f"Không ghi được memory: {exc}")
        except Exception as exc:  # noqa: BLE001 - tool phải luôn trả JSON
            return _error("MEMORY_UPDATE_FAILED", str(exc))
        return json.dumps(result, ensure_ascii=False)

    return update_project_memory