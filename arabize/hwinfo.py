"""The PC itself: specifications, live readings (CPU / RAM use, temperatures) and the game's frame rate.

Everything here is read-only and runs in background threads, so the game never waits for it. When a reading is not
available on a machine it is reported as unavailable with the reason, never guessed.

- Specifications: processor, graphics cards, memory, drives, Windows version (registry + psutil, no admin needed).
- CPU temperature: Windows has no standard way to read it. In order: LibreHardwareMonitor or OpenHardwareMonitor if
  one is running (exact package temperature), otherwise the ACPI thermal zone Windows publishes (approximate).
- GPU temperature: LibreHardwareMonitor if running, otherwise nvidia-smi on NVIDIA cards.
- FPS: Intel PresentMon (bundled), the tool game overlays use. Windows lets it watch frames only with administrator
  rights, so without them the readout says so and offers to restart the program as administrator.
"""
from __future__ import annotations

import base64
import collections
import csv
import json
import os
import platform
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from .logs import log
from .platform_utils import IS_WIN, foreground_exe, is_admin

NO_WINDOW = 0x08000000 if IS_WIN else 0


# ------------------------------------------------------------------ specifications
def _reg(path: str, name: str):
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as k:
            return winreg.QueryValueEx(k, name)[0]
    except Exception:
        return None


def cpu_name() -> str:
    if IS_WIN:
        n = _reg(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString")
        if n:
            return " ".join(str(n).split())
    try:
        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or "غير معروف"


def gpus() -> list[dict]:
    """[{"name": "NVIDIA GeForce RTX 4070", "vram_gb": 12.0}] — from the display-adapter registry keys."""
    out: list[dict] = []
    if IS_WIN:
        try:
            import winreg
            base = r"SYSTEM\CurrentControlSet\Control\Class\{4d36e968-e325-11ce-bfc1-08002be10318}"
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, base) as root:
                i = 0
                while True:
                    try:
                        sub = winreg.EnumKey(root, i)
                    except OSError:
                        break
                    i += 1
                    if not sub.isdigit():
                        continue
                    try:
                        with winreg.OpenKey(root, sub) as k:
                            name = winreg.QueryValueEx(k, "DriverDesc")[0]
                            vram = None
                            for vn in ("HardwareInformation.qwMemorySize", "HardwareInformation.MemorySize"):
                                try:
                                    v = winreg.QueryValueEx(k, vn)[0]
                                    v = int.from_bytes(v, "little") if isinstance(v, (bytes, bytearray)) else int(v)
                                    if v > 0:
                                        vram = round(v / 1024 ** 3, 1)
                                        break
                                except OSError:
                                    continue
                    except OSError:
                        continue
                    if name and "basic" not in name.lower() and "remote" not in name.lower() \
                            and not any(g["name"] == name for g in out):
                        out.append({"name": " ".join(str(name).split()), "vram_gb": vram})
        except Exception:
            pass
    else:
        try:
            r = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
            for line in r.stdout.splitlines():
                if "VGA" in line or "3D controller" in line:
                    out.append({"name": line.split(":", 2)[-1].strip(), "vram_gb": None})
        except Exception:
            pass
    return out


def drives() -> list[dict]:
    out = []
    try:
        import psutil
        seen = set()
        for p in psutil.disk_partitions(all=False):
            if p.mountpoint in seen or "cdrom" in (p.opts or "") or not p.fstype:
                continue
            seen.add(p.mountpoint)
            try:
                u = psutil.disk_usage(p.mountpoint)
            except OSError:
                continue
            if u.total < 1024 ** 3:
                continue
            out.append({"mount": p.mountpoint, "fs": p.fstype, "total_gb": round(u.total / 1024 ** 3, 1),
                        "free_gb": round(u.free / 1024 ** 3, 1)})
    except Exception:
        pass
    return out


def windows_version() -> str:
    if IS_WIN:
        name = _reg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductName") or "Windows"
        build = _reg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "CurrentBuild") or ""
        disp = _reg(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "DisplayVersion") or ""
        if build and str(build).isdigit() and int(build) >= 22000:
            name = str(name).replace("Windows 10", "Windows 11")     # Windows 11 still reports "Windows 10" here
        return " ".join(str(x) for x in (name, disp, f"(build {build})" if build else "") if x)
    return f"{platform.system()} {platform.release()}"


