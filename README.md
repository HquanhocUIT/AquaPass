# AquaPass

AquaPass là hệ thống hỗ trợ tìm bằng chứng cần thu thập tiếp theo trước khi con người đưa ra một quyết định One Health.

## Luồng chính

1. Mở một sự cố.
2. Xem câu hỏi cần quyết định.
3. Tìm bằng chứng còn thiếu.
4. Xếp hạng bằng chứng nên lấy tiếp theo.
5. Tạo yêu cầu thu thập bằng chứng.
6. Nhận kết quả qua API hoặc FHIR.
7. Đưa kết quả về đúng sự cố cũ.
8. Cập nhật quyết định và chờ con người phê duyệt.

## Phân công chính

- Phú: `frontend/`
- Quân: backend, API, database, FHIR, orchestration và deployment
- Sang: dữ liệu, AI, evidence graph, ranking, constraints và evaluation

Xem giải thích chi tiết trong `STRUCTURE.md`.

