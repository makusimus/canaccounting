#!/usr/bin/env python3
"""CanAccounting processor - run on command line, outputs CSVs"""
import csv, openpyxl, os, sys, json, subprocess
from datetime import datetime
from collections import Counter
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse, cgi, io, tempfile

def nd(d):
    d=d.strip().strip('"')
    for f in ['%Y-%m-%d','%m/%d/%Y','%m/%d/%y','%b %d,%Y','%b %d,%y','%b %d, %Y','%b %d, %y','%B %d,%Y','%B %d,%y']:
        try: return datetime.strptime(d,f).strftime('%Y-%m-%d')
        except: pass
    return d[:10]

def pa(s):
    if not s or not s.strip(): return None
    s=s.strip().strip('"').replace('$','').replace(',','').replace(' ','')
    try: return float(s)
    except: return None

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
(['free interac e-transfer','withdrawal — free interac'],'Liubov transfer'),
(['vladd cars','christa cgi','rbc convention','salarmy'],'Other'),
]

FR=[
(['payroll deposit cgi'],'Salary'),(['interac e-transfer receive liubov','e-transfer receive liubov'],'Liubov transfer'),
(['interest'],'Other income'),(['cheque image deposit'],'Other income'),(['eft credit'],'Other income'),
(['deposit mpi'],'Other income'),(['cash back'],'Other income'),
(['remise carbone','carbon rebate','ind all ac-est','tax refund','no fee cash reward'],'Other income'),
(['initial balance'],'Initial balance 2025'),
]

def catf(details, rules):
    dl=details.lower()
    for keywords,cat in rules:
        if any(k.lower() in dl for k in keywords): return cat
    return None

def process_files(files_data, master_spent_csv=None, master_funding_csv=None):
    """Main processing function - takes file contents as bytes dict, returns spent/funding CSVs"""
    spent = []
    funding = []
    excl = 0
    
    def adds(b,d,det,a):
        c=catf(det,SR) or 'Other'
        spent.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    def addf(b,d,det,a):
        c=catf(det,FR) or 'Other income'
        funding.append({'Bank':b,'Date':d,'Transaction Details':det,'Category':c,'Amount':a})
    
    def parse_csv(text):
        lines=text.split('\n')
        if not lines: return []
        h=[x.strip().strip('"') for x in lines[0].split(',')]
        rows=[]
        for line in lines[1:]:
            if not line.strip(): continue
            vals=line.split(',')
            row={}
            for i,k in enumerate(h):
                if i<len(vals): row[k]=vals[i].strip().strip('"')
                else: row[k]=''
            rows.append(row)
        return rows
    
    # Load masters
    if master_spent_csv:
        for r in parse_csv(master_spent_csv):
            r['_master']=True
            spent.append(r)
    if master_funding_csv:
        for r in parse_csv(master_funding_csv):
            r['_master']=True
            funding.append(r)
    
    for fname, content in files_data.items():
        fname_lower = fname.lower()
        text = content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content
        
        # Detect bank from filename
        if 'simplii' in fname_lower and 'debit' in fname_lower: bank_type = 'simplii-debit'
        elif 'simplii' in fname_lower and 'credit' in fname_lower: bank_type = 'simplii-credit'
        elif 'rogers' in fname_lower: bank_type = 'rogers-credit'
        elif 'scotia' in fname_lower and 'debit' in fname_lower: bank_type = 'scotia-debit'
        elif 'scotia' in fname_lower and 'credit' in fname_lower: bank_type = 'scotia-credit'
        else: continue
        
        rows = parse_csv(text)
        if not rows: continue
        bn = {'simplii-debit':'Simplii Debit','simplii-credit':'Simplii Credit','scotia-debit':'Scotia Debit','scotia-credit':'Scotia Credit','rogers-credit':'Rogers Credit'}[bank_type]
        
        if bank_type == 'simplii-debit':
            for row in rows:
                d=nd(row.get('Date',''));det=row.get('Transaction Details','') or row.get('Description','')
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                if out:
                    if any(k in det.upper() for k in ['VISA SIMPLII','MASTERCARD ROGERS','FULFILL REQ MAKSYM']): excl+=1; continue
                    adds('Simplii Debit',d,det,out)
                if inn:
                    if 'RECEIVE MAKSYM' in det.upper(): excl+=1; continue
                    if 'RETAIL PURCHASE RETURN COSTCO' in det.upper(): adds('Simplii Debit',d,det,-inn)
                    elif catf(det,FR): addf('Simplii Debit',d,det,inn)
                    else: addf('Simplii Debit',d,det,inn)
        
        elif bank_type == 'simplii-credit':
            for row in rows:
                d=nd(row.get('Date',''));det=row.get('Transaction Details','') or row.get('Description','')
                out=pa(row.get('Funds Out',''));inn=pa(row.get('Funds In',''))
                card=str(row.get('Credit Card','') or row.get(' Credit Card ','') or '').strip()
                sfx=f' | Card *{card[-4:]}' if len(card)>=4 else ''
                if 'PAYMENT THANK' in det.upper() or 'PAIEMENT' in det.upper(): excl+=1; continue
                if out: adds('Simplii Credit',d,det+sfx,out)
                if inn: adds('Simplii Credit',d,det+sfx,-inn)
        
        elif bank_type == 'scotia-debit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip()
                d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if any(k in det.upper() for k in ['PEMBINA TRAILS','CUSTOMER TRANSFER DR','MB-CREDIT CARD','LOC PAY']): excl+=1; continue
                if amt<0: adds('Scotia Debit',d,det,abs(amt))
                else: addf('Scotia Debit',d,det,amt)
        
        elif bank_type == 'scotia-credit':
            for row in rows:
                desc=str(row.get('Description',''));sub=str(row.get('Sub-description',''))
                det=f'{desc} — {sub}'.strip()
                d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','')))
                if amt is None: continue
                if 'payment from -' in det.lower(): excl+=1; continue
                adds('Scotia Credit',d,det,abs(amt))
        
        elif bank_type == 'rogers-credit':
            for row in rows:
                det=str(row.get('Description','') or row.get('Merchant Name','') or list(row.values())[1] if len(row)>1 else '')
                d=nd(str(row.get('Date','')));amt=pa(str(row.get('Amount','') or row.get(list(row.keys())[3],'') if len(row)>3 else ''))
                if amt is None: continue
                if 'payment, thank you' in det.lower(): excl+=1; continue
                adds('Rogers Credit',d,det,abs(amt))
    
    spent.sort(key=lambda t:t.get('Date','') or '')
    funding.sort(key=lambda t:t.get('Date','') or '')
    return spent, funding, excl

class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/process':
            content_type = self.headers.get('Content-Type', '')
            if 'multipart/form-data' in content_type:
                form = cgi.FieldStorage(fp=self.rfile, headers=self.headers, environ={'REQUEST_METHOD':'POST','CONTENT_TYPE':content_type})
            else:
                length = int(self.headers.get('Content-Length', 0))
                data = json.loads(self.rfile.read(length).decode('utf-8'))
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(json.dumps({'error':'JSON not supported, use multipart'}).encode())
                return
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(b'<html><body><h1>CanAccounting Processor</h1><p>Upload files via POST /process with multipart/form-data</p></body></html>')

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--server':
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 8765
        server = HTTPServer(('127.0.0.1', port), Handler)
        print(f'Server running on http://127.0.0.1:{port}')
        server.serve_forever()
    else:
        print('CanAccounting Processor')
        print('Usage: python3 parse_all.py [--server PORT]')
