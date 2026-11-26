"""CLI RAG assistant: retrieval + Foundry Local LLM.

Run:  python assistant.py   (type 'q' to quit)
"""
import re
from collections import namedtuple

from foundry_local_sdk import Configuration, FoundryLocalManager
from sentence_transformers import SentenceTransformer

from config import EMBED_MODEL_NAME, LLM_ALIAS, THRESHOLD
from retriever import Retriever

# Records scoring more than this below the best one are not given to the LLM
SCORE_MARGIN = 0.03
# Before answering a question that asks for a number or amount, ask the LLM whether the
# best record really contains it (prevents made-up figures on near-topic questions)
USE_PRECHECK = True
QUANTITY_WORDS = (
    "kaç", "en fazla", "en az", "ne kadar",
    "how many", "how much", "maximum", "minimum", "limit",
)

NO_ANSWER = "NO_ANSWER"
# One refusal message for every case, in both languages
NO_ANSWER_MSG = "Bu konuda bilgim yok. / I don't have that information."

SYSTEM_PROMPT = (
    "You answer questions using FAQ entries. Each entry has a 'Q:' line and an 'A:' line. "
    "Use only the entry whose Q: matches the user's question, and base your answer ONLY on its A: line. "
    "Do not add any detail that is not in that A: line. "
    "Do not start your answer with 'Yes' or 'No'. "
    "Answer in the same language as the user's question, in 1-2 sentences. "
    f"If no entry answers the question, reply with exactly {NO_ANSWER} and nothing else."
)

PRECHECK_PROMPT = (
    "You check whether an FAQ entry answers a user's question. "
    "Reply NO only if the A: line is about the same topic but is missing the specific fact the question asks for "
    "(for example the question asks for a number, date, price or limit that is not in the A: line). "
    "If the question asks for advice or a reason (for example 'should I...?' or 'why...?') "
    "and the A: line gives reasons or benefits, reply YES. "
    "Reply with one word: YES or NO."
)

# status: "answered", "threshold" (score too low), "precheck" (pre-check said no), "error"
Response = namedtuple("Response", "top_score reply hits status")


def load_llm():
    # Keep this name: Foundry Local stores its model cache under the app name
    FoundryLocalManager.initialize(Configuration(app_name="rag_asistan"))
    manager = FoundryLocalManager.instance
    manager.download_and_register_eps()
    model = manager.catalog.get_model(LLM_ALIAS)
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    return model


def format_chunk(chunk):
    """Label the first line as the question and the rest as the answer."""
    parts = chunk.split("\n", 1)
    if len(parts) == 2:
        return f"Q: {parts[0]}\nA: {parts[1]}"
    return chunk


def _norm(text):
    return " ".join(text.split()).lower()


def clean_answer(raw, hits):
    """Fix the typical slips of a small model before showing the answer."""
    # Drop the <think> block (Qwen3 family)
    text = re.sub(r"<think>.*?</think>", "", raw, flags=re.S).strip()
    # If the model mixed an answer with NO_ANSWER, keep the answer
    text = text.replace(NO_ANSWER, "").strip()
    # Drop copied "Q: ..." lines and an "A:" label
    lines = text.split("\n")
    while lines and re.match(r"^\s*Q:", lines[0]):
        lines.pop(0)
    text = "\n".join(lines).strip()
    text = re.sub(r"^\s*A:\s*", "", text)
    # Drop a leading Yes/No/Evet/Hayır
    text = re.sub(r"^(yes|no|evet|hayır|hayir)[,.!]?\s+", "", text, flags=re.I)

    # Drop paragraphs copied verbatim from the source when another paragraph remains
    source_text = _norm(" ".join(chunk for _, chunk, _ in hits))
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    remaining = [p for p in paragraphs if _norm(p) not in source_text]
    if remaining:
        text = "\n\n".join(remaining)

    if not text:
        return NO_ANSWER_MSG
    return text[0].upper() + text[1:]


def needs_precheck(question):
    q = question.lower()
    return any(word in q for word in QUANTITY_WORDS)


def entry_answers_question(client, question, chunk):
    """Ask the LLM whether the record directly contains what the question asks for."""
    messages = [
        {"role": "system", "content": PRECHECK_PROMPT},
        {"role": "user", "content": f"{format_chunk(chunk)}\n\nUser question: {question}"},
    ]
    out = client.complete_chat(messages).choices[0].message.content
    out = re.sub(r"<think>.*?</think>", "", out, flags=re.S).strip().upper()
    return not (out.startswith("NO") or out.startswith("HAYIR"))


def generate_answer(client, question, hits):
    context = "\n\n".join(f"[Source: {s}]\n{format_chunk(c)}" for s, c, _ in hits)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"FAQ entry:\n{context}\n\nUser question: {question}"},
    ]
    raw = client.complete_chat(messages).choices[0].message.content
    return clean_answer(raw, hits)


def respond(retriever, client, question):
    """The whole pipeline for one question. Shared by the CLI and the end-to-end test."""
    results = retriever.search(question)
    top_score = results[0][2]

    hits = [h for h in results if h[2] >= THRESHOLD]
    if not hits:
        return Response(top_score, NO_ANSWER_MSG, [], "threshold")

    # Keep only records close to the best one so unrelated ones do not confuse the LLM
    hits = [h for h in hits if h[2] >= hits[0][2] - SCORE_MARGIN]

    try:
        if USE_PRECHECK and needs_precheck(question) and not entry_answers_question(client, question, hits[0][1]):
            return Response(top_score, NO_ANSWER_MSG, hits, "precheck")
        return Response(top_score, generate_answer(client, question, hits), hits, "answered")
    except Exception as e:  # e.g. the model run was cancelled
        return Response(top_score, f"Cevap üretilemedi ({e})", hits, "error")


def main():
    print("Embedding modeli yükleniyor...")
    retriever = Retriever(SentenceTransformer(EMBED_MODEL_NAME))

    print("Foundry Local başlatılıyor...")
    model = load_llm()
    client = model.get_chat_client()
    print("\n✅ Asistan hazır! (Çıkış için 'q')\n")

    try:
        while True:
            question = input("Soru: ").strip()
            if question.lower() == "q":
                break
            if not question:
                continue

            result = respond(retriever, client, question)
            print(f"[En iyi eşleşme skoru: {result.top_score * 100:.1f}%]")
            for source, chunk, score in result.hits:
                print(f"  -> ({source}, {score:.3f}) {chunk.splitlines()[0]}")

            print(f"\nCevap: {result.reply}")
            if result.status == "precheck":
                print("(Ön kontrol: en iyi kayıt sorulan bilgiyi doğrudan içermiyor)")
            elif result.status == "answered":
                for _, chunk, score in result.hits:
                    print(f"Kaynak ({score:.3f}): {chunk.split(chr(10), 1)[-1]}")
            print()
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        model.unload()
        print("Çıkılıyor...")


if __name__ == "__main__":
    main()