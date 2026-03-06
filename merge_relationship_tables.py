import pandas as pd

# Files
sectors_file = "Sectors_relationship_table.csv"
agri_file = "Agriproduction_relationship_table.csv"

# Output file
output_file = "relationship_table.csv"

# Load the files
sectors_df = pd.read_csv(sectors_file)
agri_df = pd.read_csv(agri_file)

# Check column compatibility
if list(sectors_df.columns) != list(agri_df.columns):
    raise ValueError("❌ Column mismatch between the two CSV files")

# Merge (append agri after sectors)
merged_df = pd.concat([sectors_df, agri_df], ignore_index=True)

# Save final relationship table
merged_df.to_csv(output_file, index=False)

print("✅ Merge successful")
print("Rows from sectors:", len(sectors_df))
print("Rows from agriculture:", len(agri_df))
print("Total rows:", len(merged_df))
print("Saved as relationship_table.csv")