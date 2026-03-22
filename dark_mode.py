import ctypes
import ctypes.wintypes as wintypes
import time
import sys
import threading

# Require keyboard module
try:
    import keyboard
except ImportError:
    print("The 'keyboard' module is required. Install it using 'pip install keyboard'.", file=sys.stderr)
    sys.exit(1)

# Windows API Types
HWND = wintypes.HWND
BOOL = wintypes.BOOL
DWORD = wintypes.DWORD
LONG = wintypes.LONG
LPCWSTR = wintypes.LPCWSTR
UINT = wintypes.UINT
WPARAM = wintypes.WPARAM
LPARAM = wintypes.LPARAM

# Constants
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_POPUP = 0x80000000
WS_VISIBLE = 0x10000000
WS_CHILD = 0x40000000

LWA_ALPHA = 0x00000002

MW_FILTERMODE_INCLUDE = 0
MW_FILTERMODE_EXCLUDE = 1

WC_MAGNIFIER = "Magnifier"

# Load DLLs
try:
    user32 = ctypes.windll.user32
    magapi = ctypes.windll.Magnification
    kernel32 = ctypes.windll.kernel32
except AttributeError:
    print("Error: This script must be run on Windows.", file=sys.stderr)
    sys.exit(1)

# Definitions from Magnification API
class MAGCOLOREFFECT(ctypes.Structure):
    _fields_ = [("transform", ctypes.c_float * 25)]

class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long)]

# Function Prototypes
magapi.MagInitialize.restype = BOOL
magapi.MagInitialize.argtypes = []

magapi.MagUninitialize.restype = BOOL
magapi.MagUninitialize.argtypes = []

magapi.MagSetWindowFilterList.restype = BOOL
magapi.MagSetWindowFilterList.argtypes = [HWND, DWORD, ctypes.c_int, ctypes.POINTER(HWND)]

magapi.MagSetColorEffect.restype = BOOL
magapi.MagSetColorEffect.argtypes = [HWND, ctypes.POINTER(MAGCOLOREFFECT)]

magapi.MagSetWindowSource.restype = BOOL
magapi.MagSetWindowSource.argtypes = [HWND, RECT]

user32.GetForegroundWindow.restype = HWND
user32.GetForegroundWindow.argtypes = []

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [HWND]

user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [HWND, wintypes.LPWSTR, ctypes.c_int]

user32.CreateWindowExW.restype = HWND
user32.CreateWindowExW.argtypes = [DWORD, LPCWSTR, LPCWSTR, DWORD, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, HWND, HWND, wintypes.HINSTANCE, wintypes.LPVOID]

user32.SetLayeredWindowAttributes.restype = BOOL
user32.SetLayeredWindowAttributes.argtypes = [HWND, DWORD, ctypes.c_byte, DWORD]

user32.SetWindowPos.restype = BOOL
user32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, UINT]

user32.GetWindowRect.restype = BOOL
user32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(RECT)]

user32.IsWindow.restype = BOOL
user32.IsWindow.argtypes = [HWND]

user32.DestroyWindow.restype = BOOL
user32.DestroyWindow.argtypes = [HWND]

user32.PeekMessageW.restype = BOOL
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), HWND, UINT, UINT, UINT]

user32.TranslateMessage.restype = BOOL
user32.TranslateMessage.argtypes = [ctypes.POINTER(wintypes.MSG)]

user32.DispatchMessageW.restype = wintypes.LRESULT
user32.DispatchMessageW.argtypes = [ctypes.POINTER(wintypes.MSG)]

user32.GetWindow.restype = HWND
user32.GetWindow.argtypes = [HWND, UINT]

PM_REMOVE = 0x0001
HWND_TOP = ctypes.cast(0, HWND)
SWP_NOACTIVATE = 0x0010
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_SHOWWINDOW = 0x0040
SWP_HIDEWINDOW = 0x0080
GW_HWNDPREV = 3

INVERT_MATRIX = (ctypes.c_float * 25)(
    -1.0,  0.0,  0.0,  0.0,  0.0,
     0.0, -1.0,  0.0,  0.0,  0.0,
     0.0,  0.0, -1.0,  0.0,  0.0,
     0.0,  0.0,  0.0,  1.0,  0.0,
     1.0,  1.0,  1.0,  0.0,  1.0
)

