#!/usr/bin/env python3
"""CanAccounting Processor Backend v3 — SQLite-backed"""
import csv, os, json, sys, re, uuid, io, shutil, sqlite3
from datetime import datetime
from collections import Counter
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
try:
    import openpyxl
    HAVE_OPENPYXL = True
except ImportError:
    HAVE_OPENPYXL = False

# ==================== CONFIG ====================
ROOT = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(ROOT, 'canaccounting.db')
OVERRIDE_FILE = os.path.join(ROOT, 'overrides.json')
RAW_DIR = os.path.join(ROOT, 'raw_batches')

# ==================== DB SETUP ====================
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS batches (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'uploaded' CHECK(status IN ('uploaded','categorized','reviewed','processed')),
            file_count INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            processed_at TEXT
        );
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bank TEXT NOT NULL,
            date TEXT NOT NULL,
            description TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('spent','funding','excluded')),
            category TEXT NOT NULL DEFAULT 'Other',
            higher_category TEXT DEFAULT 'Running costs',
            reason TEXT,
            source_file TEXT,
            batch_id TEXT,
            committed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS raw_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_id TEXT NOT NULL,
            original_name TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_size INTEGER,
            created_at TEXT DEFAULT (datetime('now'))
        );
    ''')
    conn.commit()
    # Migrate: add higher_category column to existing DB if missing
    try:
        c.execute("SELECT higher_category FROM transactions LIMIT 1")
    except:
        c.execute("ALTER TABLE transactions ADD COLUMN higher_category TEXT DEFAULT 'Running costs'")
        conn.commit()
    conn.close()

# ==================== PATTERN RULES ====================
SR=[
(['lyft','lyft *'],'Taxi'),(['investment wealthsimple'],'Investments'),
(['auto insurance mpi','autopac'],'Car expenses'),(['manitoba hydro','water bill'],'Utilities'),
(['university of calgary','residence services','mycredsmescertif'],'University'),
(['rohitkumar patel'],'Rent'),(['dani scotia'],'Dani transfer'),(['maksym wise'],'Transfer to Wise'),
(['costco gas'],'Gasoline'),(['pos merchandise costco','costco wholesale','costco business','www.costco','costco.ca','www costco'],'Costco'),
(['retail purchase return costco'],'Costco'),(['opos costco'],'Subscriptions'),
(['asessippi ski','ski louise'],'Ski'),(['ozone.hr'],'Split expences'),
(['ikea hrvatska','ikea hr ecom','jysk solin'],'Split expences'),
(['konzum split','lidl hrvatska','tommy split','interspar split','dm pm','pepco croatia','ekupi zagreb','pbzbauhaus'],'Split expences'),
(['ljekarna','slasticarnica','dobri','pekar','ribola','bobis','p-3290','p-23','p-55','city split','tommy263','pu 21000','st hercegovac'],'Split expences'),
(['zadarma'],'Subscriptions'),(['shaw cablesystems','bell mts','bell mobility','bell','rogers communications','rogers ******'],'Mobile&Internet'),
(['spotify','instant ink','coinamatic','bitdefender','microsoftstore','blessed cleaners','universitycom','therlworldcom','cocom bitdefender','annual fee'],'Subscriptions'),
(['freshco'],'Freshco'),(['superstore','real cdn. superstore'],'Superstore'),(['walmart','wal-mart','walmart.ca'],'Walmart'),
(['amzn','amazon'],'Amazon'),(['204 fuels','domo gas','mobil','shell','esso','petro'],'Gasoline'),
(['mb liquor mart','liquor mart','greenstar liquor','galaxy liquor','brooks north'],'Liquor mart'),
(['winners','marshalls','homesense','marshallshomesense'],'Winners'),
(['dollarama','dollar tree'],'Variety items'),(['ikea'],'Variety items'),(['jysk'],'Variety items'),(['temu'],'Variety items'),
(['safeway','sobeys'],'Variety items'),
(['home depot','giant tiger','shoppers drug','rossmann','lidl','valleyview co-op','cabela','canex supermart','bianca amors','staples'],'Variety items'),
(['daily food','sushi','dominos','pizza','kfc','mcdonald','shawarma','pretzels','subway','tim hortons','food culture','korean bbq','evas gelato','yard burger','arbys','quesada'],'Outside dining'),
(['american eagle','adidas','hennes mauritz','just cozy','under armour','clarks','value village','skechers'],'Cloth'),
(['telus spark','cineplex','landmark','royal aviation','famous player','dakota community','pembina trail','western canada lottery','national music centre','sp nmc gift','sq *royal aviation','royal winnipeg ballet'],'Entertainment'),
(['canadian tire','great canadian oil','honk parking','true blue car','rock auto','ucalgary parking','boyd autobody','wecare automotive','reno insurance','murray chrysler','pay by phone','br *bumper'],'Car expenses'),
(['goodlife fitness','sport chek','canad inns','taylor tennis','manitoba canoe'],'Sport and recreation'),
(['city of winnipeg','act*city of winnipeg','adept a&t massage','uofm sports','uofm - sports','bamsocius'],'Sport and recreation'),
(['shared health','rexall pharmacy','gray clinic','greenwoods dental','fire paramedic','anderson family','optometry corpo','doctorsa rome'],'Medicine'),
(['days inn','cozy living','baymont inn','suffield supermart','red river co-op','grouse mountain','centex chestermere','holiday stations','best western','cozy living su'],'Canada travel'),
(['gotogate','klm','flair','air canada','westjet','kiwicom','flighthub','wizz','condor','airline toronto','gate retail','meyer feinkost','purchase holiday','bolteu'],'International travel'),
(['arthur a','bookstore','ltca prestige','project management','uscustoms esta','admission ontario'],'Education'),
(['liubov'],'Liubov transfer'),
(['free interac e-transfer','free interac'],'Liubov transfer'),
(['vladd cars','christa cgi','rbc convention','salarmy'],'Other'),
]
FR=[
(['payroll deposit cgi'],'Salary'),(['interac e-transfer receive liubov','e-transfer receive liubov'],'Liubov transfer'),
(['interest'],'Other income'),(['cheque image deposit'],'Other income'),(['eft credit'],'Other income'),
(['deposit mpi'],'Other income'),(['cash back'],'Other income'),
(['remise carbone','carbon rebate','ind all ac-est','tax refund','no fee cash reward'],'Other income'),
(['initial balance'],'Initial balance 2025'),
]

# ==================== HIGHER CATEGORY MAP ====================
HIGHER_CATEGORY_MAP = {
    # Periodic costs (rare, large amounts)
    'Canada travel': 'Periodic costs',
    'Cash witdrawal': 'Periodic costs',
    'Electronics': 'Periodic costs',
    'International travel': 'Periodic costs',
    'Investments': 'Periodic costs',
    'Liubov transfer': 'Periodic costs',
    'Ski': 'Periodic costs',
    'Split app': 'Periodic costs',
    'Split expences': 'Periodic costs',
    'Transfer to Wise': 'Periodic costs',
    'University': 'Periodic costs',
}

def get_higher_category(category):
    return HIGHER_CATEGORY_MAP.get(category, 'Running costs')

# ==================== CORE LOGIC ====================
def load_overrides():
    try:
        if os.path.exists(OVERRIDE_FILE):
            with open(OVERRIDE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {}

def save_overrides(ov):
    os.makedirs(os.path.dirname(OVERRIDE_FILE), exist_ok=True)
    with open(OVERRIDE_FILE, 'w') as f: json.dump(ov, f, indent=2)

def nd(d):
    d=str(d).strip().strip('"')
    for f in ['%Y-%m-%d','%m/%d/%Y','%m/%d/%y','%b %d,%Y','%b %d,%y','%b %d, %Y','%b %d, %y','%B %d,%Y','%B %d,%y','%d-%b-%y','%d-%b-%Y','%d-%B-%y','%d-%B-%Y']:
        try: return datetime.strptime(d,f).strftime('%Y-%m-%d')
        except: pass
    return d[:10]

def pa(s):
    if not s or not str(s).strip(): return None
    s=str(s).strip().strip('"').replace('$','').replace(',','').replace(' ','')
    try: return float(s)
    except: return None

def catf(details, rules, overrides={}):
    dl=details.lower()
    for k,v in overrides.items():
        if k.lower() in dl: return v
    for keywords,cat in rules:
        if any(k.lower() in dl for k in keywords): return cat
    return None

def parse_csv(text):
    import io
    lines = text.strip().splitlines()
    if not lines: return []
    h = [x.strip().strip('"') for x in next(csv.reader([lines[0]]))]
    rows = []
    for line in lines[1:]:
        if not line.strip(): continue
        vals = next(csv.reader([line]), [])
        if not vals: continue
        row = {}
        for i, k in enumerate(h):
            row[k] = vals[i].strip().strip('"') if i < len(vals) else ''
        rows.append(row)
    return rows

def parse_xlsx(raw_bytes, sheet_idx=0):
    if not HAVE_OPENPYXL: return [], ['openpyxl not installed']
    wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), read_only=True, data_only=True)
    ws = wb.worksheets[sheet_idx]
    rows = list(ws.iter_rows(values_only=True))
    if not rows: return [], []
    headers = [str(h).strip() if h else '' for h in rows[0]]
    result = []
    for row in rows[1:]:
        if not row or all(c is None or (isinstance(c, str) and c.strip() == '') for c in row): continue
        d = {}
        for i, h in enumerate(headers):
            val = row[i] if i < len(row) and row[i] is not None else ''
            d[h] = str(val).strip()
        result.append(d)
    return result, []

def process_all(files_data):
    """Run pattern matching on raw bank file contents, return (spent, funding, excluded) lists.
    Same logic as before — no DB interaction."""
    overrides = load_overrides()
    spent, funding, excluded = [], [], []
    
    def adds(b,d,det,a):
        c=catf(det,SR,overrides) or 'Other'
        spent.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    def addf(b,d,det,a):
        c=catf(det,FR,overrides) or 'Other income'
        funding.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    def adde(b,d,det,a,r):
        excluded.append({'Bank':b,'Date':d,'Transaction Details':det,'Amount':a,'Reason':r})
    
    for fname, text in files_data.items():
        fn=fname.lower()
        if 'simplii' in fn and 'debit' in fn: bt='simplii-debit'
        elif 'simplii' in fn and 'credit' in fn: bt='simplii-credit'
        elif 'rogers' in fn: bt='rogers-credit'
        elif 'scotia' in fn and 'debit' in fn: bt='scotia-debit'
        elif 'scotia' in fn and 'credit' in fn: bt='scotia-credit'
        else: continue
        
        if isinstance(text, bytes):
            rows, errs = parse_xlsx(text)
            if errs:
                for e in errs: print(f'xlsx error: {e}', flush=True)
                continue
        else:
            rows=parse_csv(text)
        if not rows: continue
        bn={'simplii-debit':'Simplii Debit','simplii-credit':'Simplii Credit','scotia-debit':'Scotia Debit','scotia-credit':'Scotia Credit','rogers-credit':'Rogers Credit'}[bt]
        
        if bt=='simplii-debit':
            for row in rows:
                d=nd(row.get('Date',''));det=(row.get('Transaction Details','') or row.get('Description','')).strip()
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                if out:
                    if any(k in det.upper() for k in ['VISA SIMPLII','MASTERCARD ROGERS','FULFILL REQ MAKSYM']): adde('Simplii Debit',d,det,out,'CC payment transfer'); continue
                    if 'INTERNET BILL PAYMENT' in det.upper() and 'UNIVERSITY' not in det.upper(): adde('Simplii Debit',d,det,out,'CC payment transfer'); continue
                    adds('Simplii Debit',d,det,out)
                if inn:
                    if 'RECEIVE MAKSYM' in det.upper(): adde('Simplii Debit',d,det,inn,'Transfer from self'); continue
                    if 'RETAIL PURCHASE RETURN COSTCO' in det.upper(): adds('Simplii Debit',d,det,-inn)
                    elif catf(det,FR): addf('Simplii Debit',d,det,inn)
                    else: addf('Simplii Debit',d,det,inn)
        
        elif bt=='simplii-credit':
            for row in rows:
                d=nd(row.get('Date',''));det=(row.get('Transaction Details','') or row.get('Description','')).strip()
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                card=str(row.get('Credit Card','') or row.get(' Credit Card ','') or '').strip()
                sfx=f' | Card *{card[-4:]}' if len(card)>=4 else ''
                if 'PAYMENT THANK' in det.upper() or 'PAIEMENT' in det.upper(): adde('Simplii Credit',d,det,abs(out or inn or 0),'Payment received'); continue
                if out: adds('Simplii Credit',d,det+sfx,out)
                if inn: adds('Simplii Credit',d,det+sfx,-inn)
        
        elif bt=='scotia-debit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip();d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if any(k in det.upper() for k in ['PEMBINA TRAILS','CUSTOMER TRANSFER DR','MB-CREDIT CARD','LOC PAY']): adde('Scotia Debit',d,det,abs(amt),'Internal transfer/payment'); continue
                if amt<0: adds('Scotia Debit',d,det,abs(amt))
                else: addf('Scotia Debit',d,det,amt)
        
        elif bt=='scotia-credit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip();d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if 'payment from -' in det.lower(): adde('Scotia Credit',d,det,abs(amt),'Payment received'); continue
                adds('Scotia Credit',d,det,abs(amt))
        
        elif bt=='rogers-credit':
            for row in rows:
                keys=list(row.keys())
                det=str(row.get('Description','') or row.get('Merchant Name','') or (row[keys[1]] if len(keys)>1 else '')).strip()
                date_raw = row.get('Date','') or (row.get(keys[0],'') if len(keys)>0 else '')
                d=nd(str(date_raw))
                amt_field=row.get('Amount','') or (row[keys[3]] if len(keys)>3 else '')
                amt=pa(amt_field)
                if amt is None: continue
                if 'payment, thank you' in det.lower(): adde('Rogers Credit',d,det,abs(amt),'Payment received'); continue
                adds('Rogers Credit',d,det,abs(amt))
    
    spent.sort(key=lambda t:t.get('Date','') or '')
    funding.sort(key=lambda t:t.get('Date','') or '')
    return spent, funding, excluded

def categorize_batch(batch_id):
    """Run categorization on a batch's raw files, write results to DB as pending transactions."""
    conn = get_db()
    c = conn.cursor()
    
    # Get raw files for this batch
    c.execute('SELECT original_name, stored_path FROM raw_files WHERE batch_id=?', (batch_id,))
    files = c.fetchall()
    if not files:
        conn.close()
        return None, 'No raw files found for batch'
    
    # Read file contents
    files_data = {}
    for row in files:
        name = row['original_name']
        path = row['stored_path']
        if not os.path.exists(path):
            continue
        with open(path, 'rb') as f:
            files_data[name] = f.read().decode('utf-8', errors='replace') if name.endswith('.csv') else f.read()
    
    if not files_data:
        conn.close()
        return None, 'Could not read any files'
    
    # Run pattern matching
    spent, funding, excluded = process_all(files_data)
    
    # Delete old pending transactions for this batch (in case of re-categorize)
    c.execute('DELETE FROM transactions WHERE batch_id=? AND committed=0', (batch_id,))
    
    def hc(cat):
        return HIGHER_CATEGORY_MAP.get(cat, 'Running costs')

    insert_sql = '''INSERT INTO transactions 
        (bank, date, description, amount, type, category, higher_category, reason, source_file, batch_id, committed)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)'''
    
    def is_duplicate(bank, date, desc, amt):
        c.execute('''SELECT COUNT(*) FROM transactions 
            WHERE committed=1 AND bank=? AND date=? AND description=? AND amount=?''',
            (bank, date, desc, amt))
        return c.fetchone()[0] > 0
    
    total = 0
    dup_found = 0
    for tx in spent:
        if is_duplicate(tx['Bank'], tx['Date'], tx['Transaction Details'], tx['Amount']):
            c.execute(insert_sql, (tx['Bank'], tx['Date'], tx['Transaction Details'],
                                   tx['Amount'], 'excluded', tx['Category'], hc(tx['Category']), 'Duplicate transaction', None, batch_id))
            dup_found += 1
        else:
            c.execute(insert_sql, (tx['Bank'], tx['Date'], tx['Transaction Details'],
                                   tx['Amount'], 'spent', tx['Category'], hc(tx['Category']), None, None, batch_id))
        total += 1
    for tx in funding:
        if is_duplicate(tx['Bank'], tx['Date'], tx['Transaction Details'], tx['Amount']):
            c.execute(insert_sql, (tx['Bank'], tx['Date'], tx['Transaction Details'],
                                   abs(tx['Amount']), 'excluded', tx['Category'], hc(tx['Category']), 'Duplicate transaction', None, batch_id))
            dup_found += 1
        else:
            c.execute(insert_sql, (tx['Bank'], tx['Date'], tx['Transaction Details'],
                                   tx['Amount'], 'funding', tx['Category'], hc(tx['Category']), None, None, batch_id))
        total += 1
    for tx in excluded:
        c.execute(insert_sql, (tx['Bank'], tx['Date'], tx['Transaction Details'],
                               abs(tx['Amount']), 'excluded', 'Internal transfer', 'Running costs', tx.get('Reason',''),
                               None, batch_id))
        total += 1
    
    # Update batch status
    c.execute('UPDATE batches SET status=? WHERE id=?', ('categorized', batch_id))
    conn.commit()
    conn.close()
    
    return {
        'spent': len(spent),
        'funding': len(funding),
        'excluded': len(excluded),
        'duplicates_flagged': dup_found,
        'total': total,
        'batch_id': batch_id
    }, None

# ==================== DUPLICATE DETECTION ====================
def count_duplicates_in_batch(batch_id):
    """Scan raw bank files in a batch and count how many rows match committed transactions."""
    conn = get_db()
    c = conn.cursor()
    
    c.execute('SELECT original_name, stored_path FROM raw_files WHERE batch_id=?', (batch_id,))
    files = c.fetchall()
    if not files:
        conn.close()
        return 0
    
    duplicates = 0
    total_rows = 0
    dup_list = []
    
    for row in files:
        name = row['original_name']
        path = row['stored_path']
        if not os.path.exists(path):
            continue
        
        with open(path, 'rb') as f:
            content = f.read()
        
        fn_lower = name.lower()
        if 'simplii' in fn_lower and 'debit' in fn_lower: bt = 'simplii-debit'
        elif 'simplii' in fn_lower and 'credit' in fn_lower: bt = 'simplii-credit'
        elif 'rogers' in fn_lower: bt = 'rogers-credit'
        elif 'scotia' in fn_lower and 'debit' in fn_lower: bt = 'scotia-debit'
        elif 'scotia' in fn_lower and 'credit' in fn_lower: bt = 'scotia-credit'
        else: continue
        
        bn = {'simplii-debit':'Simplii Debit','simplii-credit':'Simplii Credit',
              'scotia-debit':'Scotia Debit','scotia-credit':'Scotia Credit','rogers-credit':'Rogers Credit'}[bt]
        
        text = content.decode('utf-8', errors='replace')
        rows = parse_csv(text)
        if not rows:
            continue
        
        # Extract (bank, date, description, amount) candidates from each row
        candidates = []
        for row_data in rows:
            if bt == 'simplii-debit':
                d = nd(row_data.get('Date',''))
                det = (row_data.get('Transaction Details','') or row_data.get('Description','')).strip()
                out = pa(row_data.get('Funds Out',''))
                inn = pa(row_data.get('Funds In',''))
                if out:
                    candidates.append((bn, d, det, out))
                if inn:
                    candidates.append((bn, d, det, inn))
            elif bt == 'simplii-credit':
                d = nd(row_data.get('Date',''))
                det = (row_data.get('Transaction Details','') or row_data.get('Description','')).strip()
                card = str(row_data.get('Credit Card','') or row_data.get(' Credit Card ','') or '').strip()
                sfx = f' | Card *{card[-4:]}' if len(card) >= 4 else ''
                out = pa(row_data.get('Funds Out',''))
                inn = pa(row_data.get('Funds In',''))
                if out:
                    candidates.append((bn, d, det + sfx, out))
                if inn:
                    candidates.append((bn, d, det + sfx, abs(inn)))
            elif bt == 'scotia-debit':
                desc = str(row_data.get('Description',''))
                sub = str(row_data.get('Sub-description',''))
                det = f'{desc} — {sub}'.strip()
                d = nd(str(row_data.get('Date','')))
                amt = pa(str(row_data.get('Amount','')))
                if amt is None: continue
                if amt < 0:
                    candidates.append((bn, d, det, abs(amt)))
                else:
                    candidates.append((bn, d, det, amt))
            elif bt == 'scotia-credit':
                desc = str(row_data.get('Description',''))
                sub = str(row_data.get('Sub-description',''))
                det = f'{desc} — {sub}'.strip()
                d = nd(str(row_data.get('Date','')))
                amt = pa(str(row_data.get('Amount','')))
                if amt is None: continue
                candidates.append((bn, d, det, abs(amt)))
            elif bt == 'rogers-credit':
                keys = list(row_data.keys())
                det = str(row_data.get('Description','') or row_data.get('Merchant Name','') or (row_data[keys[1]] if len(keys)>1 else '')).strip()
                date_raw = row_data.get('Date','') or (row_data.get(keys[0],'') if len(keys)>0 else '')
                d = nd(str(date_raw))
                amt_field = row_data.get('Amount','') or (row_data[keys[3]] if len(keys)>3 else '')
                amt = pa(amt_field)
                if amt is None: continue
                candidates.append((bn, d, det, abs(amt)))
        
        for cand in candidates:
            total_rows += 1
            c.execute('''SELECT bank, date, description, amount, category FROM transactions 
                WHERE committed=1 AND bank=? AND date=? AND description=? AND amount=?''', cand)
            match = c.fetchone()
            if match:
                duplicates += 1
                # Store match details including existing category
                dup_list.append({
                    'bank': cand[0],
                    'date': cand[1],
                    'description': cand[2],
                    'amount': cand[3],
                    'existing_category': match['category']
                })
    
    conn.close()
    return duplicates, total_rows, dup_list

# ==================== MULTIPART PARSER ====================
def parse_multipart(rfile, headers):
    content_type = headers.get('Content-Type', '')
    boundary_match = re.search(r'boundary=(?:"([^"]+)"|([^;]+))', content_type)
    if not boundary_match: return {}
    boundary = boundary_match.group(1) or boundary_match.group(2)
    content_length = int(headers.get('Content-Length', 0))
    body = rfile.read(content_length)
    
    parts = body.split(('--' + boundary).encode())
    result = {}
    for part in parts:
        if not part or part == b'--\r\n' or part == b'--': continue
        header_end = part.find(b'\r\n\r\n')
        if header_end == -1: continue
        header_text = part[:header_end].decode('utf-8', errors='replace')
        data = part[header_end+4:]
        if data.endswith(b'\r\n'): data = data[:-2]
        
        filename_match = re.search(r'filename="([^"]*)"', header_text)
        name_match = re.search(r'name="([^"]*)"', header_text)
        if not name_match: continue
        field_name = name_match.group(1)
        
        if filename_match:
            result[field_name] = {'data': data, 'filename': filename_match.group(1)}
        else:
            result[field_name] = data.decode('utf-8', errors='replace')
    return result

# ==================== CSV GENERATORS ====================
def generate_csv(type_filter):
    """Generate CSV from committed transactions. type_filter='spent' or 'funding'"""
    conn = get_db()
    c = conn.cursor()
    
    if type_filter == 'spent':
        c.execute('''SELECT bank, date, description, category, higher_category, amount 
                     FROM transactions WHERE committed=1 AND type='spent' 
                     ORDER BY date''')
        cols = ['Bank','Date','Transaction Details','Category','Higher category','Amount']
    else:
        c.execute('''SELECT bank, date, description, category, higher_category, amount 
                     FROM transactions WHERE committed=1 AND type='funding' 
                     ORDER BY date''')
        cols = ['Bank','Date','Transaction Details','Category','Higher category','Amount']
    
    rows = c.fetchall()
    conn.close()
    
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(cols)
    for row in rows:
        w.writerow([row['bank'], row['date'], row['description'], row['category'], row['higher_category'], f"{row['amount']:.2f}"])
    return out.getvalue()

# ==================== HTTP SERVER ====================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            if self.path == '/':
                self.send_response(200)
                self.send_header('Content-Type', 'text/html; charset=utf-8')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                with open(os.path.join(ROOT, 'index.html'), 'rb') as f:
                    self.wfile.write(f.read())
            
            elif self.path == '/overrides':
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(load_overrides()).encode())
            
            elif self.path == '/batches':
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT id, status, file_count, created_at, processed_at FROM batches ORDER BY created_at DESC LIMIT 50')
                batches = [dict(r) for r in c.fetchall()]
                conn.close()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(batches).encode())
            
            elif self.path.startswith('/batch/'):
                batch_id = self.path[7:]
                conn = get_db()
                c = conn.cursor()
                c.execute('SELECT * FROM batches WHERE id=?', (batch_id,))
                batch = c.fetchone()
                if not batch:
                    self.send_response(404); self.end_headers(); self.wfile.write(b'{"error":"batch not found"}')
                    conn.close(); return
                
                c.execute('SELECT * FROM transactions WHERE batch_id=? AND committed=0 ORDER BY type, date', (batch_id,))
                txs = [dict(r) for r in c.fetchall()]
                conn.close()
                
                result = dict(batch)
                result['transactions'] = txs
                
                # Counts
                sp = sum(1 for t in txs if t['type'] == 'spent')
                fu = sum(1 for t in txs if t['type'] == 'funding')
                ex = sum(1 for t in txs if t['type'] == 'excluded')
                result['counts'] = {'spent': sp, 'funding': fu, 'excluded': ex}
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif self.path == '/export/spent':
                csv_data = generate_csv('spent')
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="Spent.csv"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(csv_data.encode('utf-8'))
            
            elif self.path == '/export/funding':
                csv_data = generate_csv('funding')
                self.send_response(200)
                self.send_header('Content-Type', 'text/csv; charset=utf-8')
                self.send_header('Content-Disposition', 'attachment; filename="Funding.csv"')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(csv_data.encode('utf-8'))
            
            elif self.path == '/stats':
                conn = get_db()
                c = conn.cursor()
                c.execute("SELECT type, COUNT(*) as cnt, SUM(amount) as total FROM transactions WHERE committed=1 AND type IN ('spent','funding') GROUP BY type")
                stats = {r['type']: {'count': r['cnt'], 'total': r['total']} for r in c.fetchall()}
                conn.close()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(stats).encode())
            
            else:
                self.send_response(404); self.end_headers(); self.wfile.write(b'{"error":"not found"}')
        
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            print(f'ERROR in do_GET: {err_msg}', flush=True)
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            except: pass
    
    def do_POST(self):
        try:
            if self.path == '/upload':
                form = parse_multipart(self.rfile, self.headers)
                batch_id = datetime.now().strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:8]
                batch_dir = os.path.join(RAW_DIR, batch_id)
                os.makedirs(batch_dir, exist_ok=True)
                
                file_count = 0
                file_records = []
                
                for field_name, data in form.items():
                    if isinstance(data, dict) and 'data' in data and 'filename' in data:
                        filename = data['filename']
                        content = data['data']
                        # Check if it's a bank file
                        fn_lower = filename.lower()
                        if any(k in fn_lower for k in ['simplii','scotia','rogers']):
                            stored_path = os.path.join(batch_dir, filename)
                            with open(stored_path, 'wb') as f:
                                f.write(content if isinstance(content, bytes) else content.encode())
                            file_count += 1
                            file_records.append((batch_id, filename, stored_path, len(content)))
                
                if file_count == 0:
                    shutil.rmtree(batch_dir, ignore_errors=True)
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': 'No bank files found (filename must contain simplii, scotia, or rogers)'}).encode())
                    return
                
                conn = get_db()
                c = conn.cursor()
                c.execute('INSERT INTO batches (id, status, file_count) VALUES (?, ?, ?)',
                          (batch_id, 'uploaded', file_count))
                for rec in file_records:
                    c.execute('INSERT INTO raw_files (batch_id, original_name, stored_path, file_size) VALUES (?, ?, ?, ?)', rec)
                conn.commit()
                conn.close()
                
                # Check for duplicates against committed DB
                dup_count, total_rows, dup_list = count_duplicates_in_batch(batch_id)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'batch_id': batch_id,
                    'file_count': file_count,
                    'files': [r[1] for r in file_records],
                    'duplicate_count': dup_count,
                    'total_rows': total_rows,
                    'duplicates': dup_list
                }).encode())
            
            elif self.path == '/categorize':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                batch_id = data.get('batch_id', '')
                if not batch_id:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"batch_id required"}'); return
                
                result, err = categorize_batch(batch_id)
                if err:
                    self.send_response(400)
                    self.send_header('Content-Type', 'application/json')
                    self.send_header('Access-Control-Allow-Origin', '*')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': err}).encode())
                    return
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps(result).encode())
            
            elif self.path == '/update_tx':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                tx_id = data.get('id')
                if not tx_id:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"id required"}'); return
                
                conn = get_db()
                c = conn.cursor()
                
                updates = {}
                if 'category' in data:
                    updates['category'] = data['category']
                    updates['higher_category'] = get_higher_category(data['category'])
                if 'reason' in data:
                    updates['reason'] = data['reason']
                if 'type' in data:
                    updates['type'] = data['type']
                
                if updates:
                    set_clause = ', '.join(f'{k}=?' for k in updates.keys())
                    vals = list(updates.values()) + [tx_id]
                    c.execute(f'UPDATE transactions SET {set_clause} WHERE id=?', vals)
                    conn.commit()
                
                conn.close()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
            
            elif self.path == '/process_batch':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                batch_id = data.get('batch_id', '')
                if not batch_id:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"batch_id required"}'); return
                
                conn = get_db()
                c = conn.cursor()
                # Commit all pending transactions for this batch
                c.execute('''UPDATE transactions SET committed=1 WHERE batch_id=? AND committed=0
                             AND type IN ('spent', 'funding')''', (batch_id,))
                committed_count = c.rowcount
                # Excluded also get committed but as excluded
                c.execute('''UPDATE transactions SET committed=1 WHERE batch_id=? AND committed=0
                             AND type='excluded' ''', (batch_id,))
                excluded_count = c.rowcount
                
                c.execute('UPDATE batches SET status=?, processed_at=datetime("now") WHERE id=?',
                          ('processed', batch_id))
                conn.commit()
                conn.close()
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({
                    'ok': True,
                    'committed': committed_count,
                    'excluded': excluded_count,
                    'batch_id': batch_id
                }).encode())
            
            elif self.path == '/save_override':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                ov = load_overrides()
                ov[data['pattern']] = data['category']
                save_overrides(ov)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'count': len(ov)}).encode())
            
            elif self.path == '/delete_override':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                ov = load_overrides()
                ov.pop(data['pattern'], None)
                save_overrides(ov)
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True, 'count': len(ov)}).encode())
            
            elif self.path == '/clear_overrides':
                save_overrides({})
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
            
            elif self.path == '/delete_batch':
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                batch_id = data.get('batch_id', '')
                if not batch_id:
                    self.send_response(400); self.end_headers(); self.wfile.write(b'{"error":"batch_id required"}'); return
                
                conn = get_db()
                c = conn.cursor()
                # Delete pending transactions
                c.execute('DELETE FROM transactions WHERE batch_id=? AND committed=0', (batch_id,))
                # Delete raw files
                c.execute('SELECT stored_path FROM raw_files WHERE batch_id=?', (batch_id,))
                for row in c.fetchall():
                    try: os.remove(row['stored_path'])
                    except: pass
                c.execute('DELETE FROM raw_files WHERE batch_id=?', (batch_id,))
                # Delete batch
                c.execute('DELETE FROM batches WHERE id=?', (batch_id,))
                conn.commit()
                conn.close()
                # Remove batch directory
                batch_dir = os.path.join(RAW_DIR, batch_id)
                shutil.rmtree(batch_dir, ignore_errors=True)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'ok': True}).encode())
            
            else:
                self.send_response(404); self.end_headers(); self.wfile.write(b'{"error":"not found"}')
        
        except Exception as e:
            import traceback
            err_msg = traceback.format_exc()
            print(f'ERROR in do_POST: {err_msg}', flush=True)
            try:
                self.send_response(500)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error': str(e)}).encode())
            except: pass

# ==================== MAIN ====================
if __name__ == '__main__':
    init_db()
    os.makedirs(RAW_DIR, exist_ok=True)
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    server = ThreadingHTTPServer(('0.0.0.0', port), Handler)
    print(f'CanAccounting v3 on http://127.0.0.1:{port}')
    print(f'  DB: {DB_PATH}')
    print(f'  Overrides: {OVERRIDE_FILE}')
    print(f'  Raw files: {RAW_DIR}')
    server.serve_forever()
