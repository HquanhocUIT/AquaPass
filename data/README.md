# Data

Thư mục này chứa dữ liệu mô phỏng và dữ liệu đánh giá.

- `demo/`: tình huống chính dùng trong video.
- `fixtures/`: dữ liệu cố định để kiểm thử.
- `evaluation/`: các tình huống có đáp án chuẩn để kiểm tra ranking.
- `demo/candidate_evidence.csv`: catalog giả định về bằng chứng có thể thu thập cho tình huống mô phỏng; được API intelligence dùng để dựng các lựa chọn, chi phí, thời gian và năng lực cần có.

Mọi dữ liệu tự tạo phải ghi rõ là dữ liệu mô phỏng, không được trình bày như dữ liệu đo ngoài đời thật.

Các chiều ranking trong catalog nằm trong khoảng `0..1`; trọng số prototype là
`0.40` decision value, `0.25` reliability, `0.15` feasibility, trừ `0.10`
cost và `0.10` time. Đây là giả định có thể tái lập để đánh giá luồng, chưa
được hiệu chỉnh bằng dữ liệu thực tế. Thời gian, chi phí và năng lực actor cũng
là giá trị mô phỏng. Catalog không chứa đáp án chuẩn và không được dùng như
nhãn đánh giá.