class MagnifierOverlay:
    """Manages a single magnifier overlay for a specific target window."""
    def __init__(self, target_hwnd):
        self.target_hwnd = target_hwnd
        self.host_hwnd = None
        self.magnifier_hwnd = None

        self._create_host_window()
        self._create_magnifier_control()
        self._setup_inversion_effect()

    def _create_host_window(self):
        host_class = "Static"
        ex_style = WS_EX_LAYERED | WS_EX_TRANSPARENT | WS_EX_TOOLWINDOW
        style = WS_POPUP | WS_VISIBLE

        h_inst = kernel32.GetModuleHandleW(None)

        self.host_hwnd = user32.CreateWindowExW(
            ex_style,
            host_class,
            "DarkModeAnyApp_Host",
            style,
            0, 0, 0, 0,
            None, None, h_inst, None
        )

        if self.host_hwnd:
            user32.SetLayeredWindowAttributes(self.host_hwnd, 0, 255, LWA_ALPHA)
            user32.SetWindowPos(self.host_hwnd, HWND_TOP, 0, 0, 0, 0, SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE | SWP_HIDEWINDOW)

    def _create_magnifier_control(self):
        style = WS_CHILD | WS_VISIBLE
        h_inst = kernel32.GetModuleHandleW(None)

        self.magnifier_hwnd = user32.CreateWindowExW(
            0,
            WC_MAGNIFIER,
            "MagnifierControl",
            style,
            0, 0, 0, 0,
            self.host_hwnd, None, h_inst, None
        )

    def _setup_inversion_effect(self):
        if not self.magnifier_hwnd:
            return

        effect = MAGCOLOREFFECT()
        ctypes.memmove(ctypes.byref(effect.transform), INVERT_MATRIX, ctypes.sizeof(INVERT_MATRIX))
        magapi.MagSetColorEffect(self.magnifier_hwnd, ctypes.byref(effect))

        # Include only the target window
        hwnd_array_type = HWND * 1
        hwnd_array = hwnd_array_type(self.target_hwnd)
        magapi.MagSetWindowFilterList(self.magnifier_hwnd, MW_FILTERMODE_INCLUDE, 1, ctypes.cast(hwnd_array, ctypes.POINTER(HWND)))

    def update_position(self):
        if not self.host_hwnd or not self.magnifier_hwnd:
            return False

        if not user32.IsWindow(self.target_hwnd):
            return False

        rect = RECT()
        if user32.GetWindowRect(self.target_hwnd, ctypes.byref(rect)):
            w = rect.right - rect.left
            h = rect.bottom - rect.top

            # Position host over target window in the Z-order
            # Get the window just above our target window
            hwnd_insert_after = user32.GetWindow(self.target_hwnd, GW_HWNDPREV)
            if not hwnd_insert_after:
                hwnd_insert_after = HWND_TOP

            user32.SetWindowPos(self.host_hwnd, hwnd_insert_after, rect.left, rect.top, w, h, SWP_SHOWWINDOW | SWP_NOACTIVATE)

            # Resize magnifier
            user32.SetWindowPos(self.magnifier_hwnd, HWND_TOP, 0, 0, w, h, SWP_NOACTIVATE)

            # Update source
            magapi.MagSetWindowSource(self.magnifier_hwnd, rect)
            return True

        return False

    def destroy(self):
        if self.magnifier_hwnd:
            user32.DestroyWindow(self.magnifier_hwnd)
        if self.host_hwnd:
            user32.DestroyWindow(self.host_hwnd)

class InversionApp:
    def __init__(self):
        self.overlays = {} # target_hwnd -> MagnifierOverlay
        self.running = True
        self.pending_toggles = set()
        self.lock = threading.Lock()

        if not magapi.MagInitialize():
            print("Failed to initialize Magnification API.", file=sys.stderr)
            sys.exit(1)

        print("Magnification API Initialized.")

    def get_window_title(self, hwnd):
        length = user32.GetWindowTextLengthW(hwnd)
        if length == 0:
            return "<Unknown>"
        buff = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, buff, length + 1)
        return buff.value

    def toggle_active_window(self):
        # Called from keyboard's background thread
        hwnd = user32.GetForegroundWindow()

        if not hwnd:
            return

        # Ignore our own overlays to prevent recursive inversion
        # Note: self.overlays read access from another thread could technically race with writes,
        # but the lock protects the handoff

        with self.lock:
            # We don't check for overlays here fully because we just want to enqueue the HWND
            if hwnd in self.pending_toggles:
                self.pending_toggles.remove(hwnd)
            else:
                self.pending_toggles.add(hwnd)

    def _process_pending_toggles(self):
        # Called from main thread
        toggles = []
        with self.lock:
            toggles = list(self.pending_toggles)
            self.pending_toggles.clear()

        for hwnd in toggles:
            # Check if it's an overlay we own
            is_overlay = False
            for overlay in self.overlays.values():
                if hwnd == overlay.host_hwnd or hwnd == overlay.magnifier_hwnd:
                    is_overlay = True
                    break

            if is_overlay:
                continue

            title = self.get_window_title(hwnd)

            if hwnd in self.overlays:
                overlay = self.overlays.pop(hwnd)
                overlay.destroy()
                print(f"[-] Restored window: {title} (HWND: {hwnd})")
            else:
                overlay = MagnifierOverlay(hwnd)
                self.overlays[hwnd] = overlay
                print(f"[+] Inverted window: {title} (HWND: {hwnd})")

    def _cleanup_stale_handles(self):
        invalid = []
        for hwnd, overlay in self.overlays.items():
            if not user32.IsWindow(hwnd):
                invalid.append(hwnd)

        for hwnd in invalid:
            overlay = self.overlays.pop(hwnd)
            overlay.destroy()
            print(f"[!] Removed stale window handle: {hwnd}")

    def _update_magnifier_positions(self):
        self._cleanup_stale_handles()

        for overlay in self.overlays.values():
            overlay.update_position()

    def _pump_messages(self):
        msg = wintypes.MSG()
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

    def run(self):
        print("==================================================")
        print("  Dark Mode Any App (Python Clone) is running.    ")
        print("==================================================")
        print("-> Press Ctrl+Alt+Q to toggle inversion for the active window.")
        print("-> Press Ctrl+C in this console to exit.\n")

        keyboard.add_hotkey('ctrl+alt+q', self.toggle_active_window)

        try:
            while self.running:
                self._pump_messages()
                self._process_pending_toggles()
                self._update_magnifier_positions()
                time.sleep(0.01)  # 10ms loop ~100FPS max update rate
        except KeyboardInterrupt:
            self.running = False
        finally:
            self.cleanup()

    def cleanup(self):
        print("\nCleaning up and restoring colors...")
        for overlay in self.overlays.values():
            overlay.destroy()
        self.overlays.clear()

        magapi.MagUninitialize()
        sys.exit(0)

if __name__ == '__main__':
    app = InversionApp()
    app.run()
