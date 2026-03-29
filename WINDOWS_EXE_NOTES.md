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

Windows makinede:

```bat
cd C:\path\to\KarpuzVetHastaTakip
py -3 -m pip install --user pyinstaller reportlab
build_windows.bat
```

Olusan paket:

- `dist\\KarpuzVetPatoloji\\`
- veya PyInstaller ayarina gore `KarpuzVetPatoloji.exe`

## Not

Bu ortam macOS oldugu icin gercek `.exe` build'i burada uretilmemistir. Ancak Windows paketleme scripti, tarayici tabanli arayuz ve test edilen backend akisleri bu hedefe uygun tutulmustur.
