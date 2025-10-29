#!/bin/bash

# Define paths
SCRIPT_PATH="arch_extract.py"
BASE_INPUT_DIR="/home/faiz/skripsi/HelioVerify/data/microservice-project"
OUTPUT_BASE_DIR="/home/faiz/skripsi/HelioVerify/data/extract_result"

# Define a function to detect architecture type
detect_type() {
  local project_dir="$1"
  # Check for docker-compose.yml or any Docker Compose file
  if find "$project_dir" -type f \( -iname "docker-compose.yml" -o -iname "*.compose.yml" -o -iname "*.compose.yaml" \) | grep -q .; then
    echo "docker"
    return
  fi

  # Check for Docker Compose-like files by scanning for `services:` key in .yml/.yaml
  if grep -r "services:" "$project_dir" --include="*.yml" --include="*.yaml" | grep -q .; then
    echo "docker"
    return
  fi

  # Check for Kubernetes files (`kind:` + `Deployment` or `Service`)
  if grep -r "kind:" "$project_dir" --include="*.yml" --include="*.yaml" | grep -iE "Deployment|Service" | grep -q .; then
    echo "kubernetes"
    return
  fi

  # Fallback to unknown
  echo "unknown"
}

# Loop through each subfolder
for dir in "$BASE_INPUT_DIR"/*; do
  if [ -d "$dir" ]; then
    TYPE=$(detect_type "$dir")

    if [ "$TYPE" == "unknown" ]; then
      echo "⚠️  Skipping $dir: Unknown architecture type"
      echo "--------------------------------------"
      continue
    fi

    FOLDER_NAME=$(basename "$dir")

    echo "🔍 Running extractor for: $dir (type: $TYPE)"
    python "$SCRIPT_PATH" --type "$TYPE" --input "$dir" --output "$OUTPUT_BASE_DIR"
    echo "✅ Done with: $dir"
    echo "--------------------------------------"
  fi
done

echo "🎉 All extractions completed."
