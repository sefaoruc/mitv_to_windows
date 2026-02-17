import ctypes
from ctypes import wintypes
import sys

# Windows Sabitleri
WM_INPUT = 0x00FF
RID_INPUT = 0x10000003
RIDEV_INPUTSINK = 0x00000100

# C Yapıları (Windows API için)
class RAWINPUTHEADER(ctypes.Structure):
    _fields_ = [("dwType", wintypes.DWORD), ("dwSize", wintypes.DWORD),
                ("hDevice", wintypes.HANDLE), ("wParam", wintypes.WPARAM)]

class RAWKEYBOARD(ctypes.Structure):
    _fields_ = [("MakeCode", wintypes.USHORT), ("Flags", wintypes.USHORT),
                ("Reserved", wintypes.USHORT), ("VKey", wintypes.USHORT),
                ("Message", wintypes.UINT), ("ExtraInformation", wintypes.ULONG)]

class RAWHID(ctypes.Structure):
    _fields_ = [("dwSizeHid", wintypes.DWORD), ("dwCount", wintypes.DWORD),
                ("bRawData", ctypes.c_byte * 1)]

class RAWINPUT(ctypes.Structure):
    class _U(ctypes.Union):
        _fields_ = [("keyboard", RAWKEYBOARD), ("hid", RAWHID)]
    _fields_ = [("header", RAWINPUTHEADER), ("data", _U)]

class RAWINPUTDEVICE(ctypes.Structure):
    _fields_ = [("usUsagePage", wintypes.USHORT), ("usUsage", wintypes.USHORT),
                ("dwFlags", wintypes.DWORD), ("hwndTarget", wintypes.HANDLE)]

# Klavye simülasyonu için Windows fonksiyonu
def send_key(code):
    ctypes.windll.user32.keybd_event(code, 0, 0, 0) # Bas
    ctypes.windll.user32.keybd_event(code, 0, 2, 0) # Bırak

def decode_input(lparam):
    size = wintypes.DWORD()
    ctypes.windll.user32.GetRawInputData(ctypes.cast(lparam, wintypes.HANDLE), RID_INPUT, None, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER))
    buf = ctypes.create_string_buffer(size.value)
    if ctypes.windll.user32.GetRawInputData(ctypes.cast(lparam, wintypes.HANDLE), RID_INPUT, buf, ctypes.byref(size), ctypes.sizeof(RAWINPUTHEADER)):
        raw = ctypes.cast(buf, ctypes.POINTER(RAWINPUT)).contents
        
        # 1. Durum: Standart Klavye/Medya Tuşları
        if raw.header.dwType == 1: 
            vkey = raw.data.keyboard.VKey
            flags = raw.data.keyboard.Flags
            if not (flags & 0x01): # Sadece basılma anı
                # Log ve Dönüştürme
                if vkey == 0xA6: # Geri Tuşu
                    print("Kumanda: GERİ -> ESC Gönderildi")
                    send_key(0x1B) # ESC
                elif vkey == 0x4D: # 'M' harfi (Menü)
                    print("Kumanda: MENÜ -> Windows Menü")
                    send_key(0x5B) # Windows Tuşu
                elif vkey in [0x25, 0x26, 0x27, 0x28]:
                    mapping = {0x26: "YUKARI", 0x28: "AŞAĞI", 0x25: "SOL", 0x27: "SAĞ"}
                    print(f"Kumanda: {mapping[vkey]}")

        # 2. Durum: HID (Yön Tuşları Gamepad modundaysa buraya düşer)
        elif raw.header.dwType == 2:
            # Ham veriyi oku (Burası cihazın yolladığı gizli paketlerdir)
            hid_data = ctypes.cast(ctypes.addressof(raw.data.hid.bRawData), ctypes.POINTER(ctypes.c_ubyte * raw.data.hid.dwSizeHid)).contents
            data_list = list(hid_data)
            print(f"Ham Sinyal Yakalandı: {data_list}")
            
            # Mi Stick OK/Navigasyon haritalama (Genelde 3. ve 4. byte)
            # Eğer bu rakamlar sende farklıysa terminaldeki çıktıya göre güncelleyebiliriz
            if len(data_list) > 2:
                if data_list[1] == 1: send_key(0x26) # Yukarı
                elif data_list[1] == 2: send_key(0x28) # Aşağı
                elif data_list[2] == 1: send_key(0x0D) # OK (Enter)

def main():
    print("--- Mi TV Stick Gelişmiş Sürücü (Saf Python 3.14) ---")
    print("Kumanda sinyalleri taranıyor... (Kapatmak için pencereyi kapatın)")

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_INPUT:
            decode_input(lparam)
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    # Pencere sınıfı oluştur
    hinst = ctypes.windll.kernel32.GetModuleHandleW(None)
    WNDPROC = ctypes.WINFUNCTYPE(ctypes.c_longlong, wintypes.HANDLE, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    
    class WNDCLASS(ctypes.Structure):
        _fields_ = [("style", wintypes.UINT), ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int), ("cbWndExtra", ctypes.c_int),
                    ("hInstance", wintypes.HANDLE), ("hIcon", wintypes.HANDLE),
                    ("hCursor", wintypes.HANDLE), ("hbrBackground", wintypes.HANDLE),
                    ("lpszMenuName", wintypes.LPCWSTR), ("lpszClassName", wintypes.LPCWSTR)]

    wc = WNDCLASS(0, WNDPROC(wnd_proc), 0, 0, hinst, 0, 0, 0, 0, "MiRemote")
    ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))
    hwnd = ctypes.windll.user32.CreateWindowExW(0, "MiRemote", None, 0, 0, 0, 0, 0, 0, 0, hinst, 0)

    # Cihazları kaydet: 
    # 0x01, 0x06 -> Klavye
    # 0x01, 0x05 -> Gamepad
    # 0x0C, 0x01 -> Consumer Control (Medya tuşları)
    devices = (RAWINPUTDEVICE * 3)(
        RAWINPUTDEVICE(0x01, 0x06, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x01, 0x05, RIDEV_INPUTSINK, hwnd),
        RAWINPUTDEVICE(0x0C, 0x01, RIDEV_INPUTSINK, hwnd)
    )
    ctypes.windll.user32.RegisterRawInputDevices(ctypes.byref(devices), 3, ctypes.sizeof(RAWINPUTDEVICE))

    msg = wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), 0, 0, 0) != 0:
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))

if __name__ == "__main__":
    main()