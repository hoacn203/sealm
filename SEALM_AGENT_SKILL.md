# SEALM Agent Skill

Tài liệu này tóm tắt trạng thái hiện tại của [`sealm.py`](sealm.py) để agent hoặc phiên làm việc sau có thể nắm nhanh kiến trúc, flow nghiệp vụ, các tọa độ hardcode, và cách mở rộng mà không phải đọc lại toàn bộ file từ đầu.

## 1. Mục tiêu tổng thể của [`sealm.py`](sealm.py)

[`sealm.py`](sealm.py) hiện là file điều phối chính cho toàn bộ automation SEALM trên LDPlayer, gồm 4 phần lớn:

- nạp thư viện clone cục bộ từ [`ldplayer-auto/emulator/__init__.py`](ldplayer-auto/emulator/__init__.py:1)
- điều khiển emulator bằng tap / drag / keyevent / adb
- nhận diện UI bằng OpenCV template matching từ thư mục [`images`](images)
- cung cấp GUI quản lý nhiều cửa sổ LDPlayer bằng [`LDPlayerManagerApp`](sealm.py:703)

File này không còn là script chạy 1 emulator đơn lẻ. Entry point [`main()`](sealm.py:1051) hiện mở GUI quản lý nhiều cửa sổ LDPlayer đang chạy.

## 2. Các hằng số và giả định quan trọng

### Đường dẫn LDPlayer
- thư mục LDPlayer đang dùng là [`LDPLAYER_DIR`](sealm.py:26) = `D:/LDPlayer/LDPlayer9`

### Template ảnh
Các ảnh template đang dùng nằm trong [`images`](images):
- auto: [`images/auto.png`](images/auto.png)
- not auto: [`images/not_auto.png`](images/not_auto.png)
- done loading: [`images/done_loading.png`](images/done_loading.png)
- boss done: [`images/boss_done.png`](images/boss_done.png)
- icon boss 1..4: [`BOSS_ICON_TEMPLATES`](sealm.py:33)
- map templates theo convention `map_*.png`, ví dụ [`images/map_boss1.png`](images/map_boss1.png)

### Hardcode tọa độ
Toàn bộ hardcode hiện đã scale theo layout LDPlayer `1280x720`, không còn là `1600x900`.

Nếu UI game thay đổi, cần ưu tiên kiểm tra các hàm tap/drag sau:
- [`select_channel()`](sealm.py:127)
- [`go_home()`](sealm.py:131)
- [`go_map_5x()`](sealm.py:137)
- [`dismantle_items()`](sealm.py:163)
- [`go_to_boss()`](sealm.py:189)
- [`select_channel_boss()`](sealm.py:222)
- [`enable_auto()`](sealm.py:409)

## 3. Cách nạp thư viện LDPlayer clone

### [`ensure_pkg_resources_stub()`](sealm.py:41)
Tạo stub `pkg_resources` để tương thích với source clone trong [`ldplayer-auto/emulator/__init__.py`](ldplayer-auto/emulator/__init__.py:1).

Lý do: package clone vẫn gọi `pkg_resources.require(...)`, nên file này tự giả lập version `cloned-local`.

### [`load_module()`](sealm.py:57)
Load module từ path file bằng [`importlib.util.spec_from_file_location()`](sealm.py:65).

### [`load_runtime_modules()`](sealm.py:75)
Nạp:
- package emulator clone từ [`EMULATOR_INIT`](sealm.py:25)
- keys từ [`ldplayer-auto/emulator/keys.py`](ldplayer-auto/emulator/keys.py:1)

### [`create_ldplayer()`](sealm.py:82)
Tạo instance [`LDPlayer`](ldplayer-auto/emulator/__init__.py:13) với đường dẫn hiện tại.

Đây là hàm chuẩn để mọi worker và flow GUI lấy kết nối LDPlayer.

## 4. Nhóm hàm điều khiển emulator

### [`warmup_adb()`](sealm.py:111)
Gọi `adb devices` thông qua controller của LDPlayer để làm nóng ADB trước khi thao tác.

### [`go_home_by_esc()`](sealm.py:116)
Gửi nhiều lần [`KEYCODE_ESCAPE`](ldplayer-auto/emulator/keys.py:112) liên tiếp để back ra khỏi nhiều lớp UI game.

Bản hiện tại không chỉ gửi 2 lần mà gửi liên tiếp 4 lần có delay ngắn, nên mạnh tay hơn bản cũ.

