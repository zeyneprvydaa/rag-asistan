# Yerel RAG Asistanı (Microsoft Foundry Local)

İnternet bağlantısı olmadan, tamamen kendi bilgisayarında çalışan bir soru-cevap asistanı.

Bilgi tabanı olarak iki sık sorulan sorular kaynağı kullanılır:

- `source/teknofest_faq.txt`: TEKNOFEST (kaynak: https://teknofest.org/tr/kurumsal/sss/, Kasım 2026)
- `source/microsoft_faq.txt`: Microsoft 365 Education (kaynak: https://www.microsoft.com/en/education/products/frequently-asked-questions, Kasım 2026)

Metinlerin hakları ilgili kuruluşlara aittir; yalnızca eğitim amaçlı proje kapsamında kullanılmıştır.

Akış: kullanıcı sorusu → embedding → SQLite'tan en benzer kayıtlar → (gerekirse ön kontrol) → Foundry Local LLM → cevap

## Dil kuralı

Kod, dosya adları, değişkenler, veritabanı şeması ve kod yorumları İngilizce; kullanıcıya gösterilen mesajlar ve bu belge Türkçedir. Bilgi tabanı İngilizcedir, sorular iki dilde sorulabilir. "Bilgim yok" mesajı her durumda aynı ve iki dillidir: `Bu konuda bilgim yok. / I don't have that information.`

## Mimari

| Katman | Kullanılan |
|---|---|
| Arayüz | Komut satırı (CLI) |
| Veri katmanı | SQLite (`knowledge.db`, tablolar `documents` ve `aliases`) |
| Embedding | `intfloat/multilingual-e5-base` (Türkçe + İngilizce) |
| LLM | Foundry Local, `qwen3.5-2b` |

Asistan genellikle soruyla aynı dilde cevap verir (Türkçe soruya Türkçe, İngilizce soruya İngilizce). Her cevabın altında cevabın dayandığı kaynak metin gösterilir.

## Arama yöntemi

Her kayıt iki vektörle saklanır: tüm metin (soru + cevap) ve yalnızca soru satırı. Sorgu skoru ikisinin ağırlıklı ortalamasıdır:

`skor = W_QUESTION × soru_benzerliği + (1 - W_QUESTION) × tüm_metin_benzerliği`

**Türkçe takma sorular.** Bilgi tabanı İngilizce olduğu için Türkçe sorular İngilizce soru satırıyla doğrudan karşılaştırıldığında skor düşük kalıyordu (örn. "A1, A3 ve A5 arasındaki fark nedir?" 0.764 ile eşiğin altında kalıp reddediliyordu). Bunun için `aliases_tr.txt` dosyasında her kaydın cevapladığı Türkçe sorular elle yazıldı (40 kayıt, 67 Türkçe soru). Aramada "soru benzerliği" olarak, İngilizce soru satırı ile o kaydın Türkçe takma sorularından en yüksek olanı kullanılır. Kaynak metinler değiştirilmez, cevaplar hep orijinal İngilizce metinden üretilir.

Aynı dosya biçimi: `İngilizce soru (kaydın ilk satırı, birebir) || Türkçe soru 1 || Türkçe soru 2 ...`

**Skor farkı filtresi.** Eşiği geçen kayıtlardan yalnızca en iyi skordan en fazla `SCORE_MARGIN` (0.03) düşük olanlar LLM'e verilir. Konuyla alakalı ikinci bir kayıt verildiğinde 2B model cevabı karıştırıyordu.

**Ön kontrol.** Sayı ya da miktar soran sorularda ("kaç", "en fazla", "ne kadar", "how many" vb.) LLM'e önce "bu kayıt sorulan bilgiyi doğrudan içeriyor mu?" diye sorulur; cevap hayırsa asistan "bilgim yok" der. Bu kontrol, konusu bilgi tabanında olan ama sayısı olmayan sorularda ("TEKNOFEST'te kaç takım yarışır?") uydurma cevabı engellemek için eklendi. Her soruda çalıştırıldığında doğru soruları da reddettiği için yalnızca bu tür sorularda çalışır.

Ayarlar:

| Ayar | Yer | Değer | Anlamı |
|---|---|---|---|
| `W_QUESTION` | `config.py` | 0.6 | Soru vektörünün ağırlığı |
| `THRESHOLD` | `config.py` | 0.80 | Bu skorun altındaki kayıtlar kullanılmaz |
| `TOP_K` | `config.py` | 3 | Aranan en fazla kayıt sayısı |
| `SCORE_MARGIN` | `assistant.py` | 0.03 | En iyi skordan bu kadar düşük kayıtlar LLM'e verilmez |
| `USE_PRECHECK` | `assistant.py` | `True` | Sayı soran sorularda ön kontrol açık/kapalı |

`W_QUESTION` ve `THRESHOLD` önce TEKNOFEST kaynağıyla 15 soruluk bir test setinde kalibre edildi. Yalnızca soru ya da yalnızca tüm metin kullanıldığında daha az soru doğru kayda eşleşti, karma yöntem en iyi sonucu verdi. İkinci kaynak ve Türkçe takma sorular eklendikten sonra değerler değiştirilmeden yeniden doğrulandı (aşağıdaki Değerlendirme bölümü).

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Proje Windows'ta `foundry-local-sdk-winml` paketiyle geliştirildi. Başka işletim sistemlerinde Foundry Local belgelerindeki uygun SDK paketi gerekir.

İlk çalıştırmada embedding modeli HuggingFace'ten, LLM Foundry Local üzerinden indirilir. Sonrasında internet gerekmez.

## Çalıştırma

1. Dokümanları `source/` klasörüne `.txt` olarak koy. Kayıtlar boş satırla ayrılır; her kaydın ilk satırı soru, kalanı cevaptır. Dosyanın başında başlık ya da boş satır olmamalıdır. İstersen `aliases_tr.txt` dosyasına (proje ana klasörü, `source/` içi değil) o kayıtların Türkçe sorularını ekle.
2. Veritabanını üret: `python ingest.py` (eşleşmeyen takma ad anahtarları için `UYARI` yazar)
3. İsteğe bağlı, arama kalitesini ölç: `python test_retrieval.py`
4. Asistanı başlat: `python assistant.py` (çıkış için `q`)
5. İsteğe bağlı, uçtan uca cevap testi: `python test_end_to_end.py`

Doküman, takma ad dosyası ya da embedding modeli değişirse 2. adım yeniden çalıştırılmalıdır. Asistan ve uçtan uca test aynı anda çalıştırılmamalıdır, ikisi de Foundry Local oturumu açar.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `config.py` | Ortak ayarlar |
| `aliases_tr.txt` | Kayıtların Türkçe soru varyantları (arama için) |
| `ingest.py` | Dokümanları parçalar, embed eder, takma adlarla birlikte SQLite'a yazar (`python ingest.py`) |
| `retriever.py` | Karma arama (İngilizce soru + Türkçe takma adlar + tam metin) |
| `assistant.py` | CLI asistanı; tüm akış `respond()` fonksiyonundadır (skor farkı filtresi, ön kontrol, cevap temizleme) |
| `test_retrieval.py` | Arama doğruluğu ve eşik testi |
| `test_end_to_end.py` | Uçtan uca cevap değerlendirmesi, `evaluation.md` üretir |
| `evaluation.md` | Uçtan uca test sonuçları |
| `test.py` | Foundry Local kurulum testi |

## Değerlendirme

### Arama testi (`test_retrieval.py`): 39/40

| Grup | Sonuç | Açıklama |
|---|---|---|
| A. Bilinen sorular | 16/16 | Bir kısmı `aliases_tr.txt` içindeki ifadelerle aynı, skorlar şişkin olabilir |
| B. Yeni ifadeler | 16/17 | Takma adlarda olmayan Türkçe sorular. Asıl ölçü bu grup |
| C. Konu dışı sorular | 7/7 | Hepsi eşikte reddedildi |

Grup B'deki tek hata: "TEKNOFEST ne amaçla düzenleniyor?" doğru kaydı 2. sırada buldu (0.931, 1. kayıt 0.935). Konu dışı soruların en yükseği 0.790 ("Bitcoin fiyatı nedir?"), eşik 0.80: aradaki pay dar.

### Uçtan uca test (`test_end_to_end.py`): 32 soru

Cevaplar elle okunarak değerlendirildi: 14 doğru, 9 küçük hata, 0 gerçek hata. Cevabı bilgi tabanında olmayan ya da konu dışı 9 sorunun 9'u doğru şekilde reddedildi. Ortalama cevap süresi 0.8 saniyedir.

Küçük hataların hepsi İngilizce kaynağın Türkçeye çevrilmesinden ya da cevap biçiminden gelir: bozuk çeviri ("environment" yerine "çeviklik", "accommodation" yerine "kahramanluk"), cevabın soruyu tekrarlayarak başlaması, Türkçe-İngilizce karışık cümleler. Bir soruda ("Microsoft 365 Education kaç para?") ön kontrol, kayıtta "üç kademe var, fiyat için satış ortağına başvurun" bilgisi olmasına rağmen soruyu reddetti.

Bir önceki sürümde (Türkçe takma adlar ve ön kontrol öncesi, 23 soru) 2 gerçek hata vardı: "Windows 11'e geçmeli miyim?" sorusunda kaynakta olmayan iddialar ve "TEKNOFEST'te kaç takım yarışır?" sorusunda uydurma yönlendirme. Her ikisi de bu sürümde düzeldi. Soru setleri aynı olmadığı için iki sonuç birebir karşılaştırılabilir değildir.

Ayrıntılar `evaluation.md` dosyasındadır. Tablodaki "Otomatik" sütunu kaba bir anahtar kelime kontrolüdür ve bozuk çeviri içeren cevapları da geçmiş sayabilir; asıl ölçü "Elle değerlendirme" sütunudur.

## Kaynaklar ve referanslar

Proje, Microsoft Tech Community'deki "Building Your First Local RAG Application with Foundry Local" yazısındaki mimariyi izler (https://techcommunity.microsoft.com/blog/azuredevcommunityblog/building-your-first-local-rag-application-with-foundry-local/4501968). Foundry Local kurulumu ve sohbet istemcisi için Microsoft Learn'deki Foundry Local başlangıç kılavuzu ile "Tutorial: Build a RAG application" eğitimi izlendi.

## Bilinen kısıtlar

- **Küçük bilgi tabanı:** İki kaynak, toplam 40 soru-cevap kaydı. Arama yöntemi soru-cevap formatına göre ayarlandı; düz paragraf içeren dokümanlarda ayrıca test edilmeli.
- **Takma adlar elle yazılır:** Yeni bir kayıt eklendiğinde Türkçe sorularının `aliases_tr.txt` içine eklenmesi gerekir; eklenmezse kayıt yine bulunur, ama Türkçe sorularda skoru daha düşük çıkabilir. Takma ad sayısı arttıkça konu dışı sorular da eşiğe biraz yaklaşabilir (örn. "Bitcoin fiyatı nedir?" 0.755'ten 0.790'a çıktı).
- **Dar eşik payı:** Konu dışı sorular ile cevaplanabilir sorular arasındaki skor farkı küçük. Eşiği düşürmek ya da çok sayıda yeni kayıt eklemek konu dışı soruların geçmesine yol açabilir; bu durumda eşik yeniden kalibre edilmelidir.
- **Küçük LLM:** 2 milyar parametreli model İngilizce kaynak metinden Türkçe üretirken zaman zaman bozuk çeviri ya da cümle yapar, cevabı soruyu tekrarlayarak başlatabilir ve bazen Türkçe cevaba İngilizce ifadeler karıştırır. Bu yüzden her cevapla birlikte kaynak metin gösterilir, kullanıcı cevabı bununla karşılaştırabilir. Cevabı daha sıkı kurallarla kaynağa bağlamak denendi, ancak model bu durumda Türkçe yanıt yerine İngilizce kaynak cümlesini kopyaladı. Daha büyük model (4B) bu bilgisayarda cevap üretilmeden iptal edildiği için kullanılamadı.
- **Ön kontrol kelime listesine bağlı:** Ön kontrol yalnızca "kaç", "en fazla", "ne kadar" gibi sayı/miktar sözcükleri geçen sorularda çalışır. Sayı sormayan ama cevabı bilgi tabanında olmayan, konuya yakın bir soru yine uydurma cevap alabilir. Ayrıca kısmi bilgi içeren kayıtlarda (örn. fiyat yerine "üç kademe var") soruyu fazla katı reddedebilir.
- **Yalnızca Windows'ta denendi:** Foundry Local Windows, macOS ve Linux'u destekler, ama proje yalnızca Windows'ta (`foundry-local-sdk-winml`) çalıştırıldı. Model olarak 2B `qwen3.5-2b` kullanıldı; 4B model bu bilgisayarda çalışmadı.
- **Brute-force arama:** Tüm kayıtlar bellekte taranır; bu boyutta sorun yok, binlerce kayıtta yavaşlar.