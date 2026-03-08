"""Setup verification script for Atieh data loader."""
import sys
import os
from pathlib import Path

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    os.system('chcp 65001 > nul')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')


def check_dependencies():
    """Check if required Python packages are installed."""
    print("Checking dependencies...")
    required = ['openpyxl', 'pandas', 'pytest']
    missing = []
    
    for package in required:
        try:
            __import__(package)
            print(f"  [OK] {package}")
        except ImportError:
            print(f"  [MISSING] {package}")
            missing.append(package)
    
    if missing:
        print(f"\nMissing packages: {', '.join(missing)}")
        print("Install with: pip install -r requirements.txt")
        return False
    return True


def check_input_files():
    """Check if input Excel files exist."""
    print("\nChecking input files...")
    input_dir = Path("data/inputs")
    
    required_files = [
        "__نوبت دهی 17 دی_.xlsx",
        "درمانهای نا تمام.xlsx",
        "خدمات اقای سرایی.xlsx",
        "تاریخ پرداختی بیمه ها.xlsx"
    ]
    
    missing = []
    for filename in required_files:
        filepath = input_dir / filename
        if filepath.exists():
            print(f"  [OK] {filename}")
        else:
            print(f"  [MISSING] {filename}")
            missing.append(filename)
    
    if missing:
        print(f"\nMissing files: {len(missing)}")
        print(f"Place these files in: {input_dir.absolute()}")
        return False
    return True


def main():
    """Run all checks."""
    print("="*60)
    print("Atieh Data Loader - Setup Verification")
    print("="*60)
    
    deps_ok = check_dependencies()
    files_ok = check_input_files()
    
    print("\n" + "="*60)
    if deps_ok and files_ok:
        print("SUCCESS: All checks passed! Ready to run.")
        print("\nRun the loader with:")
        print("  python -m app.loaders.atieh_loader")
        return 0
    else:
        print("WARNING: Setup incomplete. Please address the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
