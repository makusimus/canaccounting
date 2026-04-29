#!/usr/bin/env python3
"""Command-line CanAccounting processor.
Usage: python3 run.py /path/to/raw/files/ 
Output: Spent.csv and Funding.csv in same folder
"""
import sys, os, csv, io, json
sys.path.insert(0, os.path.dirname(__file__))
from server import process_all, load_overrides, save_overrides

from collections import Counter

# Try to import openpyxl
try:
    import openpyxl
    HAS_XLSX = True
except:
    HAS_XLSX = False

def read_file(path):
    """Read CSV or XLSX and return text content"""
    if path.endswith('.xlsx') and HAS_XLSX:
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        ws = wb.active
        out = io.StringIO()
        w = csv.writer(out)
        for row in ws.iter_rows(values_only=True):
            w.writerow([str(c) if c is not None else '' for c in row])
        return out.getvalue()
    else:
        with open(path, 'rb') as f:
            return f.read().decode('utf-8', errors='replace')

def write_csv(path, data, cols=['Bank','Date','Transaction Details','Category','Amount']):
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(cols)
        for t in data:
            row = [t.get(c,'') for c in cols]
            # Format amount
            if 'Amount' in t and t['Amount'] is not None:
                row[cols.index('Amount')] = f"{float(t['Amount']):.2f}"
            w.writerow(row)

if __name__ == '__main__':
    folder = sys.argv[1] if len(sys.argv) > 1 else '.'
    
    files_data = {}
    for f in sorted(os.listdir(folder)):
        fpath = os.path.join(folder, f)
        if not os.path.isfile(fpath): continue
        fn = f.lower()
        if any(k in fn for k in ['simplii','scotia','rogers']):
            try:
                files_data[f] = read_file(fpath)
                print(f'  ✓ {f}')
            except Exception as e:
                print(f'  ✗ {f}: {e}')
    
    if not files_data:
        print(f'No bank files found in {folder}')
        sys.exit(1)
    
    print(f'\nProcessing {len(files_data)} files...')
    spent, funding, excl = process_all(files_data)
    
    out_spent = os.path.join(folder, 'Spent.csv')
    out_funding = os.path.join(folder, 'Funding.csv')
    write_csv(out_spent, spent)
    write_csv(out_funding, funding)
    
    # Copy overrides to TrainingData too
    ov = load_overrides()
    
    print(f'\n✓ Done!')
    print(f'  Spent:   {len(spent)} rows → {out_spent}')
    print(f'  Funding: {len(funding)} rows → {out_funding}')
    print(f'  Excluded: {excl} transactions')
    print(f'  Overrides: {len(ov)} patterns saved')
    
    sc = Counter(t.get('Category','Other') for t in spent)
    print(f'\nSpent categories:')
    for c,n in sc.most_common():
        s = sum(abs(float(t.get('Amount',0))) for t in spent if t.get('Category','')==c)
        print(f'  {c:25s} {n:4d} tx  ${s:>8.2f}')
    
    fc = Counter(t.get('Category','') for t in funding)
    print(f'\nFunding categories:')
    for c,n in fc.most_common():
        s = sum(float(t.get('Amount',0)) for t in funding if t.get('Category','')==c)
        print(f'  {c:25s} {n:4d} tx  ${s:>8.2f}')