def specs() -> dict:
    """Everything the device page shows. Takes well under a second; call it off the UI thread if you can."""
    try:
        import psutil
        cores, threads = psutil.cpu_count(logical=False) or 0, psutil.cpu_count(logical=True) or 0
        freq = psutil.cpu_freq()
        mhz = int(freq.max or freq.current) if freq else None
        ram_gb = round(psutil.virtual_memory().total / 1024 ** 3, 1)
    except Exception:
        cores = threads = 0; mhz = None; ram_gb = None
    return {"os": windows_version(), "cpu": cpu_name(), "cores": cores, "threads": threads, "cpu_mhz": mhz,
            "gpus": gpus(), "ram_gb": ram_gb, "drives": drives()}


def specs_text(s: dict) -> str:
    """Plain-text copy of the specifications (for the "copy" button and bug reports)."""
    lines = [f"النظام: {s['os']}", f"المعالج: {s['cpu']} — {s['cores']} أنوية / {s['threads']} مسار"
             + (f" — حتى {s['cpu_mhz'] / 1000:.2f} GHz" if s.get("cpu_mhz") else "")]
    for g in s["gpus"] or [{"name": "غير معروف", "vram_gb": None}]:
        lines.append(f"كرت الشاشة: {g['name']}" + (f" — {g['vram_gb']:g} GB" if g.get("vram_gb") else ""))
    if s.get("ram_gb"):
        lines.append(f"الذاكرة العشوائية (RAM): {s['ram_gb']:g} GB")
    for d in s["drives"]:
        lines.append(f"التخزين {d['mount']}: {d['total_gb']:g} GB (المتاح {d['free_gb']:g} GB)")
    return "\n".join(lines)


# ------------------------------------------------------------------ temperatures
_PS_LOOP = r"""
$ErrorActionPreference = 'SilentlyContinue'
$nv = (Get-Command nvidia-smi -ErrorAction SilentlyContinue).Source
if (-not $nv -and (Test-Path "$env:WINDIR\System32\nvidia-smi.exe")) { $nv = "$env:WINDIR\System32\nvidia-smi.exe" }
while ($true) {
  $cpu = $null; $src = ''; $gpu = $null; $gload = $null
  foreach ($ns in 'root/LibreHardwareMonitor', 'root/OpenHardwareMonitor') {
    if ($cpu -ne $null) { break }
    $all = Get-CimInstance -Namespace $ns -ClassName Sensor | Where-Object { $_.SensorType -eq 'Temperature' }
    if ($all) {
      $c = $all | Where-Object { $_.Identifier -match 'cpu' -and $_.Name -match 'Package|Tctl|Tdie|CCD|Core \(Tctl' } | Select-Object -First 1
      if (-not $c) { $c = $all | Where-Object { $_.Identifier -match 'cpu' } | Sort-Object Value -Descending | Select-Object -First 1 }
      if ($c) { $cpu = [math]::Round($c.Value, 1); $src = $ns.Split('/')[1] }
      $g = $all | Where-Object { $_.Identifier -match 'gpu' -and $_.Name -match 'Core|GPU' } | Select-Object -First 1
      if ($g) { $gpu = [math]::Round($g.Value, 1) }
    }
  }
  if ($cpu -eq $null) {
    $z = Get-CimInstance Win32_PerfFormattedData_Counters_ThermalZoneInformation | Sort-Object HighPrecisionTemperature -Descending | Select-Object -First 1
    if ($z -and $z.HighPrecisionTemperature -gt 2732) { $cpu = [math]::Round($z.HighPrecisionTemperature / 10 - 273.15, 1); $src = 'acpi' }
  }
  if ($gpu -eq $null -and $nv) {
    $o = & $nv --query-gpu=temperature.gpu,utilization.gpu --format=csv,noheader,nounits 2>$null | Select-Object -First 1
    if ($o) { $p = $o.Split(','); $gpu = [double]$p[0].Trim(); $gload = [double]$p[1].Trim() }
  }
  [Console]::Out.WriteLine((@{cpu = $cpu; src = $src; gpu = $gpu; gload = $gload} | ConvertTo-Json -Compress))
  [Console]::Out.Flush()
  Start-Sleep -Seconds 2
}
"""

TEMP_SOURCES = {"LibreHardwareMonitor": "LibreHardwareMonitor", "OpenHardwareMonitor": "OpenHardwareMonitor",
                "acpi": "تقريبية من حساس اللوحة الأم (ACPI)"}


