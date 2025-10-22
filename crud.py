from connect import client

# Choose your database and collection
db = client["my_app_db"]
collection = db["sample"]

def insert_sample(doc):
    """Insert one document and return its ID."""
    result = collection.insert_one(doc)
    return str(result.inserted_id)

def find_all():
    """Return all documents in the collection."""
    return list(collection.find())

def delete_all():
    """Delete all documents."""
    collection.delete_many({})
    return "All documents deleted."

# --- Quick test ---
if __name__ == "__main__":
    print("🧪 Running CRUD sanity test...")
    print(delete_all())
    inserted_id = insert_sample({"name": "Zakaria", "msg": "Hello MongoDB!"})
    print("Inserted ID:", inserted_id)
    print("All documents:", find_all())
