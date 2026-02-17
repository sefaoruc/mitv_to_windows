Mi TV Kumandasını Bilgisayarda Kullanmak

Bu yazılım, Xiaomi Mi Stick / Box Bluetooth kumandalarını herhangi bir ek arayüz olmadan doğrudan Windows üzerinde kullanabilmenizi sağlar. 
Program arka planda çalışır,

Çalışma Mantığı
Program, Windows'un Raw Input API sistemini kullanır. 
Kumandanızdan gelen düşük seviyeli Bluetooth sinyallerini (HID verileri) yakalar ve bunları anında Windows klavye kısayollarına veya medya komutlarına dönüştürür.

Mi TV kumandası Bluetooth ile Windows işletim sistemine bağlanabiliyor ancak sadece medya tuşları (ses kısma + arttırma) çalışıyor.
Bu yüzden ek yazılıma ihtiyaç duyuluyor ve bu yazılım sayesinde tüm fonksiyonları çalıştırabiliyoruz.

EXE Avantajı: PyInstaller ile paketlendiği için son kullanıcının bilgisayarında Python veya kütüphane yüklü olması gerekmez.

Arka Plan Performansı: Düşük CPU ve RAM tüketimi için optimize edilmiştir.

Kurulum ve Notlar
Kütüphaneleri Yüklemek İçin:
Terminal veya CMD üzerinden şu komutu çalıştırman yeterlidir:

requirements.txt kurmak için terminale bunu yazın pystray==0.19.5, Pillow==10.2.0, pyinstaller==6.4.0 kütüphaneleri kurulacaktır
```command
pip install -r requirements.txt 
```



Programı Yönetici Olarak Çalıştırın Kapatmak İçin Görev Yöneticisini Kullanın


controller.py Dosyası:

Programın geliştirilmesinde aşağıdaki Python kütüphaneleri kullanılmıştır:

ctypes: Windows'un çekirdek (Kernel32/User32) API'lerine doğrudan erişim sağlar.

pystray: Sistem tepsisinde (sağ altta) ikon ve menü yönetimi yapar.

threading: Kumanda dinleme işlemi ile arayüz işlemlerinin birbirini dondurmadan paralel çalışmasını sağlar.

subprocess: Windows PowerShell üzerinden modern "Toast" bildirimleri fırlatmak için kullanılır.


ble_key_analysis.py Dosyası:
2. Üç Farklı Cihaz Modu Dinleme
Kod, kumandayı sadece bir klavye olarak görmez. Üç farklı HID (Human Interface Device) sınıfını aynı anda takip eder:

0x01, 0x06 (Klavye): Standart karakter ve fonksiyon tuşları.

0x01, 0x05 (Gamepad): Kumandanın yön tuşlarının bazı modlarda gönderdiği sinyaller.

0x0C, 0x01 (Tüketici Kontrolü): Ses açma/kısma, medya oynatma/durdurma gibi multimedya tuşları.

3. Sinyal Çözümleme (Decoding)
Kumandadan bir tuşa basıldığında bilgisayara bir bayt (byte) dizisi gelir. Kodun ana kalbi olan process_data fonksiyonu bu diziyi analiz eder:

Örneğin, gelen verinin 2. baytı (d[1]) "1" ise bunun "OK" tuşu olduğunu anlar ve Windows'a bir "Enter" komutu gönderir.

"32" gelirse ekranı kilitler (Win+L), "64" gelirse arama menüsünü açar (Win+S).

4. Klavye Simülasyonu
Yakalanan bu özel sinyaller, ctypes.windll.user32.keybd_event fonksiyonu aracılığıyla Windows'un anlayacağı standart tuş vuruşlarına dönüştürülür. 
Bu, sanki bilgisayara fiziksel bir klavye bağlıymış ve o tuşa basılmış gibi bir illüzyon yaratır.

5. Arka Planda Çalışma Yapısı
Kod, görünür bir pencere yerine arka planda çalışan gizli bir pencere (Message-only window) oluşturur. 
GetMessageW döngüsü ile sürekli olarak işlemciyi yormadan Windows'tan gelecek sinyalleri bekler.

Neden Windows'ta çalışmıyor?
1. Standart HID vs. Özel (Vendor-Specific) Protokol
Windows, bir Bluetooth cihaz bağlandığında onun "kimlik kartına" (HID Descriptor) bakar. 
Eğer cihaz "Ben standart bir ses açma/kısma tuşuyum" derse, Windows bunu hemen anlar ve çalıştırır. 
Ancak Mi Stick kumandasındaki Netflix, Prime Video veya OK gibi tuşlar, üreticiye özel (vendor-specific) ham veri paketleri gönderir. 
Windows bu paketleri görür ama ne anlama geldiklerini bilmediği için hiçbir işlem yapmadan çöpe atar. 
Senin yazdığın kod, bu "bilinmeyen" paketleri yakalayıp tercüme eden bir tercüman görevi görür.

2. "Raw Input" Koruması
Windows, güvenlik nedeniyle herhangi bir uygulamanın klavyeyi veya fareyi izinsiz dinlemesini engeller. 
Mi Stick kumandasının bazı özel tuşları, standart klavye tuşu olarak değil, ham veri (raw data) olarak gelir. 
Windows bu verileri sistem düzeyinde bir "tuş basımı" olarak kabul etmez. 
Yazılımın içindeki RIDEV_INPUTSINK bayrağı, Windows'a şu mesajı verir: "Bu cihazdan gelen veriyi ne olursa olsun bana ver, ben ne yapacağımı biliyorum". 
Windows'un kendi içinde böyle bir otomatik yönlendirme mekanizması yoktur.

3. Çoklu Kimlik Karmaşası (Composite Device)
Daha önce konuştuğumuz gibi kumanda 3 farklı parça (Klavye, Gamepad, Tüketici Kontrolü) olarak çalışır. 
Windows genelde bir cihazdan gelen veriyi tek bir kanal üzerinden bekler. 
Kumanda aynı anda hem klavye hem de gamepad gibi davrandığında, 
Windows hangi sinyalin hangi işleme (örneğin "OK" tuşunun "Enter" mı yoksa "A butonu" mu olduğuna) karar veremez. 
Senin kodun bu 3 kanalı aynı anda dinleyerek (0x01, 0x06; 0x01, 0x05; 0x0C, 0x01) karmaşayı çözer.

4. Sürücü (Driver) Eksikliği
Xiaomi bu kumandayı Windows için değil, Android TV (Linux tabanlı) için tasarlamıştır. 
Android sistemlerde bu "tercüme" işlemi işletim sisteminin içine gömülüdür. 
Windows tarafında ise Xiaomi resmi bir sürücü yayınlamadığı için, Windows kumandayı sadece "basit bir Bluetooth kulaklık kumandası" seviyesinde tanıyabilir.
