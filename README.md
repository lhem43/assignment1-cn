# assignment1-cn

## Tracker
    - Method hashing_file để lưu file_hash 
    - 1 file txt lưu trữ tên của tất cả file hash (không dùng mảng để lưu vì đề phòng server mất kết nối)
    - Định dạng sẽ là filehash : metainfofile (VD: abc123 : xyz.torrent)
    - Một hàm get_peers(filehash) để tìm kiếm các peers chứa piece của file tương ứng với filehash
    - Một file txt để lưu trữ tất cả thông tin (ip, port, peer_id) của tất cả peer trong mạng
    - Một hàm để kết nối 1 peer mới vào trong mạng (lưu thông tin vào txt)
    - Một hàm xoá 1 peer ra khỏi mạng (xoá thông tin khỏi txt)
    