### [`select_channel()`](sealm.py:127)
Tap nút mở chọn channel thường.

### [`go_home()`](sealm.py:131)
Tap home theo UI game, không phải Android Home.

### [`go_map_5x()`](sealm.py:137)
Flow cố định để đưa nhân vật về map farm 5x:
1. back ra ngoài bằng [`go_home_by_esc()`](sealm.py:116)
2. tap theo chuỗi tọa độ cố định
3. chờ loading bằng [`wait_loading()`](sealm.py:468)
4. bật auto bằng [`enable_auto()`](sealm.py:409)

Trả về dict chứa `loading`, `auto`, `status`.

### [`dismantle_items()`](sealm.py:163)
Flow phân rã đồ theo chuỗi tap hardcode.

Sau khi phân rã, gọi lại [`go_home_by_esc()`](sealm.py:116) và dừng ở trạng thái gần home.

### [`go_to_boss()`](sealm.py:189)
Mở giao diện boss world, chọn boss theo `boss_number` 1..4, rồi xác nhận đi đến boss.

## 5. Logic chọn channel boss

### [`select_channel_boss()`](sealm.py:222)
Đây là hàm có nhiều rule nghiệp vụ nhất trong file hiện tại.

Comment ngay phía trên hàm đã mô tả flow ngắn gọn. Tóm tắt chuẩn hiện tại:

1. mở danh sách channel boss
2. thử 2 lượt scroll:
   - lượt 1 kéo xuống
   - lượt 2 kéo ngược lên
3. ở mỗi lượt:
   - chụp màn hình
   - tìm icon boss theo template tương ứng boss_number
   - nếu thấy icon thì click icon đầu tiên
   - chờ 1 giây
   - chụp lại màn hình
   - nếu không còn icon boss nữa thì xem là vào channel thành công
4. nếu sau click đầu tiên vẫn còn icon boss thì coi như channel bị full
5. nếu trong danh sách lần đó có icon thứ 2 thì click icon thứ 2
6. nếu không có icon thứ 2 thì chuyển sang lượt scroll tiếp theo
7. nếu hết cả 2 lượt vẫn không chọn được thì skip

Một số `reason` đáng chú ý:
- `invalid_boss_number`
- `capture_failed_scroll_X`
- `capture_failed_after_click_scroll_X`
- `clicked_first_match_scroll_X_success`
- `clicked_second_match_scroll_X`
- `icon_not_found_skip_click`

Lưu ý: hiện tại sau khi click icon thứ 2, hàm return luôn thành công, chưa có bước verify lại sau 1 giây cho icon thứ 2.

## 6. Nhóm hàm xử lý ảnh

### [`load_template()`](sealm.py:314)
Đọc template ảnh bằng `cv2.imread`.

### [`decode_screen()`](sealm.py:321)
Decode screenshot bytes thành ảnh OpenCV.

### [`crop_region()`](sealm.py:328)
Crop vùng ảnh nếu có `region`.

### [`match_score()`](sealm.py:343)
Trả về score match template bằng `cv2.TM_CCOEFF_NORMED`.

Nếu template lớn hơn ảnh nguồn thì trả `-1.0`.

### [`find_template_positions()`](sealm.py:354)
Tìm tất cả vị trí match có score >= `threshold`, trả về danh sách tọa độ center `(x, y)`.

Hàm này là core cho [`select_channel_boss()`](sealm.py:222).

## 7. Nhóm nhận diện trạng thái game

### [`detect_auto_state()`](sealm.py:372)
So khớp ảnh hiện tại với:
- [`AUTO_TEMPLATE`](sealm.py:27)
- [`NOT_AUTO_TEMPLATE`](sealm.py:28)

Rule hiện tại:
- nếu cả 2 score đều `< 0` thì ép `state = "not_auto"`
- ngược lại, chọn state có score cao hơn

### [`enable_auto()`](sealm.py:409)
Nếu state hiện tại là `not_auto` thì tap nút auto.

### [`map_name_from_template_path()`](sealm.py:419)
Chuyển tên file `map_*.png` thành tên logic in hoa.

### [`detect_current_map()`](sealm.py:426)
Duyệt toàn bộ `map_*.png` trong [`images`](images), lấy score cao nhất, nếu qua threshold thì xem đó là map hiện tại.

## 8. Nhóm hàm chờ theo template

