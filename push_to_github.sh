#!/bin/bash
# Simple script to push to GitHub

echo "════════════════════════════════════════════════════════════════"
echo "🚀 PUSH TO GITHUB"
echo "════════════════════════════════════════════════════════════════"
echo ""

# Check if remote already exists
if git remote | grep -q "origin"; then
    echo "✅ Remote 'origin' already configured"
    git remote -v
    echo ""
    read -p "Do you want to push now? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Pushing..."
        git push -u origin main
    fi
else
    echo "⚠️  No remote configured yet"
    echo ""
    echo "First, create your repo at: https://github.com/new"
    echo "   Name: Football"
    echo "   Private: ✅ YES"
    echo "   DON'T initialize with README"
    echo ""
    read -p "Enter your repository URL (e.g., https://github.com/username/Football.git): " repo_url
    
    if [ -z "$repo_url" ]; then
        echo "❌ No URL provided. Exiting."
        exit 1
    fi
    
    echo ""
    echo "Adding remote..."
    git remote add origin "$repo_url"
    
    echo "Pushing to GitHub..."
    git push -u origin main
fi

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Done! Check your repo at GitHub"
echo "════════════════════════════════════════════════════════════════"

