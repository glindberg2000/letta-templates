# Development Setup

## Latest Version: 0.9.1
Current development is on `feature/group-memory-tools` branch.

## First Time Setup
1. Clone the repository:
```bash
git clone https://github.com/glindberg2000/letta-templates.git
cd letta-templates
```

2. Switch to development branch:
```bash
git checkout feature/group-memory-tools
```

3. Install in development mode:
```bash
pip install -e .
```

## Updating Existing Clone
```bash
# Switch to the branch
git checkout feature/group-memory-tools

# Reset any local changes (if needed)
git reset --hard origin/feature/group-memory-tools

# Pull latest changes
git pull origin feature/group-memory-tools
```

### Example Output
```bash
$ git checkout feature/group-memory-tools
Previous HEAD position was b1484bc chore: bump version to 0.8.0 and update author
Branch 'feature/group-memory-tools' set up to track remote branch 'feature/group-memory-tools' from 'origin'.
Switched to a new branch 'feature/group-memory-tools'

$ git reset --hard origin/feature/group-memory-tools
HEAD is now at abc123d chore: bump version to 0.9.1

$ git pull origin feature/group-memory-tools
From https://github.com/glindberg2000/letta-templates
 * branch            feature/group-memory-tools -> FETCH_HEAD
Already up to date.
```

If you see "Already up to date." after the pull, you're successfully on the latest version!