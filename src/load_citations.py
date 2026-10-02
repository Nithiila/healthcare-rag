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

def load_deficiency(tx, row):
    # Create Survey node
    tx.run("""
        MERGE (sv:Survey {survey_id: $survey_id})
        SET sv.date = $date,
            sv.type = $type,
            sv.cycle = $cycle
    """,
        survey_id=str(row['CMS Certification Number (CCN)']) + '_' + str(row['Survey Date']),
        date=str(row['Survey Date']),
        type=row['Survey Type'],
        cycle=str(row['Inspection Cycle'])
    )

    # Link Survey to Facility
    tx.run("""
        MATCH (f:Facility {ccn: $ccn})
        MATCH (sv:Survey {survey_id: $survey_id})
        MERGE (f)-[:HAD_SURVEY]->(sv)
    """,
        ccn=str(row['CMS Certification Number (CCN)']),
        survey_id=str(row['CMS Certification Number (CCN)']) + '_' + str(row['Survey Date'])
    )

    # Create Deficiency node
    tx.run("""
        MERGE (d:Deficiency {tag: $tag})
        SET d.description = $description,
            d.category = $category,
            d.prefix = $prefix
    """,
        tag=str(row['Deficiency Tag Number']),
        description=str(row['Deficiency Description'])[:500],
        category=str(row['Deficiency Category']),
        prefix=str(row['Deficiency Prefix'])
    )

    # Link Survey to Deficiency
    tx.run("""
        MATCH (sv:Survey {survey_id: $survey_id})
        MATCH (d:Deficiency {tag: $tag})
        MERGE (sv)-[:CITED {
            severity: $severity,
            corrected: $corrected,
            standard: $standard,
            complaint: $complaint
        }]->(d)
    """,
        survey_id=str(row['CMS Certification Number (CCN)']) + '_' + str(row['Survey Date']),
        tag=str(row['Deficiency Tag Number']),
        severity=str(row['Scope Severity Code']),
        corrected=str(row['Deficiency Corrected']),
        standard=str(row['Standard Deficiency']),
        complaint=str(row['Complaint Deficiency'])
    )

print("Loading health citations CSV...")
df = pd.read_csv(
    os.path.join(DATA_PATH, 'NH_HealthCitations_Aug2026.csv'),
    dtype={'CMS Certification Number (CCN)': str},
    low_memory=False
)
print(f"Loaded {len(df)} citation records")

# Create constraints
print("Creating constraints...")
with driver.session() as session:
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (sv:Survey) REQUIRE sv.survey_id IS UNIQUE")
    session.run("CREATE CONSTRAINT IF NOT EXISTS FOR (d:Deficiency) REQUIRE d.tag IS UNIQUE")

# Load in batches
print("Loading citations into Neo4j...")
batch_size = 500
total = len(df)

for i in range(0, total, batch_size):
    batch = df.iloc[i:i+batch_size]
    with driver.session() as session:
        for _, row in batch.iterrows():
            try:
                session.execute_write(load_deficiency, row)
            except Exception as e:
                print(f"  Skipping row {i}: {e}")
                continue
    if i % 5000 == 0:
        print(f"  Processed {min(i+batch_size, total)}/{total} records")

print("Done loading citations.")
driver.close()