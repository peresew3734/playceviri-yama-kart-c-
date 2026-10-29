import hashlib
import os
import re
import shutil
import sys
import threading
import zipfile
from pathlib import Path

from Crypto.Cipher import AES
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

APP_DIR = Path(sys.argv[0]).resolve().parent
ENC_KEY_STRING = "pbkdf2_sha256$390000$tJ2mPcbw0eQz$lZ8sYTcZc2VjZ2..."
ENC_KEY = hashlib.sha256(ENC_KEY_STRING.encode()).digest()


def clean_game_name(folder_name):
    name = re.sub(r"_TRyama.*", "", folder_name, flags=re.IGNORECASE)
    name = name.replace("_", " ").strip()
    return name or folder_name


def norm_name(value):
    return re.sub(r"[^a-z0-9]", "", str(value).lower())


def decrypt_dat(path):
    data = path.read_bytes()
    if len(data) < 16:
        raise ValueError(f"{path.name}: dosya çok küçük")
    iv, ct = data[:16], data[16:]
    cipher = AES.new(ENC_KEY, AES.MODE_CFB, iv=iv, segment_size=128)
    return cipher.decrypt(ct)


def extract_all(exe_path, game_name, status_var, progress):
    base = exe_path.parent
    setups = sorted(p for p in base.glob("Setup-*.dat") if p.name.lower() != "setup-0.dat")
    if not setups:
        raise FileNotFoundError("Seçilen klasörde Setup-*.dat bulunamadı")

    output_root = APP_DIR / "output"
    game_dir = output_root / game_name
    game_dir.mkdir(parents=True, exist_ok=True)

    total = len(setups)
    for i, setup in enumerate(setups, 1):
        status_var.set(f"{setup.name} çözülüyor...")
        progress["value"] = (i - 1) / total * 100
        decrypted = decrypt_dat(setup)

        temp_zip = APP_DIR / "output" / f".{setup.stem}.tmp.zip"
        temp_zip.write_bytes(decrypted)

        target = game_dir
        target.mkdir(parents=True, exist_ok=True)

        status_var.set(f"{setup.name} çıkarılıyor...")
        with zipfile.ZipFile(temp_zip) as zf:
            zf.testzip()
            names = [m.filename for m in zf.infolist() if not m.is_dir()]
            top_dirs = {n.split("/")[0] for n in names if "/" in n}
            strip_prefix = None
            if len(top_dirs) == 1:
                top = next(iter(top_dirs))
                if norm_name(top) == norm_name(game_name) or norm_name(top) in norm_name(game_name) or norm_name(game_name) in norm_name(top):
                    strip_prefix = top + "/"

            if strip_prefix:
                for m in zf.infolist():
                    if m.is_dir():
                        continue
                    arcname = m.filename
                    if arcname.startswith(strip_prefix):
                        arcname = arcname[len(strip_prefix):]
                    if not arcname:
                        continue
                    out_path = target / arcname
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(m) as src, open(out_path, "wb") as dst:
                        shutil.copyfileobj(src, dst)
            else:
                zf.extractall(target)

        try:
            temp_zip.unlink()
        except OSError:
            pass

        progress["value"] = i / total * 100

    status_var.set(f"Tamamlandı: {game_dir}")
    return game_dir


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Yama Çıkarıcı")
        self.geometry("620x260")
        self.resizable(False, False)

        self.exe_var = tk.StringVar()
        self.name_var = tk.StringVar()
        self.status_var = tk.StringVar(value="Kurulum.exe seçin.")

        frame = ttk.Frame(self, padding=16)
        frame.pack(fill="both", expand=True)

        ttk.Label(frame, text="Kurulum.exe:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.exe_var, width=62).grid(row=1, column=0, columnspan=2, sticky="we", pady=4)
        ttk.Button(frame, text="Seç", command=self.choose_exe).grid(row=1, column=2, padx=6)

        ttk.Label(frame, text="Oyun klasör adı:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        ttk.Entry(frame, textvariable=self.name_var, width=62).grid(row=3, column=0, columnspan=2, sticky="we", pady=4)

        ttk.Button(frame, text="Yama dosyalarını çıkar", command=self.start).grid(row=4, column=0, sticky="w", pady=12)

        self.progress = ttk.Progressbar(frame, length=560, mode="determinate")
        self.progress.grid(row=5, column=0, columnspan=3, sticky="we", pady=6)

        ttk.Label(frame, textvariable=self.status_var, wraplength=590).grid(row=6, column=0, columnspan=3, sticky="w")

    def choose_exe(self):
        path = filedialog.askopenfilename(
            title="Kurulum.exe seç",
            filetypes=[("Kurulum.exe", "Kurulum.exe"), ("Tüm dosyalar", "*.*")],
        )
        if not path:
            return
        p = Path(path)
        self.exe_var.set(str(p))
        self.name_var.set(clean_game_name(p.parent.name))

    def start(self):
        exe_text = self.exe_var.get().strip()
        game_name = self.name_var.get().strip()
        if not exe_text:
            messagebox.showerror("Hata", "Önce Kurulum.exe seçin.")
            return
        if not game_name:
            messagebox.showerror("Hata", "Oyun klasör adı boş olamaz.")
            return
        exe_path = Path(exe_text)
        if not exe_path.is_file():
            messagebox.showerror("Hata", "Seçilen dosya bulunamadı.")
            return
        if not (exe_path.parent / "Setup-0.dat").is_file():
            messagebox.showerror("Hata", "Seçilen klasörde Setup-0.dat bulunamadı.")
            return

        self.progress["value"] = 0
        threading.Thread(target=self.run_extract, args=(exe_path, game_name), daemon=True).start()

    def run_extract(self, exe_path, game_name):
        try:
            game_dir = extract_all(exe_path, game_name, self.status_var, self.progress)
            messagebox.showinfo("Tamamlandı", f"Dosyalar çıkarıldı:\n{game_dir}")
        except Exception as e:
            self.status_var.set(f"Hata: {e}")
            messagebox.showerror("Hata", str(e))


if __name__ == "__main__":
    App().mainloop()