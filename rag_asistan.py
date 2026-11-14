"""RAG asistanı: top-K retrieval + Foundry Local LLM (CLI)."""
import re

from foundry_local_sdk import Configuration, FoundryLocalManager
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, LLM_ALIAS, THRESHOLD
from retriever import Retriever

NO_ANSWER = "NO_ANSWER"
NO_ANSWER_MSG = "Bu konuda bilgim yok. / I don't have that information."

SYSTEM_PROMPT = (
    "You answer questions using FAQ entries. Each entry has a 'Q:' line and an 'A:' line. "
    "Use only the entry whose Q: matches the user's question, and base your answer ONLY on its A: line. "
    "Do not add any detail that is not in that A: line. "
    "Do not start your answer with 'Yes' or 'No'. "
    "Answer in the same language as the user's question, in 1-2 sentences. "
    f"If no entry answers the question, reply with exactly {NO_ANSWER} and nothing else."
)


def load_llm():
    FoundryLocalManager.initialize(Configuration(app_name="rag_asistan"))
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model(LLM_ALIAS)
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    return model


def format_chunk(chunk):
    """İlk satırı soru, kalanı cevap olarak etiketler."""
    parts = chunk.split("\n", 1)
    if len(parts) == 2:
        return f"Q: {parts[0]}\nA: {parts[1]}"
    return chunk


def answer(client, question, hits):
    context = "\n\n".join(f"[Source: {s}]\n{format_chunk(c)}" for s, c, _ in hits)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"FAQ entry:\n{context}\n\nUser question: {question}"},
    ]
    out = client.complete_chat(messages).choices[0].message.content
    # <think> bloğunu temizle (Qwen3 ailesi)
    text = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip()
    # Model cevap + NO_ANSWER karışık yazarsa kelimeyi at, cevabı koru
    text = text.replace(NO_ANSWER, "").strip()
    # "Yes, there is no..." gibi çelişkili girişleri baştan at
    stripped = re.sub(r"^(yes|no|evet|hayır)\s*[,.:;-]\s*", "", text, flags=re.I)
    if stripped:
        text = stripped[0].upper() + stripped[1:]
    return text if text else NO_ANSWER_MSG


def main():
    print("Embedding modeli yükleniyor...")
    retriever = Retriever(SentenceTransformer(EMBED_MODEL_NAME))

    print("Foundry Local başlatılıyor...")
    model = load_llm()
    client = model.get_chat_client()
    print("\n✅ Asistan hazır! (Çıkış için 'q')\n")

    try:
        while True:
            q = input("Soru: ").strip()
            if q.lower() == "q":
                break
            if not q:
                continue

            results = retriever.search(q)
            print(f"[En iyi eşleşme skoru: {results[0][2] * 100:.1f}%]")
            hits = [h for h in results if h[2] >= THRESHOLD]
            if not hits:
                print("Bilgi tabanında yeterli bilgi yok.\n")
                continue

            for s, c, sc in hits:
                print(f"  -> ({s}, {sc:.3f}) {c.splitlines()[0]}")
            print(f"\nCevap: {answer(client, q, hits)}")
            for _, c, sc in hits:
                print(f"Kaynak ({sc:.3f}): {c.split(chr(10), 1)[-1]}")
            print()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        model.unload()
        print("Çıkılıyor...")


if __name__ == "__main__":
    main()