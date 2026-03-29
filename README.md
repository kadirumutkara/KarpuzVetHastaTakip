# Karpuz Vet Patoloji Takip

Tek bilgisayarda calisan, lokal `SQLite` veritabani kullanan veteriner patoloji takip uygulamasi. Arayuz tarayicida acilir ama sistem internet sitesi degildir; tum veri ayni bilgisayarda saklanir.

Bu surumde:

- Login ekrani var
- Varsayilan `admin` kullanicisi var
- Admin panelinden yeni kullanici eklenebiliyor
- Tetkik tanimlari admin tarafindan ayri ekranda yonetilebiliyor
- Tetkik tanimlari kategori bazli yonetilebiliyor
- Vaka icine birden fazla yapilan tetkik eklenebiliyor
- Vaka icinde secilen tetkiklerin adet ve birim fiyati duzenlenebiliyor
- Histopatoloji raporu PDF olusturulabiliyor
- Analiz talep formu PDF olusturulabiliyor
- Numune borc detayi PDF olusturulabiliyor
- Excel aktarim ekrani ile mevcut `KAYITLAR.xlsx` gibi dosyalar sisteme alinabiliyor
- Uygulama acilisinda gecici veritabani ile startup self-check calisiyor
- Varsayilan veritabani icin otomatik yedek snapshot sistemi var

## Varsayilan Giris

- Kullanici adi: `admin`
- Sifre: `admin123`

Ilk acilistan sonra bu hesapla girip `Kullanicilar` sekmesinden yeni kullanici, `Tetkik Tanimlari` sekmesinden de tetkik kodu, adi ve fiyat listesi ekleyebilirsin.

## Calistirma

macOS:

```bash
cd /Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip
/usr/bin/python3 app.py
```

Uygulama otomatik olarak `http://127.0.0.1:8765` adresini acmaya calisir. Bu port doluysa otomatik olarak sonraki uygun portu kullanir; terminalde acilan gercek adresi yazar.

Windows:

```bat
py -3 app.py
```

Windows `.exe` hedefi icin arayuz ve backend tarayici tabanli tutulmustur; bu sayede macOS ve Windows tarafinda ayni HTML/CSS/JS calisir. Bu repoda Windows paketleme komutu [build_windows.bat](/Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip/build_windows.bat) icinde hazirdir.

Komut satiri bilmeyen son kullanicilar icin hedef dosya:

- `setup.exe`
- `KarpuzVetPatoloji-Windows.zip`

Bu kurulum dosyasi GitHub `Actions` altindaki `Build Windows Installer` workflow'u ile uretilecek sekilde hazirlanmistir.

## Test

```bash
cd /Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip
/usr/bin/python3 -m unittest discover -s tests -v
```

Ek olarak `app.py` her acilista gercek veritabanina dokunmadan gecici bir veritabani ile startup kontrolu calistirir. Bu kontrol:

- admin girisini
- tetkik tanimi olusturmayi
- vaka + tetkik toplam hesabini
- PDF uretimini

dogrular.

## Veri Guvenligi

Bu surumde veritabani guvenligi icin:

- SQLite `WAL` modu aciktir
- yabanci anahtar denetimi aciktir
- varsayilan veritabani kullaniminda otomatik snapshot yedekleri alinir

Yedekler su klasore yazilir:

- `~/KarpuzVetHastaTakip/backups/`

## Loglar

Uygulama acildiginda log dosyalari su klasore yazilir:

- `~/KarpuzVetHastaTakip/logs/`

Olusan ana dosyalar:

- `app-YYYY-MM-DD.log`
- `errors-YYYY-MM-DD.log`

Bir problem oldugunda bu dosyalari isteyebiliriz.

## PDF Ciktilari

PDF ciktilari su klasore yazilir:

- `~/KarpuzVetHastaTakip/exports/`

Olusan baslica belgeler:

- Histopatoloji raporu
- Analiz talep dilekce formu
- Numune borc detayi bilgisi

## Ice Aktar

`Ice Aktar` ekrani, eski Excel kayitlarini toplu olarak sisteme aktarmak icindir. Bu ekran gunluk veri girisinden ayri dusunulmelidir.

## Paketleme

PyInstaller ile paketleme icin yardimci scriptler:

- [build_macos.sh](/Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip/build_macos.sh)
- [build_windows.bat](/Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip/build_windows.bat)
- [installer_windows.iss](/Users/umutkara/Desktop/Umut/PROJECT/KarpuzVetHastaTakip/installer_windows.iss)

macOS tarafinda burada `.app` uretebilirim. Windows `.exe` dosyasi ise normalde Windows ortaminda build edilmelidir.
