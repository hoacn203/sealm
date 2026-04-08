# SEALM Agent Skill

Tài liệu này mô tả các hàm chính trong [`sealm.py`](sealm.py) để agent khác có thể hiểu nhanh logic điều khiển LDPlayer, nhận diện trạng thái game, và tái sử dụng đúng cách.

## Mục tiêu file [`sealm.py`](sealm.py)

[`sealm.py`](sealm.py) là lớp glue code để:
- nạp trực tiếp source clone từ [`ldplayer-auto/emulator/__init__.py`](ldplayer-auto/emulator/__init__.py:1)
- làm việc với LDPlayer đầu tiên qua [`LDPlayer`](ldplayer-auto/emulator/__init__.py:13)
- thao tác bằng ADB/keyevent/tap thông qua [`ObjectEmulator`](ldplayer-auto/emulator/em_object.py:18)
- nhận diện UI bằng template matching từ thư mục [`images`](images)

## Cách khởi tạo môi trường

### [`ensure_pkg_resources_stub()`](sealm.py:28)
Tạo stub cho `pkg_resources` nếu môi trường Python không có module này.

Lý do:
- source clone trong [`ldplayer-auto/emulator/__init__.py`](ldplayer-auto/emulator/__init__.py:10) dùng `pkg_resources.require(...)`
- trên một số môi trường Python mới, import này có thể lỗi

Khi agent khác dùng lại [`sealm.py`](sealm.py), nên luôn gọi [`ensure_pkg_resources_stub()`](sealm.py:28) trước khi load module clone.

### [`load_module()`](sealm.py:44)
Load module Python trực tiếp từ path file.

Dùng để:
- load package clone từ [`ldplayer-auto/emulator/__init__.py`](ldplayer-auto/emulator/__init__.py:1)
- load file keys từ [`ldplayer-auto/emulator/keys.py`](ldplayer-auto/emulator/keys.py:1)

Nếu cần mở rộng sang module khác trong repo clone, agent nên tái sử dụng [`load_module()`](sealm.py:44) thay vì `pip install` thêm package khác.

## Nhóm hàm điều khiển emulator

### [`warmup_adb()`](sealm.py:62)
Gọi lệnh `devices` thông qua controller của LDPlayer để làm nóng kết nối ADB.

Mục đích:
- tránh lỗi kiểu `device not found`
- nên gọi trước các thao tác [`send_event()`](ldplayer-auto/emulator/em_object.py:313), [`tap()`](ldplayer-auto/emulator/em_object.py:294), hoặc chụp màn hình

Rule cho agent:
- trước các hành động quan trọng trên emulator, ưu tiên gọi [`warmup_adb()`](sealm.py:62)

### [`go_home_by_esc()`](sealm.py:67)
Gửi 2 lần [`KEYCODE_ESCAPE`](ldplayer-auto/emulator/keys.py:112), mỗi lần cách nhau `delay`, sau đó chờ thêm 1 giây.

Ý nghĩa nghiệp vụ:
- dùng để back ra khỏi màn hình hiện tại về gần màn hình chính

### [`select_channel()`](sealm.py:74)
Tap vào tọa độ cố định `(1490, 336)`.

Ý nghĩa nghiệp vụ:
- đây là thao tác chọn kênh theo UI hiện tại của game/LDPlayer

### [`go_home()`](sealm.py:78)
Tap vào `(1382, 200)`, chờ `delay`, rồi tap tiếp `(939, 677)`.

Ý nghĩa nghiệp vụ:
- thao tác home theo flow UI hiện tại
- không phải Android Home key, mà là click theo vị trí UI game

Rule cho agent:
- nếu UI game thay đổi, cần cập nhật tọa độ trong [`go_home()`](sealm.py:78)
- không thay thế hàm này bằng [`go_home_by_esc()`](sealm.py:67), vì hai hàm phục vụ hai flow khác nhau

## Nhóm hàm xử lý ảnh

### [`load_template()`](sealm.py:84)
Đọc một ảnh mẫu bằng OpenCV.

Dùng cho:
- [`detect_auto_state()`](sealm.py:124)
- [`detect_current_map()`](sealm.py:164)

### [`decode_screen()`](sealm.py:91)
Decode bytes screenshot từ emulator thành ảnh OpenCV `numpy.ndarray`.

Nguồn dữ liệu screenshot đến từ [`ObjectEmulator._get_screencap_b64decode()`](ldplayer-auto/emulator/em_object.py:382).

### [`crop_region()`](sealm.py:98)
Crop một vùng ảnh hình chữ nhật nếu có truyền `region=(x1, y1, x2, y2)`.

