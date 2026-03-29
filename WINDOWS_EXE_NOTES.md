# Windows EXE Notlari

Bu proje Windows `.exe` paketine uygun olacak sekilde tasarlanmaktadir.

## Neden Uygun?

- Arayuz tarayici tabanli lokal HTML/CSS/JS yapidadir.
- Veritabani `SQLite` oldugu icin ayri sunucu veya servis gerekmez.
- Backend standart Python HTTP sunucusu ile lokal `127.0.0.1` uzerinde calisir.
- `PyInstaller` ile Windows tarafinda tek paket haline getirilebilir.

## Bu Turda Kontrol Edilenler

- `web/app.js` syntax kontrolu yapildi.
- Python unit testleri calistirildi.
- Backend ve PDF uretim akisi testlerden gecti.
- Kodda macOS'a ozel Tk bagimliligi yoktur; bu da Windows tarafinda ayni ekranlarin calismasini kolaylastirir.
- Tetkik tanimlarinda virgullu fiyat girisi kabul edilir.
- Uygulama acilisinda gecici veritabani ile startup self-check calisir.
- Web endpoint testleri de gecici veritabani ile dogrulanir.
- Varsayilan veritabani icin otomatik backup snapshot sistemi vardir.
- Tetkik tanimlari kategori bazli yonetilir ve vaka ekraninda kategoriye gore secilir.

## Windows Paketleme

Bu repoda artik iki cikti hedefi vardir:

- `dist\KarpuzVetPatoloji\` : PyInstaller uygulama klasoru
- `installer-dist\setup.exe` : son kullaniciya gonderecegin tek kurulum dosyasi
- `installer-dist\KarpuzVetPatoloji-Windows.zip` : gonderime uygun zip paket

## En Kolay Yol

GitHub'a push ettikten sonra:

- `Actions` sekmesinden `Build Windows Installer` workflow'unu calistir
- is bitince artifact olarak `KarpuzVetPatoloji-Windows-Setup` indir
- icinden `setup.exe` veya `KarpuzVetPatoloji-Windows.zip` dosyasini al
- karsi tarafa tercihen zip dosyasini gonder

Bu dosya kurulum sihirbazi acacak; kullanicinin `cmd` veya Python bilmesi gerekmeyecek.

Windows makinede:

```bat
cd C:\path\to\KarpuzVetHastaTakip
py -3 -m pip install --user pyinstaller reportlab pypdf
build_windows.bat
```

Olusan uygulama paketi:

- `dist\\KarpuzVetPatoloji\\`

Kurulum `.exe` dosyasi icin Inno Setup ile:

```bat
iscc installer_windows.iss
```

Olusan kurulum dosyasi:

- `installer-dist\\setup.exe`

Zip paket icin:

```bat
package_windows_zip.bat
```

Bu komut su dosyayi olusturur:

- `%USERPROFILE%\Desktop\KarpuzVetPatoloji-Windows.zip`

## Not

Bu ortam macOS oldugu icin gercek `.exe` build'i burada uretilmemistir. Ancak Windows paketleme scripti, tarayici tabanli arayuz ve test edilen backend akisleri bu hedefe uygun tutulmustur.
