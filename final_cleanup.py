#!/usr/bin/env python3
"""
Final cleanup - archive remaining unused files explicitly.
"""
import shutil
from pathlib import Path

root = Path('.')
archive_root = root / 'archive'

# Create archive directories
archive_root.mkdir(exist_ok=True)
for subdir in ['old_html', 'old_docs', 'old_logs', 'old_images', 'old_data', 'old_scripts']:
    (archive_root / subdir).mkdir(exist_ok=True)

# Files/directories to keep
KEEP_FILES = {
    'app_flask.py',
    'requirements.txt',
    'README.md',
    'Dockerfile',
    'run_simulator_integration.sh',
    'validate_frontend_data.py',
    'cleanup_archive.py',
    'final_cleanup.py',
    '.gitignore',
    '.cursorignore',
}

KEEP_HTML = {
    'alpha_index_v3.html',
    'base.html',
    'error.html',
    'game_detail.html',
}

KEEP_DIRS = {
    'simulation_engine',
    'data',
    'artifacts',
    'edge_hunt',
    'nfl_edge',
    'static',
    'templates',  # Will clean contents
    'archive',
    '.git',
}

def archive_files(files, dest_dir, description):
    """Archive list of files."""
    archived = 0
    for filepath in files:
        if filepath.exists() and filepath.is_file():
            dest = dest_dir / filepath.name
            if dest.exists():
                counter = 1
                stem = filepath.stem
                suffix = filepath.suffix
                while dest.exists():
                    dest = dest_dir / f"{stem}_{counter}{suffix}"
                    counter += 1
            try:
                shutil.move(str(filepath), str(dest))
                print(f"📦 {description}: {filepath.name}")
                archived += 1
            except Exception as e:
                print(f"⚠️  Error archiving {filepath}: {e}")
    return archived

print("="*70)
print("FINAL CLEANUP - ARCHIVING UNUSED FILES")
print("="*70)

total_archived = 0

# 1. Archive old HTML templates
print("\n📁 Archiving old HTML templates...")
old_html = []
for html in (root / 'templates').glob('*.html'):
    if html.name not in KEEP_HTML:
        old_html.append(html)
total_archived += archive_files(old_html, archive_root / 'old_html', 'HTML')

# 2. Archive old markdown docs (keep README.md)
print("\n📁 Archiving old documentation...")
old_docs = []
for doc in root.glob('*.md'):
    if doc.name != 'README.md':
        old_docs.append(doc)
total_archived += archive_files(old_docs, archive_root / 'old_docs', 'DOC')

# 3. Archive log files
print("\n📁 Archiving log files...")
logs = list(root.glob('*.log'))
total_archived += archive_files(logs, archive_root / 'old_logs', 'LOG')

# 4. Archive image files
print("\n📁 Archiving image files...")
images = list(root.glob('*.png')) + list(root.glob('*.jpg')) + list(root.glob('*.jpeg'))
total_archived += archive_files(images, archive_root / 'old_images', 'IMAGE')

# 5. Archive old data files in root (not in data/ or artifacts/)
print("\n📁 Archiving old data files...")
old_data = []
for data_file in root.glob('*.json'):
    if data_file.name not in KEEP_FILES:
        old_data.append(data_file)
for data_file in root.glob('*.txt'):
    if data_file.name not in KEEP_FILES:
        old_data.append(data_file)
for data_file in root.glob('*.db'):
    old_data.append(data_file)
total_archived += archive_files(old_data, archive_root / 'old_data', 'DATA')

# 6. Archive old CSV files in root
print("\n📁 Archiving old CSV files from root...")
csv_files = []
for csv in root.glob('*.csv'):
    if csv.name not in KEEP_FILES:
        csv_files.append(csv)
total_archived += archive_files(csv_files, archive_root / 'old_data', 'CSV')

# 7. Archive old shell scripts (keep run_simulator_integration.sh)
print("\n📁 Archiving old shell scripts...")
old_sh = []
for sh in root.glob('*.sh'):
    if sh.name not in KEEP_FILES:
        old_sh.append(sh)
total_archived += archive_files(old_sh, archive_root / 'old_scripts', 'SCRIPT')

# 8. Archive JS files
print("\n📁 Archiving JS files...")
js_files = list(root.glob('*.js'))
total_archived += archive_files(js_files, archive_root / 'old_scripts', 'JS')

print("\n" + "="*70)
print(f"✅ Archived {total_archived} files")
print(f"📦 Archive location: {archive_root}")
print("="*70)

