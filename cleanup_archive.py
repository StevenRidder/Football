#!/usr/bin/env python3
"""
Archive unused files to clean up repository.
Moves old scripts, templates, docs, logs, images to archive/
"""
import shutil
from pathlib import Path

# Active files to KEEP
KEEP_FILES = {
    # Main app
    'app_flask.py',
    'requirements.txt',
    'README.md',
    'Dockerfile',
    
    # Active scripts
    'run_simulator_integration.sh',
    'validate_frontend_data.py',
    
    # Simulation engine (entire directory)
    'simulation_engine',
    
    # Templates (only v3)
    'templates/alpha_index_v3.html',
    'templates/base.html',
    'templates/error.html',
    'templates/game_detail.html',
    
    # Data directories
    'data',
    'artifacts',
    'edge_hunt',
    'nfl_edge',
    'static',
    
    # Git files
    '.git',
    '.gitignore',
    '.cursorignore',
}

# Patterns for files to archive
ARCHIVE_PATTERNS = {
    'old_scripts': [
        '*.py.bak',
        'app_alpha.py',
        'app_flask_db.py',
        'generate_*.py',
        'backfill_*.py',
        'calibrate_*.py',
        'compare_*.py',
        'learn_*.py',
        'quick_*.py',
        'test_*.py',
        'validate_features.py',
        'fetch_*.py',
        'import_*.py',
        'load_*.py',
        'parse_*.py',
        'extract_*.py',
        'update_*.py',
        'migrate_*.py',
        'train_*.py',
        'xgboost_*.py',
        'calculate_*.py',
        'sim_backtest*.py',
    ],
    'old_html': [
        'templates/alpha_index.html',
        'templates/alpha_index_v2.html',
        'templates/alpha_dashboard.html',
        'templates/index.html',
        'templates/bets.html',
        'templates/performance.html',
        'templates/accuracy.html',
        'templates/betting_guide.html',
    ],
    'old_docs': [
        '*.md',  # Except README.md (handled separately)
    ],
    'old_logs': [
        '*.log',
        '*.txt',
    ],
    'old_images': [
        '*.png',
        '*.jpg',
        '*.jpeg',
    ],
    'old_data': [
        '*.json',
        '*.csv',  # Except in artifacts/ and data/
        '*.db',
        '*.sqlite',
        '*.sql',
    ],
    'old_backtests': [
        'backtest_*.csv',
        'sim_backtest*.csv',
        'predictions_*.csv',  # Except in artifacts/
    ],
}

# Explicit files to keep
KEEP_EXPLICIT = {
    'app_flask.py',
    'requirements.txt',
    'README.md',
    'Dockerfile',
    'run_simulator_integration.sh',
    'validate_frontend_data.py',
    'templates/alpha_index_v3.html',
    'templates/base.html',
    'templates/error.html',
    'templates/game_detail.html',
}

# Explicit directories to keep
KEEP_DIRECTORIES = {
    'simulation_engine',
    'data',
    'artifacts',
    'edge_hunt',
    'nfl_edge',
    'static',
    'templates',  # But will clean contents
    'archive',
    '.git',
    '.github',
}

def should_keep(path: Path) -> bool:
    """Check if file should be kept."""
    # Keep if in explicit keep list
    if str(path) in KEEP_EXPLICIT:
        return True
    
    # Keep if in keep directory
    for keep_dir in KEEP_DIRECTORIES:
        if path.is_relative_to(Path(keep_dir)):
            return True
    
    # Keep specific backtest/prediction scripts
    if path.name in ['backtest_all_games_conviction.py', 'backtest_2023_2024.py', 
                     'predict_game_correct.py', 'backtest_2022_2024.py',
                     'backtest_ultra_fast.py', 'backtest_optimized.py',
                     'backtest_with_pff.py']:
        return True
    
    # Keep scripts in simulation_engine (entire directory kept)
    if 'simulation_engine' in str(path):
        return True
    
    # Keep .gitignore, .cursorignore
    if path.name.startswith('.') and path.name in ['.gitignore', '.cursorignore']:
        return True
    
    return False

def archive_file(path: Path, archive_dir: Path):
    """Move file to archive directory."""
    dest = archive_dir / path.name
    
    # Handle name conflicts
    counter = 1
    while dest.exists():
        stem = path.stem
        suffix = path.suffix
        dest = archive_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    
    print(f"📦 Archiving: {path.name} -> {dest}")
    shutil.move(str(path), str(dest))
    return dest

def main():
    root = Path('.')
    archive_root = root / 'archive'
    
    print("="*70)
    print("CLEANING UP REPOSITORY")
    print("="*70)
    
    # Process files by pattern
    archived_count = 0
    
    for category, patterns in ARCHIVE_PATTERNS.items():
        archive_dir = archive_root / category
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"\n📁 Processing {category}...")
        
        for pattern in patterns:
            for path in root.glob(pattern):
                # Skip if should keep
                if should_keep(path):
                    continue
                
                # Skip directories
                if path.is_dir():
                    continue
                
                # Skip if already in archive
                if 'archive' in str(path):
                    continue
                
                # Archive it
                try:
                    archive_file(path, archive_dir)
                    archived_count += 1
                except Exception as e:
                    print(f"⚠️  Error archiving {path}: {e}")
    
    # Archive old shell scripts
    print(f"\n📁 Processing old shell scripts...")
    archive_dir = archive_root / 'old_scripts'
    for script in root.glob('*.sh'):
        if script.name not in ['run_simulator_integration.sh']:
            try:
                archive_file(script, archive_dir)
                archived_count += 1
            except Exception as e:
                print(f"⚠️  Error archiving {script}: {e}")
    
    # Archive old JS files
    print(f"\n📁 Processing old JS files...")
    archive_dir = archive_root / 'old_scripts'
    for js_file in root.glob('*.js'):
        try:
            archive_file(js_file, archive_dir)
            archived_count += 1
        except Exception as e:
            print(f"⚠️  Error archiving {js_file}: {e}")
    
    # Archive betonline-fetcher (old extension)
    print(f"\n📁 Processing betonline-fetcher...")
    betonline_dir = root / 'betonline-fetcher'
    if betonline_dir.exists():
        try:
            shutil.move(str(betonline_dir), str(archive_root / 'betonline-fetcher'))
            print(f"📦 Archived directory: betonline-fetcher")
            archived_count += 1
        except Exception as e:
            print(f"⚠️  Error archiving betonline-fetcher: {e}")
    
    print("\n" + "="*70)
    print(f"✅ Archived {archived_count} files/directories")
    print(f"📦 Archive location: {archive_root}")
    print("="*70)

if __name__ == "__main__":
    main()

