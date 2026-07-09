#!/usr/bin/env python
"""
Bible Data Download from Kaggle using Environment Variables
Reads KAGGLE_USERNAME and KAGGLE_KEY from .env file
"""

import os
import json
import zipfile
from pathlib import Path

# Get Kaggle credentials from environment variables
KAGGLE_USERNAME = os.getenv('KAGGLE_USERNAME')
KAGGLE_KEY = os.getenv('KAGGLE_API_TOKEN')

if not KAGGLE_USERNAME or not KAGGLE_KEY:
    print("❌ ERROR: KAGGLE_USERNAME and KAGGLE_KEY environment variables not set")
    print("\nAdd to your .env file:")
    print("  KAGGLE_USERNAME=your_username")
    print("  KAGGLE_KEY=your_api_key")
    exit(1)

print("Setting up Kaggle credentials from environment variables...")

# Create .kaggle directory if it doesn't exist
kaggle_dir = Path.home() / '.kaggle'
kaggle_dir.mkdir(exist_ok=True)

# Create kaggle.json from environment variables
kaggle_json_path = kaggle_dir / 'kaggle.json'
kaggle_config = {
    "username": KAGGLE_USERNAME,
    "key": KAGGLE_KEY
}

with open(kaggle_json_path, 'w') as f:
    json.dump(kaggle_config, f)

# Set proper permissions (Kaggle API requires 600)
kaggle_json_path.chmod(0o600)

print(f"✅ Kaggle credentials configured in {kaggle_json_path}")

from kaggle.api.kaggle_api_extended import KaggleApi

# Create data/raw folder
raw_dir = Path('data/raw')
raw_dir.mkdir(parents=True, exist_ok=True)

# 1. Initialize and authenticate Kaggle API
print("\nAuthenticating with Kaggle...")
api = KaggleApi()
api.authenticate()
print("✅ Authentication successful")

# 2. Define the dataset target and specific versions you want
# This corpus contains: KJV, DARBY, ASV, BBE, WBT, WEB, YLT
DATASET_ID = "oswinrh/bible"
VERSIONS_TO_EXTRACT = ["t_kjv.csv", "t_dby.csv"] 

print(f"\nDownloading dataset '{DATASET_ID}' from Kaggle...")
# Downloads the dataset zip file directly into your raw data directory
api.dataset_download_files(DATASET_ID, path=str(raw_dir), unzip=False)

zip_file_path = raw_dir / f"{DATASET_ID.split('/')[-1]}.zip"

# 3. Unzip and extract ONLY the specified Bible versions
print("Extracting selected Bible files...")
with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
    for file_name in zip_ref.namelist():
        if file_name in VERSIONS_TO_EXTRACT:
            zip_ref.extract(file_name, path=str(raw_dir))
            
            # Show file confirmation size
            extracted_file = raw_dir / file_name
            file_size = os.path.getsize(extracted_file) / 1e6
            print(f"  ✅ Extracted {file_name}: {file_size:.1f} MB")

# Clean up the main zip download file to save space
if zip_file_path.exists():
    os.remove(zip_file_path)
    print("✅ Cleaned up temporary zip file")

print("\n" + "="*50)
print("✅ KJV and DARBY successfully downloaded from Kaggle!")
print("="*50)
print("\nNext steps:")
print("1. Convert CSV to JSON:")
print("   docker-compose exec web python scripts/csv_to_json.py")
print("\n2. Ingest Bible data:")
print("   docker-compose exec web python manage.py ingest_bible --source kjv")
print("\n3. Create embeddings:")
print("   docker-compose exec web python manage.py chunk_and_embed")