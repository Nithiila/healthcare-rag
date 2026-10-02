import pandas as pd
from neo4j import GraphDatabase
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\.env')

URI = os.getenv("NEO4J_URI")
USERNAME = os.getenv("NEO4J_USERNAME")
PASSWORD = os.getenv("NEO4J_PASSWORD")
DATA_PATH = os.getenv("DATA_PATH")

driver = GraphDatabase.driver(URI, auth=(USERNAME, PASSWORD))

def load_facilities(tx, row):
    tx.run("""
        MERGE (f:Facility {ccn: $ccn})
        SET f.name = $name,
            f.address = $address,
            f.city = $city,
            f.state = $state,
            f.zip = $zip,
            f.overall_rating = $overall_rating,
            f.beds = $beds,
            f.ownership_type = $ownership_type,
            f.provider_type = $provider_type
    """,
        ccn=str(row['CMS Certification Number (CCN)']),
        name=row['Provider Name'],
        address=row['Provider Address'],
        city=row['City/Town'],
        state=row['State'],
        zip=str(row['ZIP Code']),
        overall_rating=row['Overall Rating'],
        beds=row['Number of Certified Beds'],
        ownership_type=row['Ownership Type'],
        provider_type=row['Provider Type']
    )

def load_chains(tx, row):
    chain_id = row['Chain ID']
    if pd.isna(chain_id):
        return
    tx.run("""
        MERGE (c:Chain {chain_id: $chain_id})
        SET c.name = $name,
            c.num_facilities = $num_facilities
    """,
        chain_id=str(chain_id),
        name=row['Chain Name'] if not pd.isna(row['Chain Name']) else 'Unknown',
        num_facilities=row['Number of Facilities in Chain']
    )
    tx.run("""
        MATCH (f:Facility {ccn: $ccn})
        MATCH (c:Chain {chain_id: $chain_id})
        MERGE (f)-[:BELONGS_TO]->(c)
    """,
        ccn=str(row['CMS Certification Number (CCN)']),
        chain_id=str(chain_id)
    )

def load_states(tx, row):
    tx.run("""
        MERGE (s:State {code: $code})
    """, code=row['State'])
    tx.run("""
        MATCH (f:Facility {ccn: $ccn})
        MATCH (s:State {code: $code})
        MERGE (f)-[:LOCATED_IN]->(s)
    """,
        ccn=str(row['CMS Certification Number (CCN)']),
        code=row['State']
    )

print("Loading provider info CSV...")
df = pd.read_csv(
    os.path.join(DATA_PATH, 'NH_ProviderInfo_Aug2026.csv'),
    dtype={'CMS Certification Number (CCN)': str, 'ZIP Code': str}
)
print(f"Loaded {len(df)} facilities")

print("Creating constraints in Neo4j...")
with driver.session() as session:
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (f:Facility) REQUIRE f.ccn IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (c:Chain) REQUIRE c.chain_id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (s:State) REQUIRE s.code IS UNIQUE")

print("Loading facilities into Neo4j...")
batch_size = 500
total = len(df)

for i in range(0, total, batch_size):
    batch = df.iloc[i:i+batch_size]
    with driver.session() as session:
        for _, row in batch.iterrows():
            session.execute_write(load_facilities, row)
            session.execute_write(load_chains, row)
            session.execute_write(load_states, row)
    print(f"  Processed {min(i+batch_size, total)}/{total} facilities")

print("Done loading graph.")
driver.close()