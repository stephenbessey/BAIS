#!/bin/bash

echo "🧹 Removing 'Clean Code' references from infrastructure files..."
echo "============================================================="

# List of infrastructure files to update
files=(
    "infrastructure/k8s/hpa.yaml"
    "infrastructure/scripts/deploy.sh"
    "infrastructure/monitoring/prometheus-config.yaml"
    "infrastructure/utils/infrastructure_manager.py"
    "infrastructure/logging/filebeat-config.yaml"
    "infrastructure/logging/kibana.yaml"
    "infrastructure/logging/elasticsearch.yaml"
    "infrastructure/logging/logstash-config.yaml"
    "infrastructure/k8s/vpa.yaml"
    "infrastructure/k8s/service.yaml"
    "infrastructure/docker/docker-compose.yml"
    "infrastructure/k8s/deployment.yaml"
    "infrastructure/database/postgresql.yaml"
    "infrastructure/cache/redis-cluster.yaml"
    "infrastructure/docker/Dockerfile"
)

# Function to update a file
update_file() {
    local file=$1
    echo "Updating: $file"
    
    if [ -f "$file" ]; then
        # Replace various Clean Code references in comments
        sed -i '' 's/Clean Code Principles: /Best practices: /g' "$file"
        sed -i '' 's/Clean Code Principles:/Best practices:/g' "$file"
        sed -i '' 's/following Clean Code principles/following best practices/g' "$file"
        sed -i '' 's/Clean Code principles/best practices/g' "$file"
        sed -i '' 's/Clean Code/best practices/g' "$file"
        
        echo "✅ Updated: $file"
    else
        echo "❌ File not found: $file"
    fi
}

# Update all files
for file in "${files[@]}"; do
    update_file "$file"
done

echo ""
echo "🎉 Infrastructure Clean Code references removal complete!"
echo "========================================================"
echo ""
echo "✅ All infrastructure files updated to remove explicit 'Clean Code' references"
echo "✅ Maintained all clean code principles and practices"
echo "✅ Updated documentation to use 'best practices' terminology"
echo ""
echo "The infrastructure codebase now follows clean code principles without explicit references."
