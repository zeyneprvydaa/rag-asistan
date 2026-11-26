# Yerel RAG Asistanı (Microsoft Foundry Local)

İnternet bağlantısı olmadan, tamamen kendi bilgisayarında çalışan bir soru-cevap asistanı.

Bilgi tabanı olarak iki sık sorulan sorular kaynağı kullanılır:

- `source/teknofest_faq.txt`: TEKNOFEST (kaynak:https://teknofest.org/tr/kurumsal/sss/, Kasım 2026)
- `source/microsoft_faq.txt`: Microsoft 365 Education (kaynak:https://www.microsoft.com/en/education/products/frequently-asked-questions, Kasım 2026)

Akış: kullanıcı sorusu → embedding → SQLite'tan en benzer kayıtlar → Foundry Local LLM → cevap

## Mimari

| Katman | Kullanılan |
|---|---|
| Arayüz | Komut satırı (CLI) |
| Veri katmanı | SQLite (`veritabani.db`, tablo `dokumanlar`) |
| Embedding | `intfloat/multilingual-e5-base` (Türkçe + İngilizce) |
| LLM | Foundry Local, `qwen3.5-2b` |

## Arama yöntemi

Her kayıt iki vektörle saklanır: tüm metin (soru + cevap) ve yalnızca soru satırı. Sorgu skoru ikisinin ağırlıklı ortalamasıdır:

`skor = W_QUESTION × soru_benzerliği + (1 - W_QUESTION) × tüm_metin_benzerliği`

Ayarlar `config.py` içindedir:

| Ayar | Değer | Anlamı |
|---|---|---|
| `W_QUESTION` | 0.6 | Soru vektörünün ağırlığı |
| `THRESHOLD` | 0.80 | Bu skorun altındaki kayıtlar kullanılmaz |
| `TOP_K` | 3 | LLM'e verilen en fazla kayıt sayısı |

Bu değerler 15 soruluk bir test setiyle (10 cevaplanabilir, 5 konu dışı soru) kalibre edildi. İkinci kaynak eklendikten sonra 23 soruluk genişletilmiş sette (18 cevaplanabilir, 5 konu dışı) doğrulandı: 22 soruda doğru kayıt 1. sırada geldi, konu dışı soruların hepsi reddedildi. Tek istisna Türkçe bir TEKNOFEST sorusu, doğru kayıt 3. sırada çıktı.

## Kurulum

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

İlk çalıştırmada embedding modeli HuggingFace'ten, LLM Foundry Local üzerinden indirilir. Sonrasında internet gerekmez.

Not: Proje Windows'ta `foundry-local-sdk-winml` paketiyle geliştirildi. Başka işletim sistemlerinde Foundry Local belgelerindeki uygun SDK paketi gerekir.

## Çalıştırma

1. Dokümanları `source/` klasörüne `.txt` olarak koy. Kayıtlar boş satırla ayrılır; her kaydın ilk satırı soru, kalanı cevaptır.
2. Veritabanını üret: `python adim3_parcala_kaydet.py`
3. İsteğe bağlı, arama kalitesini ölç: `python test_retrieval.py`
4. Asistanı başlat: `python rag_asistan.py` (çıkış için `q`)

Doküman ya da embedding modeli değişirse 2. adım yeniden çalıştırılmalıdır.

## Dosyalar

| Dosya | Görevi |
|---|---|
| `config.py` | Ortak ayarlar |
| `adim3_parcala_kaydet.py` | Dokümanları parçalar, embed eder, SQLite'a yazar |
| `retriever.py` | Karma arama |
| `rag_asistan.py` | CLI asistanı |
| `test_retrieval.py` | Arama doğruluğu ve eşik testi |
| `test.py` | Foundry Local kurulum testi |

## Bilinen kısıtlar

- **Küçük bilgi tabanı:** İki kaynak, toplam 40 soru-cevap kaydı. Arama yöntemi soru-cevap formatına göre ayarlandı; düz paragraf içeren dokümanlarda ayrıca test edilmeli.
- **Türkçe sorularda arama:** Bilgi tabanı İngilizce olduğu için bazı Türkçe sorularda doğru kayıt 1. sırada gelmeyebilir (örn. "TEKNOFEST'e giriş ücretli mi?" sorusunda 3. sırada). `TOP_K = 3` bunu telafi eder, ama LLM'in doğru kaydı seçmesine bağlıdır.
- **Küçük LLM:** 2 milyar parametreli model cevaplarda tutarsız olabilir. Türkçe sorulara bazen İngilizce kaynak cümlesini kopyalayarak cevap verir, tavsiye isteyen sorularda ("Windows 11'e geçmeli miyim?") kaynaklarda yazmayan ayrıntı ekleyebilir. Bu yüzden her cevapla birlikte kullanılan kaynak metinler de gösterilir, kullanıcı cevabı bu metinlerle karşılaştırabilir. Daha büyük model (4B) bu bilgisayarda cevap üretmeden iptal edildiği için denenemedi.
- **Eşik sınırı:** Eşik yalnızca konu dışı soruları eler. Konuyla ilgili ama cevabı bilgi tabanında olmayan sorularda ret kararını LLM verir.
- **Brute-force arama:** Tüm kayıtlar bellekte taranır; bu boyutta sorun yok, binlerce kayıtta yavaşlar.