import ctypes
from ctypes import wintypes
import threading
import pystray
from PIL import Image
import os
import sys
import subprocess

# --- EXE İÇİNDEKİ DOSYALARA ERİŞİM FONKSİYONU ---
def resource_path(relative_path):
    """ EXE derlendiğinde geçici klasördeki dosyalara (ikon vb.) ulaşmayı sağlar """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- WINDOWS API SABİTLERİ ---
WM_INPUT = 0x00FF
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100

class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD), ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]
class RAWHID(ctypes.Structure):
    _fields_ = [("dwSizeHid", wintypes.DWORD), ("dwCount", wintypes.DWORD), ("bRawData", ctypes.c_byte * 1)]
class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT), ("Reserved", wintypes.USHORT), ("VKey", wintypes.USHORT), ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]
class RAWINPUT(ctypes.Structure):
    class _U(ctypes.Union): _fields_ = [("keyboard", RAWKEYBOARD), ("hid", RAWHID)]
    _fields_ = [("header", RAWINPUTHEADER), ("data", _U)]
class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT), ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HANDLE)]

def press(vk):
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)

def press_combo(mod, vk):
    ctypes.windll.user32.keybd_event(mod, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk, 0, 2, 0)
    ctypes.windll.user32.keybd_event(mod, 0, 2, 0)

# --- GARANTİ BİLDİRİM FONKSİYONU ---
def send_notification(title, message):
    """Windows PowerShell kullanarak kütüphanesiz bildirim fırlatır"""
    script = f"Add-Type -AssemblyName System.Windows.Forms; $notify = New-Object System.Windows.Forms.NotifyIcon; $notify.Icon = [System.Drawing.Icon]::ExtractAssociatedIcon((Get-Process -id $pid).Path); $notify.Visible = $true; $notify.ShowBalloonTip(5000, '{title}', '{message}', [System.Windows.Forms.ToolTipIcon]::Info)"
    try:
        subprocess.Popen(["powershell", "-Command", script], creationflags=subprocess.CREATE_NO_WINDOW)
    except: pass

def process_data(lparam):
    size = wintypes.DWORD()
    ctypes.windll.user32.GetRawInputData(ctypes.cast(lparam, wintypes.HANDLE), RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
    buf = ctypes.create_string_buffer(size.value)
    if ctypes.windll.user32.GetRawInputData(ctypes.cast(lparam, wintypes.HANDLE), RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)):
        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        if raw.header.dwType == 2:
            try:
                hid_data = ctypes.cast(ctypes.addressof(raw.data.hid.bRawData), ctypes.POINTER(ctypes.c_ubyte * raw.data.hid.dwSizeHid)).contents
                d = list(hid_data)
                if len(d) < 4: return
                
                # Orijinal Driver Mantığın
                if d[1] == 1: press(0x0D)
                elif d[1] == 2: press(0x26)
                elif d[1] == 4: press(0x28)
                elif d[1] == 8: press(0x25)
                elif d[1] == 16: press(0x27)
                elif d[1] == 32: press_combo(0x5B, 0x4C)
                elif d[1] == 64: press_combo(0x5B, 0x53)
                elif d[1] == 128: press(0xAF)
                elif d[1] == 0:
                    if d[2] == 1: press(0xAE)
                    elif d[2] == 2: press(0x5B)
                    elif d[2] == 4: press_combo(0x12, 0x09)
                    elif d[2] == 32: press_combo(0x5B, 0x45)
                    elif d[2] == 0:
                        if d[3] == 4: press_combo(0x5B, 0x44)
                        elif d[3] == 8: press(0x1B)
            except: pass

def driver_thread():
    hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
    WNDPROC_TYPE = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HANDLE, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    
    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            process_data(lparam)
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    class_name = "MiDriverWindow"
    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC_TYPE), ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int), ("hInstance", wintypes.HANDLE), ("hIcon", wintypes.HANDLE), ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE), ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    wc = WNDCLASS(0, WNDPROC_TYPE(wnd_proc), 0, 0, hinst, 0, 0, 0, 0, class_name)
    ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))
    hwnd = ctypes.windll.user32.CreateWindowExW(0, class_name, "MiDriver", 0, 0, 0, 0, 0, 0, 0, hinst, 0)

    devices = (RAWINPUTDEVICE * 3)(
        RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x01, 0x05, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x0C, 0x01, RIDEV_INPUTSINK, hwnd)
    )
    ctypes.windll.user32.RegisterRawInputDevices(ctypes.byref(devices), 3, ctypes.sizeof(RAWINPUTDEVICE))

    # Başlangıç bildirimi
    send_notification("Mi Stick Driver", "Kumandanız Aktif ve Hazır!")

    msg = wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    # Sürücüyü ayrı thread'de başlat
    t = threading.Thread(target=driver_thread)
    t.daemon = True
    t.start()

    # Tepsi ikonu için logon.ico dosyasını kullan
    try:
        icon_path = resource_path("logon.ico")
        icon_image = Image.open(icon_path)
    except:
        # Eğer ikon bulunamazsa basit bir görsel oluştur (hata vermemesi için)
        icon_image = Image.new('RGB', (64, 64), (30, 30, 30))

    icon = pystray.Icon("MiStick", icon_image, "Mi Stick Kumanda Aktif", menu=pystray.Menu(
        pystray.MenuItem("Kapat", lambda i, item: os._exit(0))
    ))
    icon.run()