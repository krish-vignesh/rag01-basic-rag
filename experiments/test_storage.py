from src.storage.storage import LocalStorage


storage = LocalStorage("test_storage")


documents = storage.list(
    company_id="novatech"
)

print("Documents:")
print(documents)