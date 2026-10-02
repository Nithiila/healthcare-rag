import pandas as pd

df1 = pd.read_csv(r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\NH_ProviderInfo_Aug2026.csv', nrows=5)
print('PROVIDER INFO COLUMNS:')
print(list(df1.columns))

df2 = pd.read_csv(r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\NH_ProviderInfo_Aug2026.csv')
print('\nProvider Info row count:', len(df2))

df3 = pd.read_csv(r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\NH_HealthCitations_Aug2026.csv', nrows=5)
print('\nHEALTH CITATIONS COLUMNS:')
print(list(df3.columns))

df4 = pd.read_csv(r'C:\Users\nithi\OneDrive\Projects\Knowledge graph RAG\NH_HealthCitations_Aug2026.csv')
print('\nHealth Citations row count:', len(df4))