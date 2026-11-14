from foundry_local_sdk import Configuration, FoundryLocalManager

def main():
    print("Foundry Local baslatiliyor...")
    config = Configuration(app_name="rag_asistan")
    FoundryLocalManager.initialize(config)
    manager = FoundryLocalManager.instance

    print("Donanim hizlandiricilari hazirlaniyor...")
    manager.download_and_register_eps()

    model = manager.catalog.get_model("qwen2.5-0.5b")
    model.download(lambda p: print(f"\rModel indiriliyor: {p:.1f}%", end=""))
    print()
    model.load()
    print("Model hazir!\n")

    client = model.get_chat_client()
    messages = [{"role": "user", "content": "Merhaba! Kendini bir cumleyle tanıt."}]

    print("Cevap: ", end="")
    for chunk in client.complete_streaming_chat(messages):
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print()

    model.unload()

if __name__ == "__main__":
    main()