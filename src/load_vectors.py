import pandas as pd
import psycopg2
from sentence_transformers import SentenceTransformer
from dotenv import load_dotenv
import os
import json

load_dotenv(dotenv_path=r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\.env')

SUPABASE_URL = os.getenv("SUPABASE_DB_URL")
DATA_PATH = os.getenv("DATA_PATH")

print("Loading embedding model...")
model = SentenceTransformer('all-MiniLM-L6-v2')
print("Model loaded.")

def get_connection():
    return psycopg2.connect(SUPABASE_URL)

# Create table
print("Creating vector table in Supabase...")
conn = get_connection()
cur = conn.cursor()
cur.execute("""
    CREATE TABLE IF NOT EXISTS embeddings (
        id SERIAL PRIMARY KEY,
        text TEXT,
        embedding vector(384),
        metadata JSONB
    );
""")
conn.commit()
cur.close()
conn.close()
print("Table ready.")

# Load provider data
print("Loading provider CSV...")
df = pd.read_csv(
    os.path.join(DATA_PATH, 'NH_ProviderInfo_Aug2026.csv'),
    dtype={'CMS Certification Number (CCN)': str, 'ZIP Code': str}
)
print(f"Loaded {len(df)} facilities")

# Build text chunks
print("Building text chunks...")
chunks = []

for _, row in df.iterrows():
    ccn = str(row['CMS Certification Number (CCN)'])
    text = (
        f"{row['Provider Name']} is a nursing home located in "
        f"{row['City/Town']}, {row['State']}. "
        f"Overall rating: {row['Overall Rating']} stars. "
        f"Ownership type: {row['Ownership Type']}. "
        f"Number of beds: {row['Number of Certified Beds']}. "
    )
    if not pd.isna(row['Chain Name']):
        text += f"Part of {row['Chain Name']} chain. "
    if not pd.isna(row['Staffing Rating']):
        text += f"Staffing rating: {row['Staffing Rating']} stars. "
    if not pd.isna(row['Health Inspection Rating']):
        text += f"Health inspection rating: {row['Health Inspection Rating']} stars. "

    chunks.append({
        'text': text,
        'metadata': {
            'ccn': ccn,
            'name': row['Provider Name'],
            'state': row['State'],
            'type': 'facility_summary'
        }
    })

print(f"Built {len(chunks)} text chunks")

# Insert with fresh connection per batch
print("Generating embeddings and inserting into Supabase...")
batch_size = 50

for i in range(0, len(chunks), batch_size):
    batch = chunks[i:i+batch_size]
    texts = [c['text'] for c in batch]
    embeddings = model.encode(texts, show_progress_bar=False)

    try:
        conn = get_connection()
        cur = conn.cursor()
        for j, chunk in enumerate(batch):
            embedding_list = embeddings[j].tolist()
            cur.execute(
                "INSERT INTO embeddings (text, embedding, metadata) VALUES (%s, %s::vector, %s)",
                (chunk['text'], str(embedding_list), json.dumps(chunk['metadata']))
            )
        conn.commit()
        cur.close()
        conn.close()
        print(f"  Inserted {min(i+batch_size, len(chunks))}/{len(chunks)} chunks")
    except Exception as e:
        print(f"  Error at batch {i}: {e}")
        continue

print("Done loading vectors.")