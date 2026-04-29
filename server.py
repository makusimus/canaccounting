#!/usr/bin/env python3
"""CanAccounting Processor Backend v2"""
import csv, os, json, sys
from datetime import datetime
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
# replaced cgi import

# ==================== LOGIC ====================
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
ROOT = os.path.dirname(os.path.abspath(__file__))
OVERRIDE_FILE = os.path.join(ROOT, 'overrides.json')

def load_overrides():
    try:
        if os.path.exists(OVERRIDE_FILE):
            with open(OVERRIDE_FILE, 'r') as f: return json.load(f)
    except: pass
    return {}

def save_overrides(ov):
    with open(OVERRIDE_FILE, 'w') as f: json.dump(ov, f, indent=2)

def nd(d):
    d=str(d).strip().strip('"')
    for f in ['%Y-%m-%d','%m/%d/%Y','%m/%d/%y','%b %d,%Y','%b %d,%y','%b %d, %Y','%b %d, %y','%B %d,%Y','%B %d,%y']:
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
    lines=text.strip().split('\n')
    if not lines: return []
    h=[x.strip().strip('"') for x in lines[0].split(',')]
    rows=[]
    for line in lines[1:]:
        if not line.strip(): continue
        vals=line.split(',')
        row={}
        for i,k in enumerate(h):
            row[k]=vals[i].strip().strip('"') if i<len(vals) else ''
        rows.append(row)
    return rows

def process_all(files_data, master_spent_csv=None, master_funding_csv=None):
    overrides = load_overrides()
    spent, funding, excl = [], [], 0
    
    def adds(b,d,det,a):
        c=catf(det,SR,overrides) or 'Other'
        spent.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    def addf(b,d,det,a):
        c=catf(det,FR,overrides) or 'Other income'
        funding.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    
    if master_spent_csv:
        for r in parse_csv(master_spent_csv):
            r['_master']=True; spent.append(r)
    if master_funding_csv:
        for r in parse_csv(master_funding_csv):
            r['_master']=True; funding.append(r)
    
    for fname, text in files_data.items():
        fn=fname.lower()
        if 'simplii' in fn and 'debit' in fn: bt='simplii-debit'
        elif 'simplii' in fn and 'credit' in fn: bt='simplii-credit'
        elif 'rogers' in fn: bt='rogers-credit'
        elif 'scotia' in fn and 'debit' in fn: bt='scotia-debit'
        elif 'scotia' in fn and 'credit' in fn: bt='scotia-credit'
        else: continue
        
        rows=parse_csv(text)
        if not rows: continue
        bn={'simplii-debit':'Simplii Debit','simplii-credit':'Simplii Credit','scotia-debit':'Scotia Debit','scotia-credit':'Scotia Credit','rogers-credit':'Rogers Credit'}[bt]
        
        if bt=='simplii-debit':
            for row in rows:
                d=nd(row.get('Date',''));det=(row.get('Transaction Details','') or row.get('Description','')).strip()
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                if out:
                    if any(k in det.upper() for k in ['VISA SIMPLII','MASTERCARD ROGERS','FULFILL REQ MAKSYM']): excl+=1; continue
                    adds('Simplii Debit',d,det,out)
                if inn:
                    if 'RECEIVE MAKSYM' in det.upper(): excl+=1; continue
                    if 'RETAIL PURCHASE RETURN COSTCO' in det.upper(): adds('Simplii Debit',d,det,-inn)
                    elif catf(det,FR): addf('Simplii Debit',d,det,inn)
                    else: addf('Simplii Debit',d,det,inn)
        
        elif bt=='simplii-credit':
            for row in rows:
                d=nd(row.get('Date',''));det=(row.get('Transaction Details','') or row.get('Description','')).strip()
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                card=str(row.get('Credit Card','') or row.get(' Credit Card ','') or '').strip()
                sfx=f' | Card *{card[-4:]}' if len(card)>=4 else ''
                if 'PAYMENT THANK' in det.upper() or 'PAIEMENT' in det.upper(): excl+=1; continue
                if out: adds('Simplii Credit',d,det+sfx,out)
                if inn: adds('Simplii Credit',d,det+sfx,-inn)
        
        elif bt=='scotia-debit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip();d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if any(k in det.upper() for k in ['PEMBINA TRAILS','CUSTOMER TRANSFER DR','MB-CREDIT CARD','LOC PAY']): excl+=1; continue
                if amt<0: adds('Scotia Debit',d,det,abs(amt))
                else: addf('Scotia Debit',d,det,amt)
        
        elif bt=='scotia-credit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip();d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if 'payment from -' in det.lower(): excl+=1; continue
                adds('Scotia Credit',d,det,abs(amt))
        
        elif bt=='rogers-credit':
            for row in rows:
                keys=list(row.keys())
                det=str(row.get('Description','') or row.get('Merchant Name','') or (row[keys[1]] if len(keys)>1 else '')).strip()
                d=nd(str(row.get('Date','')));amt_field=row.get('Amount','') or (row[keys[3]] if len(keys)>3 else '')
                amt=pa(amt_field)
                if amt is None: continue
                if 'payment, thank you' in det.lower(): excl+=1; continue
                adds('Rogers Credit',d,det,abs(amt))
    
    spent.sort(key=lambda t:t.get('Date','') or '')
    funding.sort(key=lambda t:t.get('Date','') or '')
    return spent, funding, excl

# ==================== HTTP SERVER ====================
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
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
        else:
            self.send_response(404); self.end_headers()
    
    def do_POST(self):
        if self.path == '/process':
            form = parse_multipart(self.rfile, self.headers)
            files_data = {}
            master_spent = master_funding = None
            for field_name, data in form.items():
                if isinstance(data, bytes):
                    decoded = data.decode('utf-8', errors='replace')
                    if field_name == 'masterSpent': master_spent = decoded
                    elif field_name == 'masterFunding': master_funding = decoded
                    else: files_data[field_name] = decoded
            spent, funding, excl = process_all(files_data, master_spent, master_funding)
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({
                'spent': spent, 'funding': funding, 'excluded': excl,
                'overrides': load_overrides()
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

if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    server = HTTPServer(('127.0.0.1', port), Handler)
    print(f'CanAccounting server on http://127.0.0.1:{port}')
    print(f'Overrides stored in: {OVERRIDE_FILE}')
    server.serve_forever()
import re, sys

def parse_multipart(rfile, headers):
    """Parse multipart/form-data without cgi module"""
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
            result[field_name] = data
        else:
            result[field_name] = data.decode('utf-8', errors='replace')
    return result