class Sensors:
    """Live readings, refreshed in the background while someone is looking at them (start/stop).

    data: cpu (% all cores), ram_pct, ram_used_gb, ram_total_gb, cpu_temp (°C or None), cpu_temp_src,
    gpu_temp, gpu_load."""

    def __init__(self):
        self.data: dict = {"cpu": None, "ram_pct": None, "ram_used_gb": None, "ram_total_gb": None,
                           "cpu_temp": None, "cpu_temp_src": "", "gpu_temp": None, "gpu_load": None}
        self._users = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ps: subprocess.Popen | None = None
        self._lock = threading.Lock()
        self.temp_note = ""

    def start(self):
        with self._lock:
            self._users += 1
            if self._thread and self._thread.is_alive():
                return
            self._stop.clear()
            self._thread = threading.Thread(target=self._run, daemon=True, name="sensors")
            self._thread.start()
            if IS_WIN:
                threading.Thread(target=self._temps, daemon=True, name="sensors-temp").start()
            else:
                self.temp_note = self._linux_temp_note()

    def stop(self, force: bool = False):
        with self._lock:
            self._users = 0 if force else max(0, self._users - 1)
            if self._users:
                return
            self._stop.set()
            ps, self._ps = self._ps, None
        if ps:
            try:
                ps.kill()
            except Exception:
                pass

    def _run(self):
        try:
            import psutil
        except Exception:
            return
        psutil.cpu_percent(interval=None)
        while not self._stop.wait(1.0):
            try:
                vm = psutil.virtual_memory()
                self.data.update(cpu=psutil.cpu_percent(interval=None), ram_pct=vm.percent,
                                 ram_used_gb=round((vm.total - vm.available) / 1024 ** 3, 1),
                                 ram_total_gb=round(vm.total / 1024 ** 3, 1))
                if not IS_WIN:
                    self.data["cpu_temp"], self.data["cpu_temp_src"] = self._linux_temp()
            except Exception:
                pass

    @staticmethod
    def _linux_temp():
        try:
            import psutil
            t = psutil.sensors_temperatures()
            for key in ("coretemp", "k10temp", "zenpower", "cpu_thermal", "acpitz"):
                if t.get(key):
                    return round(max(x.current for x in t[key]), 1), key
        except Exception:
            pass
        return None, ""

    def _linux_temp_note(self) -> str:
        return "" if self._linux_temp()[0] is not None else "لا يوجد حساس حرارة يمكن قراءته على هذا الجهاز"

    def _temps(self):  # pragma: no cover - Windows only
        """One PowerShell process for the whole session (not one per reading), printing a JSON line every 2 s."""
        enc = base64.b64encode(_PS_LOOP.encode("utf-16-le")).decode()
        try:
            ps = subprocess.Popen(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                                   "-EncodedCommand", enc], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  stdin=subprocess.DEVNULL, creationflags=NO_WINDOW, text=True, encoding="utf-8",
                                  errors="replace")
        except Exception as e:
            log.info("temperature reader unavailable: %s", e)
            self.temp_note = "تعذّر تشغيل قارئ الحرارة على هذا الجهاز"
            return
        with self._lock:
            if self._stop.is_set():
                ps.kill(); return
            self._ps = ps
        for line in ps.stdout:
            if self._stop.is_set():
                break
            try:
                d = json.loads(line)
            except ValueError:
                continue
            self.data["cpu_temp"] = d.get("cpu")
            self.data["cpu_temp_src"] = d.get("src") or ""
            self.data["gpu_temp"] = d.get("gpu")
            self.data["gpu_load"] = d.get("gload")
            self.temp_note = "" if d.get("cpu") is not None else (
                "ويندوز لا يتيح حرارة المعالج على هذا الجهاز مباشرة. شغّل LibreHardwareMonitor (مجاني) "
                "وسيقرأ البرنامج الحرارة الدقيقة منه تلقائياً.")


# ------------------------------------------------------------------ FPS (PresentMon)
def presentmon_path() -> Path | None:
    roots = [Path(getattr(sys, "_MEIPASS", "")), Path(sys.executable).parent, Path(__file__).resolve().parents[1]]
    for r in roots:
        for rel in ("presentmon/PresentMon.exe", "vendor/PresentMon.exe"):
            p = r / rel
            if str(r) and p.is_file():
                return p
    found = shutil.which("PresentMon") or shutil.which("PresentMon.exe")
    return Path(found) if found else None


def frame_column(header: list[str]) -> int | None:
    """Index of the per-frame time column in PresentMon's CSV (1.x and 2.x names)."""
    names = [h.strip() for h in header]
    for col in ("MsBetweenPresents", "FrameTime", "MsBetweenAppStart", "MsBetweenDisplayChange"):
        if col in names:
            return names.index(col)
    return None


