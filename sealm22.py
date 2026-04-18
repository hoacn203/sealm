import time
import win32gui
import win32api
import win32con
import interception
import autoit

WINDOW_TITLE = "SealM on CROSS"

# Khởi tạo interception (chỉ chuột)
interception.auto_capture_devices(keyboard=False, mouse=True)

RA_DO_CLICKS = [
    (378,  101),   # Bước 1
    (1177, 708),   # Bước 2
    (728,  566),   # Bước 3
    (439,  723),
    (726,  523),
    (378,  101),
    (378,  101)
]


def find_window_by_title(partial_title):
    result = []

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            # Chỉ lấy đúng cửa sổ game gốc hoặc cửa sổ đã đổi tên thành SealM-1, SealM-2...
            if "SealM" in title:
                result.append((hwnd, title))

    win32gui.EnumWindows(enum_handler, None)
    return result


def click_at(hwnd, x, y, delay_after=1.0):
    """Click qua thư viện interception như bản cũ"""
    left, top, _, _ = win32gui.GetWindowRect(hwnd)
    abs_x = left + x
    abs_y = top + y
    
    interception.move_to(abs_x, abs_y)
    time.sleep(0.1)
    interception.mouse_down("left")
    time.sleep(0.05)
    interception.mouse_up("left")
    time.sleep(delay_after)
    print(f"  🖱️ Click interception ({abs_x}, {abs_y})")


def ra_do(hwnd):
    print("\n▶ Bắt đầu rã đồ...")
    for i, (cx, cy) in enumerate(RA_DO_CLICKS, 1):
        print(f"  [{i}/{len(RA_DO_CLICKS)}] client ({cx},{cy})")
        click_at(hwnd, cx, cy)
    print("✅ Hoàn thành rã đồ!")


def main(hwnd, name):
    print(f"\n═══ Chạy: '{name}' (hwnd={hwnd}) ═══")

    
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE) # Cứ nhấc lên khỏi Taskbar trước
    
    # Kích hoạt cửa sổ nhanh, mạnh và dứt khoát bằng AutoIt
    try:
        handle_str = f"[HANDLE:{hwnd:016x}]"
        autoit.win_activate(handle_str)
        autoit.win_wait_active(handle_str, 3) # Đợi tối đa 3 giây để nó nổi lên hoàn toàn
    except Exception as e:
        print(f"  [AutoIt] Warning: {e}")
            
    print("  ⏳ Chờ 1 giây sau khi Active cửa sổ...")
    time.sleep(1)

    # Lấy vị trí cửa sổ trên màn hình
    rect = win32gui.GetWindowRect(hwnd)
    print(f"  Cửa sổ tại: left={rect[0]}, top={rect[1]}")

    # Thực hiện rã đồ
    ra_do(hwnd)


def setup_windows():
    """Tìm tất cả cửa sổ SealM, đổi tên và gán cấu trúc."""
    found = []
    for hwnd, title in find_window_by_title(""):
        if hwnd not in [h for h, _ in found]:
            found.append((hwnd, title))

    if not found:
        print("Không tìm thấy cửa sổ game!")
        return []

    # Sắp xếp theo vị trí x (trái → phải) để thứ tự ổn định
    found.sort(key=lambda w: win32gui.GetWindowRect(w[0])[0])

    chars = []
    for i, (hwnd, title) in enumerate(found):
        new_name = f"SealM-{i+1}"
        win32gui.SetWindowText(hwnd, new_name)
        rect = win32gui.GetWindowRect(hwnd)
        print(f"  Cửa sổ {i+1}: '{title}' → '{new_name}' (pos={rect[0]},{rect[1]})")
        chars.append({"hwnd": hwnd, "name": new_name})

    return chars


import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import threading
import sys
import os

class SealMGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto HOADZ")
        self.root.geometry("450x550")
        self.root.configure(padx=15, pady=15)

        self.process = None
        self.windows_data = []

        # -- TIÊU ĐỀ --
        lbl_title = tk.Label(root, text="QUẢN LÝ CỬA SỔ SEALM", font=("Arial", 14, "bold"))
        lbl_title.pack(pady=(0, 10))

        # -- DANH SÁCH --
        frame_list = tk.Frame(root)
        frame_list.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame_list)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(frame_list, selectmode=tk.MULTIPLE, font=("Arial", 11), height=10, yscrollcommand=scrollbar.set)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

        # -- NÚT CHỌN TẤT CẢ / BỎ CHỌN --
        frame_sel = tk.Frame(root)
        frame_sel.pack(fill=tk.X, pady=5)
        tk.Button(frame_sel, text="Cập nhật danh sách", command=self.refresh_windows, bg="#e0e0e0").pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(frame_sel, text="Chọn tất cả", command=self.select_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)
        tk.Button(frame_sel, text="Bỏ chọn", command=self.deselect_all).pack(side=tk.LEFT, expand=True, fill=tk.X, padx=2)

        # -- CỤM NÚT ĐIỀU KHIỂN --
        frame_ctrl = tk.LabelFrame(root, text="Điều khiển", padx=10, pady=10)
        frame_ctrl.pack(fill=tk.X, pady=15)

        tk.Button(frame_ctrl, text="🔍 Active Cửa Sổ (Đẩy lên trước)", command=self.activate_selected, bg="#d4edda", height=2).pack(fill=tk.X, pady=(0, 5))
        
        self.btn_run = tk.Button(frame_ctrl, text="▶ Bắt đầu Rã Đồ", command=self.run_bot, bg="#28a745", fg="white", font=("Arial", 11, "bold"), height=2)
        self.btn_run.pack(fill=tk.X, pady=(0, 5))
        
        self.btn_stop = tk.Button(frame_ctrl, text="🛑 Dừng Tất Cả", command=self.stop_bot, bg="#dc3545", fg="white", font=("Arial", 11, "bold"), height=2, state=tk.DISABLED)
        self.btn_stop.pack(fill=tk.X)

        # -- TRẠNG THÁI --
        self.lbl_status = tk.Label(root, text="Trạng thái: Đang chờ...", font=("Arial", 10, "italic"), fg="blue")
        self.lbl_status.pack(pady=10)

        # Nạp dữ liệu lần đầu
        self.refresh_windows()

    def get_selected_names(self):
        selected_indices = self.listbox.curselection()
        if not selected_indices:
            return []
        
        return [self.windows_data[i]["name"] for i in selected_indices]

    def refresh_windows(self):
        self.listbox.delete(0, tk.END)
        self.windows_data = setup_windows()
        
        if not self.windows_data:
            self.listbox.insert(tk.END, "Không tìm thấy cửa sổ SealM nào...")
            self.lbl_status.config(text="Status: Không tìm thấy game.")
            self.windows_data = [] # clear memory
        else:
            for w in self.windows_data:
                self.listbox.insert(tk.END, f"{w['name']} (hwnd:{w['hwnd']})")
            self.lbl_status.config(text=f"Đã cập nhật {len(self.windows_data)} cửa sổ.")

    def select_all(self):
        self.listbox.select_set(0, tk.END)

    def deselect_all(self):
        self.listbox.select_clear(0, tk.END)

    def activate_selected(self):
        selected = self.get_selected_names()
        if not selected:
            messagebox.showwarning("Chưa chọn", "Vui lòng chọn ít nhất 1 cửa sổ trong danh sách để Active!")
            return
            
        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Chạy subprocess lệnh activate
        subprocess.Popen([python_exe, script_path, "activate"] + selected)
        self.lbl_status.config(text=f"Đã Active: {', '.join(selected)}")

    def run_bot(self):
        # Bắt buộc phải chọn tất cả khi Rã đồ như yêu cầu
        self.select_all()
        selected = self.get_selected_names()
        
        if not selected:
            messagebox.showwarning("Trống", "Không có cửa sổ nào đang mở để Rã Đồ!")
            return

        if self.process is not None and self.process.poll() is None:
            messagebox.showinfo("Đang chạy", "Bot hiện vẫn đang chạy rồi!")
            return

        self.lbl_status.config(text=f"Trạng thái: Đang Rã Đồ cho {len(selected)} acc...", fg="green")
        self.btn_run.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)

        python_exe = sys.executable
        script_path = os.path.abspath(__file__)
        
        # Để chạy ngầm trên tkinter mà không bị đứng, dùng Popen là hoàn hảo
        self.process = subprocess.Popen([python_exe, script_path, "run"] + selected)
        threading.Thread(target=self.monitor_process, daemon=True).start()

    def stop_bot(self):
        if self.process is not None:
            self.process.terminate()
            self.process = None
        
        self.lbl_status.config(text="Trạng thái: Đã DỪNG thao tác!", fg="red")
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

    def monitor_process(self):
        if self.process is not None:
            self.process.wait()
            self.root.after(0, self.reset_ui)

    def reset_ui(self):
        self.lbl_status.config(text="Trạng thái: Đang chờ...", fg="blue")
        self.btn_run.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)

if __name__ == "__main__":
    args = sys.argv[1:]
    command = args[0] if args else "gui"
    target_names = args[1:] if len(args) > 1 else []

    if command == "gui":
        root = tk.Tk()
        app = SealMGUI(root)
        root.mainloop()
        sys.exit(0)

    chars = setup_windows()
    if not chars:
        print("Không có cửa sổ nào để chạy!")
        sys.exit(1)

    if command == "activate":
        import autoit
        for c in chars:
            if not target_names or c["name"] in target_names:
                print(f"Bật cửa sổ: {c['name']}")
                win32gui.ShowWindow(c["hwnd"], win32con.SW_RESTORE)
                try:
                    handle_str = f"[HANDLE:{c['hwnd']:016x}]"
                    autoit.win_activate(handle_str)
                except Exception as e:
                    print(f"  [AutoIt] Lỗi Active: {e}")
        sys.exit(0)

    elif command == "run":
        while True:
            try:
                if not chars or any(not win32gui.IsWindow(c["hwnd"]) for c in chars):
                    print("\n--- Setup cửa sổ ---")
                    chars = setup_windows()
                    if not chars:
                        print("Đợi 60s rồi thử lại...")
                        time.sleep(60)
                        continue

                run_chars = chars
                if target_names:
                    run_chars = [c for c in chars if c["name"] in target_names]
                
                if not run_chars:
                    print("Không có cửa sổ nào khớp với yêu cầu!")
                    sys.exit(1)

                for i, char in enumerate(run_chars):
                    if i > 0:
                        print("\n⏳ Đang chuyển sang cửa sổ tiếp theo...")
                    main(char["hwnd"], char["name"])

            except Exception as e:
                print(f"\n[ERROR] {e}")

            print("\nĐợi 10 phút trước lần chạy tiếp...")
            time.sleep(600)
