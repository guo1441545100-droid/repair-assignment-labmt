"""
fetch_data.py

Checks that the one raw input this project needs is present under
data/raw/:

    Data_Set_S1.txt , labMT 1.0 lexicon, from the supporting
                       information of Dodds et al. (2011), PLoS ONE.

The whole repair assignment uses only this one file. If it is missing,
the script prints the exact URL and stops. I don't try to auto-download
because the PLoS supporting-information link sits behind a click-through
and I would rather fail loudly than fetch the wrong file.

Run:
    python src/fetch_data.py
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
LABMT_PATH = RAW_DIR / "Data_Set_S1.txt"


def check_labmt() -> bool:
    if LABMT_PATH.exists():
        size_kb = LABMT_PATH.stat().st_size // 1024
        print(f"[ok]  labMT 1.0 lexicon found at {LABMT_PATH} ({size_kb} KB)")
        return True
    print("[!!]  labMT 1.0 lexicon NOT found.")
    print("      Expected path: data/raw/Data_Set_S1.txt")
    print("      How to get it:")
    print("       1. Open: https://journals.plos.org/plosone/article?"
          "id=10.1371/journal.pone.0026752")
    print("       2. In the 'Supporting Information' section, download")
    print("          'Data Set S1' (a .txt file, about 360 KB).")
    print("       3. Rename if needed and move to data/raw/Data_Set_S1.txt")
    print("")
    print("      Citation for Data_Set_S1.txt:")
    print("      Dodds, P. S., Harris, K. D., Kloumann, I. M.,")
    print("      Bliss, C. A., & Danforth, C. M. (2011). Temporal Patterns")
    print("      of Happiness and Information in a Global Social Network:")
    print("      Hedonometrics and Twitter. PLoS ONE, 6(12), e26752.")
    return False


def main() -> int:
    print("Checking raw inputs under", RAW_DIR)
    if check_labmt():
        print("\nAll raw inputs present. You can now run load_labmt.py.")
        return 0
    print("\nRaw input is missing. Follow the instructions above and rerun.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
