# assignment1-cn

## Tracker

    - Method hashing_file để lưu file_hash
    - 1 file txt lưu trữ tên của tất cả file hash (không dùng mảng để lưu vì đề phòng server mất kết nối)
    - Định dạng sẽ là filehash : metainfofile (VD: abc123 : xyz.torrent)
    - Một hàm get_peers(filehash) để tìm kiếm các peers chứa piece của file tương ứng với filehash
    - Một file txt để lưu trữ tất cả thông tin (ip, port, peer_id) của tất cả peer trong mạng
    - Một hàm để kết nối 1 peer mới vào trong mạng (lưu thông tin vào txt)
    - Một hàm xoá 1 peer ra khỏi mạng (xoá thông tin khỏi txt)

## hashing

    - Xài thư viện hashlib và encode sha256

## Peer

    - Kết nối với Tracker qua socket + validate peer id
    - Giữ socket kết nối với Tracker để khi peer xảy ra lỗi đột ngột, Tracker tự bỏ peer đó
    - Menu cho peer có 3 sự lựa chọn: get file (show tất cả các file có trong meta info); peer upload (khai báo file nhằm cho Tracker biết file này public cho mọi peer trong hệ thống); peer download (tải các piece của file từ những seeder, seeder ở đây có nghĩa là những người giữ đúng piece đang cần hoặc người có full file)
