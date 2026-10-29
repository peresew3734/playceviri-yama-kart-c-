# Planet Zoo 2 TR Yama - Manuel Dosya Çıkarma Yöntemi

Bu yama, `Kurulum.exe` çalıştırılmadan manuel kopyalama için çıkarılmıştır.

## Kaynak dosyalar

- `Kurulum.exe`
- `Setup-0.dat`
- `Setup-1.dat`
- Oyun klasörü: `C:\Users\pc\Desktop\Oyunlar\Planet Zoo 2`

## 1. Kurulum.exe yapısını tespit etme

`Kurulum.exe` bir PyInstaller paketidir. İçeriği şu araçla çıkarılır:

```powershell
pyinstxtractor-ng -i "Kurulum.exe"
pyinstxtractor-ng "Kurulum.exe"
```

Çıkan `installer.pyc` dosyasından okunan bilgiler:

- `CORE_URL = https://playceviri.net/core_logic.dat`
- `CORE_KEY = bytes.fromhex("fd57b011fa96b60312ee153547796ed903bc072b9f5f45973bc744304045598a")`
- `Setup-0.dat` AES-CFB ile şifrelenmiştir; ilk 16 bayt IV, geri kalan ciphertext'tir.
- `Setup-0.dat` çözüldüğünde JSON yapılandırma verisi elde edilir.

## 2. Setup-0.dat çözme

```python
from Crypto.Cipher import AES
import json

key = bytes.fromhex("fd57b011fa96b60312ee153547796ed903bc072b9f5f45973bc744304045598a")
data = open("Setup-0.dat", "rb").read()
iv, ct = data[:16], data[16:]
cipher = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
out = cipher.decrypt(ct)
config = json.loads(out.decode("utf-8"))
```

Bu JSON içinde patch sürümü, API adresi, platform ayarları ve anahtar dosya yolları bulunur.

## 3. Uzak kurulum mantığını alma

`core_logic.dat` dosyası indirilirken `User-Agent` başlığı gerekir:

```powershell
python -c "import urllib.request; urllib.request.urlretrieve('https://playceviri.net/core_logic.dat', 'core_logic.dat')"
```

İndirilen dosya aynı `CORE_KEY` ile AES-CFB yöntemiyle çözülür. Çözülen dosya Python kaynak kodudur ve asıl kurulum mantığını içerir.

## 4. Setup-1.dat çözme ve zip çıkarma

`Setup-1.dat` şifreleme anahtarı kaynak koddan alınır:

```python
ENCRYPTION_KEY_STRING = "pbkdf2_sha256$390000$tJ2mPcbw0eQz$lZ8sYTcZc2VjZ2..."
key = hashlib.sha256(ENCRYPTION_KEY_STRING.encode()).digest()
```

Çözme ve zip çıkarma:

```python
import hashlib, zipfile, os
from Crypto.Cipher import AES

s = "pbkdf2_sha256$390000$tJ2mPcbw0eQz$lZ8sYTcZc2VjZ2..."
key = hashlib.sha256(s.encode()).digest()

data = open("Setup-1.dat", "rb").read()
iv, ct = data[:16], data[16:]
cipher = AES.new(key, AES.MODE_CFB, iv=iv, segment_size=128)
dec = cipher.decrypt(ct)

open("Setup-1.zip", "wb").write(dec)

with zipfile.ZipFile("Setup-1.zip") as zf:
    zf.extractall("patch_files")
```

## Çıkarılan dosyalar

`patch_files` klasörüne şu dosyalar çıkarılmıştır:

- `win64\ovldata\Content0\Localised\English\UnitedKingdom\Loc.ovl`
- `win64\ovldata\Content0\Localised\English\UnitedStates\Loc.ovl`

## Manuel kopyalama

Önce orijinal dosyaları yedekle, sonra yama dosyalarını kopyala:

```powershell
$game = "C:\Users\pc\Desktop\Oyunlar\Planet Zoo 2"
$patch = "C:\Users\pc\Downloads\Planet_Zoo_2_TRyama_v3\patch_files"

Copy-Item "$game\win64\ovldata\Content0\Localised\English\UnitedKingdom\Loc.ovl" "$game\win64\ovldata\Content0\Localised\English\UnitedKingdom\Loc.ovl.backup"
Copy-Item "$game\win64\ovldata\Content0\Localised\English\UnitedStates\Loc.ovl" "$game\win64\ovldata\Content0\Localised\English\UnitedStates\Loc.ovl.backup"

Copy-Item "$patch\win64" "$game" -Recurse -Force
```

Bu işlem sırasında `Kurulum.exe` çalıştırılmamıştır.
PYEOF