### [`wait_loading()`](sealm.py:468)
Chờ loading xong bằng cách polling screenshot và match với [`DONE_LOADING_TEMPLATE`](sealm.py:31).

### [`wait_boss_done()`](sealm.py:506)
Chờ boss kết thúc bằng template [`BOSS_DONE_TEMPLATE`](sealm.py:32).

## 9. Flow boss world và farm loop

### [`active_boss_world()`](sealm.py:542)
Flow boss world theo thứ tự boss 1 → 4:
1. back ra ngoài
2. về home và chờ loading
3. có [`time.sleep(50)`](sealm.py:555) sau khi về home
4. với từng boss:
   - đi đến boss qua [`go_to_boss()`](sealm.py:189)
   - chờ loading
   - chọn channel bằng [`select_channel_boss()`](sealm.py:222)
   - nếu skip thì ghi kết quả rồi sang boss tiếp theo
   - nếu chọn được thì chờ 5 giây
   - back ra
   - bật auto
   - chờ boss done theo timeout riêng từng boss
   - back ra lại

Timeout boss hiện tại:
- boss 1: 2 phút
- boss 2: 5 phút
- boss 3: 7 phút
- boss 4: 10 phút

### [`should_run_boss_world()`](sealm.py:597)
Trigger boss world vào các mốc phút chính xác:
- 09:59
- 14:59
- 18:59
- 21:59

### [`infinite_farm_loop()`](sealm.py:601)
Loop farm chính:
1. đầu mỗi vòng gọi [`go_home_by_esc()`](sealm.py:116)
2. kiểm tra có đến giờ boss world chưa
3. nếu đến giờ thì chạy [`active_boss_world()`](sealm.py:542), sau đó quay lại [`go_map_5x()`](sealm.py:137)
4. nếu chưa đến giờ boss thì kiểm tra auto bằng [`detect_auto_state()`](sealm.py:372)
5. nếu không auto thì quay lại map 5x
6. mỗi 20 phút chạy [`dismantle_items()`](sealm.py:163)
7. ngủ theo `loop_interval`

## 10. Worker multiprocessing

### [`QueueWriter`](sealm.py:88)
Adapter để redirect [`sys.stdout`](sealm.py:6) và [`sys.stderr`](sealm.py:7) vào [`multiprocessing.Queue`](sealm.py:89).

Dùng cho live log GUI, không lưu file.

### [`run_emulator_worker()`](sealm.py:659)
Worker cho nút Run:
- tạo LDPlayer
- lấy emulator theo `emulator_index`
- start emulator nếu cần
- warmup adb
- chạy [`infinite_farm_loop()`](sealm.py:601)

### [`run_boss_worker()`](sealm.py:681)
Worker cho nút Boss:
- setup tương tự worker thường
- nhưng chỉ chạy [`active_boss_world()`](sealm.py:542)

## 11. GUI quản lý LDPlayer

### [`get_running_emulators()`](sealm.py:635)
Lấy danh sách emulator đang chạy dựa trên:
- [`LDPlayer.list_running()`](ldplayer-auto/emulator/__init__.py:92)
- [`ld.emulators`](ldplayer-auto/emulator/__init__.py:30)

### [`LDPlayerManagerApp`](sealm.py:703)
Đây là GUI chính bằng `tkinter`.

#### Layout hiện tại
Form nhỏ gọn:
- geometry: [`"620x360"`](sealm.py:707)
- minsize: [`(560, 300)`](sealm.py:708)

Bảng hiển thị 5 cột:
- `Name`
- `Status`
- `Action`
- `Boss`
- `Log`

#### Nút theo từng cửa sổ emulator
Mỗi dòng có 3 nút chính:
- [`Run/Stop`](sealm.py:829): chạy hoặc kill [`run_emulator_worker()`](sealm.py:659)
- [`Boss/Stop`](sealm.py:836): chạy hoặc kill [`run_boss_worker()`](sealm.py:681)
- [`Log`](sealm.py:843): mở cửa sổ live log

#### Trạng thái process
GUI giữ riêng:
- process farm thường trong [`self.processes`](sealm.py:709)
- process boss trong [`self.boss_processes`](sealm.py:710)
- queue log trong [`self.log_queues`](sealm.py:711)

