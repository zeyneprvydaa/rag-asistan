from foundry_local_sdk import Configuration, FoundryLocalManager

FoundryLocalManager.initialize(Configuration(app_name="list_models"))
manager = FoundryLocalManager.instance
catalog = manager.catalog

print("Catalog fonksiyonları:")
print([a for a in dir(catalog) if not a.startswith("_")])

# SDK'daki liste fonksiyonunun adını bilmediğim için birkaç adı deniyorum
for name in ("list_models", "get_models", "models"):
    fn = getattr(catalog, name, None)
    if fn is None:
        continue
    try:
        items = fn() if callable(fn) else fn
        print(f"\n'{name}' sonucu:")
        for m in items:
            print(" -", getattr(m, "alias", None) or getattr(m, "id", None) or m)
        break
    except Exception as e:
        print(f"'{name}' hata verdi: {e}")