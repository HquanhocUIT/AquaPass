# Backend

Backend dùng kiến trúc modular monolith.

- Quân phụ trách database, API, FHIR, vòng đời yêu cầu và lưu lịch sử.
- Sang phụ trách evidence graph, AI, ranking, constraints và đánh giá.

Mỗi module chỉ nên làm một việc rõ ràng. Không tách microservice trong thời gian hackathon.

