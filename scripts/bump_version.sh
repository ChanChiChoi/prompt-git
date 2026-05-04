#!/bin/bash
# ============================================================
# Version Bump Script for prompt-git
# ============================================================
# Usage:
#   ./scripts/bump_version.sh [major|minor|patch]
#
# Examples:
#   ./scripts/bump_version.sh patch   # 0.1.0 -> 0.1.1
#   ./scripts/bump_version.sh minor   # 0.1.0 -> 0.2.0
#   ./scripts/bump_version.sh major   # 0.1.0 -> 1.0.0
#
# What it does:
#   1. Reads current version from pyproject.toml
#   2. Bumps the specified component
#   3. Updates pyproject.toml and src/promptgit/__init__.py
#   4. Creates a git commit
#   5. Creates a git tag

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Default bump type
BUMP_TYPE=${1:-patch}

# Validate bump type
if [[ ! "$BUMP_TYPE" =~ ^(major|minor|patch)$ ]]; then
    echo -e "${RED}Error: Invalid bump type '$BUMP_TYPE'${NC}"
    echo "Usage: $0 [major|minor|patch]"
    exit 1
fi

# Get current version from pyproject.toml
CURRENT_VERSION=$(grep -E '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')

if [ -z "$CURRENT_VERSION" ]; then
    echo -e "${RED}Error: Could not find version in pyproject.toml${NC}"
    exit 1
fi

echo -e "${GREEN}Current version:${NC} $CURRENT_VERSION"

# Parse version components
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"

# Bump version
case $BUMP_TYPE in
    major)
        MAJOR=$((MAJOR + 1))
        MINOR=0
        PATCH=0
        ;;
    minor)
        MINOR=$((MINOR + 1))
        PATCH=0
        ;;
    patch)
        PATCH=$((PATCH + 1))
        ;;
esac

NEW_VERSION="$MAJOR.$MINOR.$PATCH"
echo -e "${GREEN}New version:${NC} $NEW_VERSION"

# Confirm
echo ""
read -p "Bump version from $CURRENT_VERSION to $NEW_VERSION? (y/N) " -n 1 -r
echo ""
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

# Update pyproject.toml
echo -e "${YELLOW}Updating pyproject.toml...${NC}"
sed -i "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

# Update __init__.py
echo -e "${YELLOW}Updating src/promptgit/__init__.py...${NC}"
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" src/promptgit/__init__.py

# Verify changes
echo ""
echo "Changes:"
git diff pyproject.toml src/promptgit/__init__.py

# Git operations
echo ""
echo -e "${YELLOW}Creating git commit and tag...${NC}"

git add pyproject.toml src/promptgit/__init__.py
git commit -m "chore: bump version to $NEW_VERSION"
git tag -a "v$NEW_VERSION" -m "Release v$NEW_VERSION"

echo ""
echo -e "${GREEN}✓ Version bumped to $NEW_VERSION${NC}"
echo ""
echo "Next steps:"
echo "  git push && git push --tags"
echo ""
echo "The GitHub Action will automatically:"
echo "  1. Build the package"
echo "  2. Publish to PyPI"
echo "  3. Create release assets"
