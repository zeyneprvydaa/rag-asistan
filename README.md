# Yerel RAG Asistanı (Microsoft Foundry Local)

İnternet bağlantısı olmadan, tamamen kendi bilgisayarında çalışan bir soru-cevap asistanı.

Bilgi tabanı olarak iki sık sorulan sorular kaynağı kullanılır:

- `source/teknofest_faq.txt`: TEKNOFEST (kaynak: https://teknofest.org/tr/kurumsal/sss/, Kasım 2026)
- `source/microsoft_faq.txt`: Microsoft 365 Education (kaynak: https://www.microsoft.com/en/education/products/frequently-asked-questions, Kasım 2026)

Metinlerin hakları ilgili kuruluşlara aittir; yalnızca eğitim amaçlı proje kapsamında kullanılmıştır.

Akış: kullanıcı sorusu → embedding → SQLite'tan en benzer kayıtlar → Foundry Local LLM → cevap

## Mimari

| Katman | Kullanılan |
|---|---|
| Arayüz | Komut satırı (CLI) |
| Veri katmanı | SQLite (`veritabani.db`, tablo `dokumanlar`) |
| Embedding | `intfloat/multilingual-e5-base` (Türkçe + İngilizce) |
| LLM | Foundry Local, `qwen3.5-2b` |

Asistan soruyla aynı dilde cevap verir (Türkçe soruya Türkçe, İngilizce soruya İngilizce). Her cevabın altında cevabın dayandığı kaynak metinler gösterilir.

## Arama yöntemi

Her kayıt iki vektörle saklanır: tüm metin (soru + cevap) ve yalnızca soru satırı. Sorgu skoru ikisinin ağırlıklı ortalamasıdır:

`skor = W_QUESTION × soru_benzerliği + (1 - W_QUESTION) × tüm_metin_benzerliği`

Ayarlar `config.py` içindedir:

| Ayar | Değer | Anlamı |
|---|---|---|
| `W_QUESTION` | 0.6 | Soru vektörünün ağırlığı |
| `THRESHOLD` | 0.80 | Bu skorun altındaki kayıtlar kullanılmaz |
| `TOP_K` | 3 | LLM'e verilen en fazla kayıt sayısı |

Bu değerler önce TEKNOFEST kaynağıyla 15 soruluk bir test setinde (10 cevaplanabilir, 5 konu dışı soru) kalibre edildi. Yalnızca soru ya da yalnızca tüm metin kullanıldığında daha az soru doğru kayda eşleşti, karma yöntem en iyi sonucu verdi.

İkinci kaynak eklendikten sonra (toplam 40 kayıt) 23 soruluk arama testinde (18 cevaplanabilir, 5 konu dışı) ayarlar yeniden değiştirilmeden doğrulandı: 22 soruda doğru kayıt 1. sırada geldi, konu dışı soruların hepsi reddedildi. Tek istisna Türkçe bir TEKNOFEST sorusu ("TEKNOFEST'e giriş ücretli mi?"), doğru kayıt 3. sırada çıktı. `TOP_K = 3` sayesinde bu kayıt yine de modele ulaşır.

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Proje Windows'ta `foundry-local-sdk-winml` paketiyle geliştirildi. Başka işletim sistemlerinde Foundry Local belgelerindeki uygun SDK paketi gerekir.

İlk çalıştırmada embedding modeli HuggingFace'ten, LLM Foundry Local üzerinden indirilir. Sonrasında internet gerekmez.

## Çalıştırma

1. Dokümanları `source/` klasörüne `.txt` olarak koy. Kayıtlar boş satırla ayrılır; her kaydın ilk satırı soru, kalanı cevaptır. Dosyanın başında başlık ya da boş satır olmamalıdır.
2. Veritabanını üret: `python adim3_parcala_kaydet.py`
3. İsteğe bağlı, arama kalitesini ölç: `python test_retrieval.py`
4. Asistanı başlat: `python rag_asistan.py` (çıkış için `q`)
5. İsteğe bağlı, uçtan uca cevap testi: `python test_end_to_end.py`

Doküman ya da embedding modeli değişirse 2. adım yeniden çalıştırılmalıdır. Asistan ve testler aynı anda çalıştırılmamalıdır, ikisi de Foundry Local oturumu açar.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `config.py` | Ortak ayarlar |
| `adim3_parcala_kaydet.py` | Dokümanları parçalar, embed eder, SQLite'a yazar |
| `retriever.py` | Karma arama |
| `rag_asistan.py` | CLI asistanı |
| `test_retrieval.py` | Arama doğruluğu ve eşik testi |
| `test_end_to_end.py` | Uçtan uca cevap değerlendirmesi, `degerlendirme.md` üretir |
| `degerlendirme.md` | Uçtan uca test sonuçları |
| `sweep_weights.py` | Arama ağırlığını (`W_QUESTION`) yeniden kalibre etmek için yardımcı script |
| `list_models.py` | Foundry Local kataloğundaki modelleri listeler |
| `test.py` | Foundry Local kurulum testi |

## Değerlendirme

23 soruluk uçtan uca testte (TEKNOFEST ve Microsoft kaynakları, Türkçe ve İngilizce, konu dışı ve cevabı bilgi tabanında olmayan sorular) cevaplar elle okunarak değerlendirildi: 16 doğru, 5 küçük hata, 2 gerçek hata. Ortalama cevap süresi 0.9 saniyedir. İngilizce sorulara verilen cevapların hepsi doğruydu; hatalar Türkçe cevaplarda, İngilizce kaynağın çevrilmesi sırasında çıktı.

İki gerçek hata:

- Tavsiye isteyen bir soruda ("Windows 11'e geçmeli miyim?") kaynakta olmayan iddialar.
- Konusu bilgi tabanında olan ama cevabı olmayan bir soruda ("TEKNOFEST'te kaç takım yarışır?") reddetmek yerine uydurma yönlendirme.

Ayrıntılar `degerlendirme.md` dosyasındadır. Test `python test_end_to_end.py` ile yeniden üretilebilir. Tablodaki "Otomatik" sütunu kaba bir anahtar kelime kontrolüdür ve bozuk çeviri içeren cevapları da geçmiş sayabilir; asıl ölçü "Elle değerlendirme" sütunudur.

## Bilinen kısıtlar

- **Küçük bilgi tabanı:** İki kaynak, toplam 40 soru-cevap kaydı. Arama yöntemi soru-cevap formatına göre ayarlandı; düz paragraf içeren dokümanlarda ayrıca test edilmeli.
- **Türkçe sorularda arama:** Bilgi tabanı İngilizce olduğu için bazı Türkçe sorularda doğru kayıt 1. sırada gelmeyebilir (örn. "TEKNOFEST'e giriş ücretli mi?" sorusunda 3. sırada). `TOP_K = 3` bunu telafi eder, ama LLM'in doğru kaydı seçmesine bağlıdır.
- **Küçük LLM:** 2 milyar parametreli model soruyla aynı dilde cevap verir, ama İngilizce kaynak metinden Türkçe üretirken zaman zaman ufak anlam kaymaları ve bozuk cümleler çıkabilir (örn. "institutions" yerine "eğitimciler" demek). Tavsiye isteyen sorularda kaynaklarda yazmayan ayrıntı da ekleyebilir. Bu yüzden her cevapla birlikte kullanılan kaynak metinler gösterilir, kullanıcı cevabı bunlarla karşılaştırabilir. Cevabı daha sıkı kurallarla kaynağa bağlamak denendi, ancak model bu durumda Türkçe yanıt yerine İngilizce kaynak cümlesini kopyaladı. Daha büyük model (4B) bu bilgisayarda cevap üretilmeden iptal edildiği için denenemedi.
- **Eşik sınırı:** Eşik yalnızca konu dışı soruları eler. Konuyla ilgili ama cevabı bilgi tabanında olmayan sorularda ret kararını LLM verir ve bu her zaman doğru çıkmaz.
- **Brute-force arama:** Tüm kayıtlar bellekte taranır; bu boyutta sorun yok, binlerce kayıtta yavaşlar.