Dùng khi:
- chỉ muốn so khớp trong một vùng UI nhất định
- tối ưu tốc độ hoặc tránh false positive

### [`match_score()`](sealm.py:113)
Tính điểm khớp template bằng `cv2.matchTemplate(..., cv2.TM_CCOEFF_NORMED)`.

Kết quả:
- trả về `float`
- càng gần `1.0` thì càng giống
- trả `-1.0` nếu template lớn hơn ảnh nguồn

Rule cho agent:
- đây là hàm core cho mọi logic nhận diện bằng ảnh trong [`sealm.py`](sealm.py)

## Nhóm hàm nhận diện trạng thái game

### [`detect_auto_state()`](sealm.py:124)
So khớp screenshot hiện tại với hai ảnh mẫu:
- [`images/auto.png`](images/auto.png)
- [`images/not_auto.png`](images/not_auto.png)

Cách hoạt động:
1. chụp màn hình emulator
2. decode thành ảnh OpenCV
3. crop theo `region` nếu có
4. tính điểm khớp với ảnh `auto` và `not_auto`
5. chọn trạng thái có score cao hơn

Giá trị trả về gồm:
- `state`: `auto` hoặc `not_auto`
- `confidence`
- `auto_score`
- `not_auto_score`
- metadata về kích thước ảnh

Rule cho agent:
- nếu hai nút quá giống nhau, nên truyền `region` hẹp để tăng độ chính xác

### [`map_name_from_template_path()`](sealm.py:157)
Chuyển tên file map như `map_boss4.png` thành tên logic như `BOSS4` hoặc `BOSS 4` tùy convention hiện tại.

Dùng để convert tên template thành tên map hiển thị.

### [`detect_current_map()`](sealm.py:164)
Nhận diện map hiện tại bằng cách:
1. chụp screenshot hiện tại
2. duyệt tất cả file `map_*.png` trong [`images`](images)
3. tính score từng ảnh map
4. lấy template có score cao nhất
5. nếu score >= `threshold` thì kết luận map hiện tại là template đó

Giá trị trả về gồm:
- `map`
- `best_score`
- `threshold`
- `matched_template`
- `screen_size`
- `all_scores`

Rule cho agent:
- để thêm map mới, chỉ cần thêm file `map_<ten>.png` vào thư mục [`images`](images)
- không cần sửa logic trong [`detect_current_map()`](sealm.py:164) nếu vẫn theo convention `map_*.png`

## Luồng demo hiện tại

Trong [`main()`](sealm.py:205), flow đang là:
1. gọi [`ensure_pkg_resources_stub()`](sealm.py:28)
2. load source clone bằng [`load_module()`](sealm.py:44)
3. tạo [`LDPlayer`](ldplayer-auto/emulator/__init__.py:13)
4. lấy emulator đầu tiên `ld.emulators[0]`
5. gọi [`warmup_adb()`](sealm.py:62)
6. gọi [`go_home_by_esc()`](sealm.py:67)
7. gọi [`go_home()`](sealm.py:78)

## Quy ước mở rộng cho agent khác

Khi thêm behavior mới vào [`sealm.py`](sealm.py), agent nên làm theo nguyên tắc sau:
- thao tác điều khiển UI bằng hàm riêng, ví dụ kiểu [`go_home()`](sealm.py:78), [`select_channel()`](sealm.py:74)
- thao tác nhận diện bằng ảnh dùng chung [`load_template()`](sealm.py:84), [`decode_screen()`](sealm.py:91), [`match_score()`](sealm.py:113)
- mọi ảnh mẫu mới đặt trong thư mục [`images`](images)
- nếu là map, đặt tên theo convention `map_*.png`
- nếu là trạng thái nhị phân, viết hàm tương tự [`detect_auto_state()`](sealm.py:124)
- trước khi thao tác emulator, ưu tiên gọi [`warmup_adb()`](sealm.py:62)

## Tóm tắt nhanh cho agent

- Load source clone: [`load_module()`](sealm.py:44)
- Fix tương thích `pkg_resources`: [`ensure_pkg_resources_stub()`](sealm.py:28)
- Warm ADB: [`warmup_adb()`](sealm.py:62)
- Back ra màn hình chính: [`go_home_by_esc()`](sealm.py:67)
- Home theo UI game: [`go_home()`](sealm.py:78)
- Chọn kênh: [`select_channel()`](sealm.py:74)
- Check auto/not auto: [`detect_auto_state()`](sealm.py:124)
- Check map hiện tại theo ảnh `map_*.png`: [`detect_current_map()`](sealm.py:164)