class FrameCounter:
    """Turns PresentMon CSV rows into frames per second (the busiest swap chain over the last second)."""

    def __init__(self, window_s: float = 1.0):
        self.window_s = window_s
        self.col = None
        self.chain_col = None
        self.frames: dict[str, collections.deque] = {}

    def header(self, row: list[str]) -> bool:
        self.col = frame_column(row)
        names = [h.strip() for h in row]
        self.chain_col = names.index("SwapChainAddress") if "SwapChainAddress" in names else None
        return self.col is not None

    def add(self, row: list[str], now: float) -> None:
        if self.col is None or len(row) <= self.col:
            return
        try:
            ms = float(row[self.col])
        except ValueError:
            return
        if ms <= 0 or ms > 2000:
            return
        chain = row[self.chain_col] if self.chain_col is not None and len(row) > self.chain_col else ""
        self.frames.setdefault(chain, collections.deque(maxlen=2000)).append((now, ms))

    def fps(self, now: float) -> float | None:
        best = None
        for dq in self.frames.values():
            while dq and now - dq[0][0] > self.window_s * 2:
                dq.popleft()
            recent = [ms for t, ms in dq if now - t <= self.window_s]
            if len(recent) >= 2:
                f = 1000.0 * len(recent) / sum(recent)
                best = f if best is None or f > best else best
        return round(best, 0) if best is not None else None


class FpsMeter:
    """The frame rate of the game in front, through PresentMon.

    state: off | missing (no PresentMon) | need_admin | waiting (no game in front yet) | running | error."""

    SESSION = "ArabizeGameFPS"

    def __init__(self):
        self.state = "off"
        self.exe: str | None = None
        self.fps: float | None = None
        self._proc: subprocess.Popen | None = None
        self._counter = FrameCounter()
        self._stop = threading.Event()
        self._watch: threading.Thread | None = None
        self._lock = threading.Lock()

    def start(self):
        if self._watch and self._watch.is_alive():
            return
        self._stop.clear()
        self._watch = threading.Thread(target=self._loop, daemon=True, name="fps")
        self._watch.start()

    def stop(self):
        self._stop.set()
        self._kill()
        self.state, self.fps = "off", None

    def _kill(self):
        with self._lock:
            p, self._proc = self._proc, None
        if p:
            try:
                p.kill()
            except Exception:
                pass

    def _loop(self):
        pm = presentmon_path()
        if not IS_WIN or pm is None:
            self.state = "missing"
            return
        if not is_admin():
            self.state = "need_admin"
            return
        while not self._stop.is_set():
            exe = foreground_exe()
            if exe and not exe.lower().startswith(("arabize", "python", "explorer")) and exe != self.exe:
                self._kill()
                self.exe, self.fps = exe, None
                self._spawn(pm, exe)
            elif not self.exe:
                self.state = "waiting"
            if self._stop.wait(3.0):
                break
        self._kill()

    def _spawn(self, pm: Path, exe: str):  # pragma: no cover - Windows only
        args = [str(pm), "--process_name", exe, "--output_stdout", "--no_console_stats", "--v1_metrics",
                "--stop_existing_session", "--session_name", self.SESSION, "--terminate_on_proc_exit"]
        try:
            p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                 creationflags=NO_WINDOW, text=True, encoding="utf-8", errors="replace")
        except Exception as e:
            log.info("PresentMon start failed: %s", e)
            self.state = "error"
            return
        with self._lock:
            self._proc = p
        self.state = "running"
        threading.Thread(target=self._read, args=(p,), daemon=True, name="fps-read").start()

    def _read(self, p: subprocess.Popen):  # pragma: no cover - Windows only
        counter = FrameCounter()
        self._counter = counter
        reader = csv.reader(p.stdout)
        tail = []
        for row in reader:
            if self._stop.is_set():
                break
            if counter.col is None:
                if not counter.header(row):
                    tail.append(",".join(row))
                continue
            counter.add(row, time.monotonic())
            self.fps = counter.fps(time.monotonic())
        if p is self._proc and not self._stop.is_set():
            text = " ".join(tail[-5:]).lower()
            log.info("PresentMon exited: %s", text[:300])
            self.state = "need_admin" if ("elevat" in text or "administrator" in text or "access" in text) else "waiting"
            self.exe = None

    def current(self) -> float | None:
        """FPS now (None while there is no reading)."""
        if self.state != "running":
            return None
        return self._counter.fps(time.monotonic())


FPS_STATES = {
    "off": "متوقف",
    "missing": "قارئ الإطارات غير موجود في هذه النسخة",
    "need_admin": "يحتاج تشغيل البرنامج كمسؤول",
    "waiting": "بانتظار لعبة في المقدمة",
    "running": "يعمل",
    "error": "تعذّر تشغيل قارئ الإطارات",
}