#### Live log
- cửa sổ log mở bằng [`open_log_window()`](sealm.py:856)
- text widget append bằng [`append_log()`](sealm.py:884)
- queue được đọc định kỳ bằng [`drain_log_queues()`](sealm.py:967)
- log là live only, không ghi file

#### Stop behavior
Cả [`stop_emulator()`](sealm.py:925) và [`stop_boss()`](sealm.py:946) đều dùng `process.kill()` để dừng ngay, không chờ hết chu trình.

#### Polling và dọn tài nguyên
- [`poll_processes()`](sealm.py:981) dọn process chết và queue tương ứng
- [`on_close()`](sealm.py:1016) kill toàn bộ process còn sống, đóng queue và cửa sổ log

## 12. Entry point hiện tại

### [`main()`](sealm.py:1051)
Entry point chỉ làm 4 việc:
1. gọi `multiprocessing.freeze_support()`
2. in thông tin module/path/version
3. tạo [`LDPlayerManagerApp`](sealm.py:703)
4. chạy [`LDPlayerManagerApp.run()`](sealm.py:1047)

Không còn flow `ld.emulators[0]` trực tiếp như bản cũ.

## 13. Những chỗ dễ gây hiểu nhầm cho phiên sau

### [`messagebox`](sealm.py:12)
Hiện đang import nhưng chưa thấy dùng thực tế. Có thể xóa nếu muốn dọn code.

### Log live chỉ là log runtime
Không có log file, không có đọc lịch sử cũ. Nếu mở cửa sổ log muộn, chỉ thấy phần log được push kể từ khi queue còn dữ liệu và cửa sổ đang mở.

### Run và Boss là 2 process riêng
Một emulator có thể có:
- process farm thường
- process boss

GUI hiện có state riêng cho cả hai. Khi sửa logic start/stop phải cẩn thận không làm hỏng [`has_active_process()`](sealm.py:754).

### [`select_channel_boss()`](sealm.py:222) là hàm dễ thay đổi nhất
Nếu người dùng tiếp tục chỉnh rule chọn channel boss, cần đọc cả comment phía trên hàm và logic `reason` return trước khi sửa.

### [`active_boss_world()`](sealm.py:542) đang có [`time.sleep(50)`](sealm.py:555)
Đây là thay đổi nghiệp vụ đáng chú ý. Đừng xóa nếu chưa xác nhận lại với user.

### [`infinite_farm_loop()`](sealm.py:601) hiện luôn back trước mỗi vòng
Dòng [`go_home_by_esc(emulator, keys_module)`](sealm.py:606) đang chạy ở đầu mỗi iteration. Đây là thay đổi hành vi quan trọng so với các phiên trước.

## 14. Checklist nhanh cho agent ở phiên sau

Nếu cần sửa file này, ưu tiên xác định user đang muốn chỉnh nhóm nào:

- điều khiển UI và tọa độ hardcode → xem các hàm tap/drag đầu file, đặc biệt [`go_map_5x()`](sealm.py:137), [`dismantle_items()`](sealm.py:163), [`go_to_boss()`](sealm.py:189), [`select_channel_boss()`](sealm.py:222)
- nhận diện ảnh → xem [`match_score()`](sealm.py:343), [`find_template_positions()`](sealm.py:354), [`detect_auto_state()`](sealm.py:372)
- flow farm/boss → xem [`active_boss_world()`](sealm.py:542), [`infinite_farm_loop()`](sealm.py:601)
- GUI đa cửa sổ → xem [`LDPlayerManagerApp`](sealm.py:703)
- live log / multiprocessing → xem [`QueueWriter`](sealm.py:88), [`run_emulator_worker()`](sealm.py:659), [`run_boss_worker()`](sealm.py:681)

## 15. Tóm tắt cực ngắn

- file chính hiện tại là GUI manager cho nhiều LDPlayer: [`LDPlayerManagerApp`](sealm.py:703)
- hardcode tọa độ đang theo `1280x720`
- có 2 worker độc lập: farm thường [`run_emulator_worker()`](sealm.py:659) và boss [`run_boss_worker()`](sealm.py:681)
- stop dùng `kill` ngay, không chờ xong việc
- live log dùng queue, không lưu file
- logic chọn channel boss nằm ở [`select_channel_boss()`](sealm.py:222) và đang có rule scroll xuống → scroll lên, click icon đầu, verify sau 1 giây, fallback icon thứ 2
- entry point hiện tại là GUI trong [`main()`](sealm.py:1051)
