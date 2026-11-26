# Uçtan Uca Değerlendirme

- LLM: `qwen3.5-2b`
- Embedding: `intfloat/multilingual-e5-base`
- Ayarlar: W_QUESTION=0.6, THRESHOLD=0.8, TOP_K=3
- Otomatik kontrol (anahtar kelime): **20/23**
- Elle değerlendirme: **16 doğru, 5 küçük hata, 2 gerçek hata** (23 soru)
- Ortalama süre: 0.9 sn/soru

| # | Soru | Beklenen | En iyi skor | Gelen cevap | Süre (sn) | Otomatik | Elle değerlendirme |
|---|---|---|---|---|---|---|---|
| 1 | TEKNOFEST nedir? | Cevap: festival / havacılık / aerospace | 0.904 | TEKNOFEST, dünyanın en büyük havacılık, uzay ve teknoloji festivalidir. | 1.2 | ✅ | ✅ Doğru |
| 2 | What is TEKNOFEST? | Cevap: festival / aerospace / largest | 0.928 | TEKNOFEST is the world's largest aerospace, space, and technology festival, organized with the participation of institutions and organizations that contribute to the development of national technology in Turkey. | 1.1 | ✅ | ✅ Doğru, kaynakla birebir |
| 3 | TEKNOFEST'e giriş ücretli mi? | Cevap: ücretsiz / değildir / free | 0.860 | TEKNOFEST'e giriş ücretli değildir. | 0.5 | ✅ | ✅ Doğru |
| 4 | Is there an admission fee for the festival? | Cevap: no admission / free / no fee | 0.949 | There is no admission fee for the festival. | 0.5 | ✅ | ✅ Doğru |
| 5 | TEKNOFEST ne zaman yapılır? | Cevap: her yıl / farklı / every year | 0.897 | TEKNOFEST her yıl farklı şehirlerde ve ülkelerde farklı tarihlerde düzenlenir. | 0.7 | ✅ | ✅ Doğru |
| 6 | TEKNOFEST'e ziyaretçi olarak nasıl katılırım? | Cevap: kayıt / qr / registration | 0.912 | TEKNOFEST'e ziyaretçi olarak katılmak için festival öncesi resmi web sitesinden veya mobil uygulamada online kayıt oluşturmanız gerekir. | 0.9 | ✅ | ✅ Doğru, QR kodu ayrıntısı eksik |
| 7 | TEKNOFEST hangi alanları kapsıyor? | Cevap: yapay zeka / artificial intelligence / havacılık | 0.907 | TEKNOFEST kapsamlı teknolojik ve bilimsel alanları, özellikle havacılık ve uzay, yapay zeka, yazılım, robotik sistemler, enerji, çeviklik, tarım, sağlık ve deniz teknolojilerini kapsamaktadır. | 1.3 | ✅ | ⚠️ Kapsam doğru; çeviri hatası: 'environment' yerine 'çeviklik' |
| 8 | Rapor şablonlarını nereden indirebilirim? | Cevap: şartname / belge / specification | 0.830 | Rapor şablonlarını, ilgili yarışmanın "Sınavlar ve Belgeler" sayfasından indirebilirsiniz. | 0.7 | ✅ | ⚠️ Sayfa adı yanlış çevrilmiş: 'Sınavlar ve Belgeler' (kaynakta 'specifications and documents') |
| 9 | Milli Teknoloji Hamlesi nedir? | Cevap: vizyon / kalkınma / vision | 0.834 | Milli Teknoloji Hamlesi, Türkiye'nin tam bağımsızlığı, gelişmiş ve yüksek teknoloji üretimi hedefi olan kapsamlı bir gelişme vizyonudur. | 1.0 | ✅ | ✅ Doğru |
| 10 | Microsoft 365 Education nedir? | Cevap: platform | 0.942 | Microsoft 365 Education, bir platform, öğrenci öğrenimini desteklerken eğitimcileri ve öğrencileri yapay zeka çağına hazırlar. | 1.0 | ✅ | ⚠️ Anlam kayması: kurumlar yerine 'eğitimciler', cümle bozuk |
| 11 | What is Microsoft 365 Education? | Cevap: platform | 0.973 | Microsoft 365 Education delivers a secure, integrated platform that supports student learning today—while preparing institutions and learners for an AI-powered future. | 0.9 | ✅ | ✅ Doğru, kaynakla birebir |
| 12 | Microsoft 365 Education kaç para? | Cevap: kademe / üç / three | 0.916 | Bilgilerinizde Microsoft 365 Education fiyatlandırması bulunmamaktadır. | 0.8 | ❌ | ⚠️ Fiyat olmadığını söylemesi doğru; üç kademe ve satış ortağı bilgisini vermiyor |
| 13 | Teams'e nasıl giriş yaparım? | Cevap: e-posta / şifre / email | 0.831 | Teams'e nasıl giriş yaparsınız? Okulunuzun e-posta adresi ve şifresini girin. Eğer okulunuz zaten Office 365 veya Microsoft 365 for Education'a bağlıysa ve giriş yapma özelliğini açmışsa, giriş yapabilirsiniz. Sorun yaşarsanız, okulunuzun IT yöneticisine başvurunuz. | 1.8 | ✅ | ✅ Doğru (soruyu tekrar ederek başlıyor) |
| 14 | How do I sign in to Teams? | Cevap: email / password / sign in | 0.902 | To access Microsoft Teams for Education, click Sign In and enter the email address and password provided by your institution. If your institution is already signed up for Office 365 or Microsoft 365 for Education and has turned on access to Microsoft Teams, or if your institution is an accredited academic institution, you will be able to sign in or sign up. If you are having trouble, please contact your institution's IT administrator. | 2.2 | ✅ | ✅ Doğru, kaynakla birebir |
| 15 | Windows 11'e geçmeli miyim? | Cevap: hız / güvenlik / speed | 0.851 | Windows 11'e geçmek zorunlu değildir; ancak cihazınızın minimum gereksinimleri sağlanırsa ve internet bağlantısı varsa, Windows Update üzerinden ücretsiz olarak güncelleyebilirsiniz. | 1.1 | ❌ | ❌ Kaynakta olmayan iddialar: 'zorunlu değildir', 'ücretsiz' |
| 16 | Windows 10 uygulamalarım Windows 11'de çalışır mı? | Cevap: uyumlu / compatible / çalışır | 0.895 | Çoğu Windows 10 uygulaması Windows 11'de çalışır.  Bu, Windows 10 uygulamalarının Windows 11'e uyumlu olduğunu gösterir. | 1.1 | ✅ | ✅ Doğru |
| 17 | Copilot+ PC nedir? | Cevap: yapay zeka / ai / on-device | 0.902 | Copilot+ PC, bir Windows 11 bilgisayarı sınıfıdır. On-ikisinde AI, belirli özelliklerin bilgisayara doğrudan çalışmasını sağlar. | 0.9 | ✅ | ⚠️ Temel bilgi var; bozuk çeviri: 'On-ikisinde AI' |
| 18 | OneDrive hesabını kim yönetir? | Cevap: okul / school / yönetici | 0.868 | OneDrive hesabını kim yönetir? Hesabı yönetmek için okulun IT yöneticisi tarafından erişim kontrolü yapılabilir. | 0.8 | ✅ | ✅ Doğru (soruyu tekrar ederek başlıyor) |
| 19 | TEKNOFEST'te kaç takım yarışır? | Reddedilmeli | 0.852 | TekNOFEST'te yarışma takı sayısı her yıl değiştiği için, bu bilgiyi tekNOFEST'in resmi web sitesinden veya sosyal medya hesaplarından takip etmeniz gerekir. | 1.1 | ❌ | ❌ Reddetmesi gerekirdi; kaynakta olmayan 'sayı her yıl değişir' iddiası, yazım bozuk |
| 20 | Microsoft 365 A3 lisansı kaç dolar? | Reddedilmeli | 0.850 | Bilgilerinizde Microsoft 365 Education A3 lisansının fiyat bilgisi bulunmamaktadır. | 0.8 | ✅ | ✅ Doğru ret: fiyat bilgisi yok |
| 21 | Bitcoin fiyatı nedir? | Reddedilmeli | 0.755 | Bilgi tabanında yeterli bilgi yok. (eşikte reddedildi) | 0.0 | ✅ | ✅ Eşikte reddedildi |
| 22 | What is the capital of France? | Reddedilmeli | 0.731 | Bilgi tabanında yeterli bilgi yok. (eşikte reddedildi) | 0.0 | ✅ | ✅ Eşikte reddedildi |
| 23 | Bugün hava nasıl? | Reddedilmeli | 0.733 | Bilgi tabanında yeterli bilgi yok. (eşikte reddedildi) | 0.0 | ✅ | ✅ Eşikte reddedildi |
