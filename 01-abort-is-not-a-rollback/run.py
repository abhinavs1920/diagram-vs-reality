"""Independent local toy experiment: client abort is not application cancellation.
Python standard library + Node 18+. Binds only to 127.0.0.1.
Server intentionally has no cancellation propagation. Never use as production code.
"""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import datetime, json, sqlite3, subprocess, threading, time, platform
ROOT=Path(__file__).resolve().parent
DB=ROOT/'orders.sqlite'
if DB.exists(): DB.unlink()
with sqlite3.connect(DB) as c:
 c.execute('CREATE TABLE orders(id INTEGER PRIMARY KEY, trial TEXT NOT NULL, request TEXT NOT NULL, idem_key TEXT UNIQUE)')
epoch=time.time_ns()//1_000_000
trace=[]; lock=threading.Lock()
def log(event,**kw):
 with lock: trace.append({'ms':time.time_ns()//1_000_000-epoch,'event':event,**kw})
class Handler(BaseHTTPRequestHandler):
 def log_message(self,*args): pass
 def do_POST(self):
  if self.path!='/orders': self.send_error(404); return
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  trial,request=body['trial'],body['request']
  key=self.headers.get('Idempotency-Key')
  log('server_received',trial=trial,request=request,key=key)
  # Controlled local delay before commit, not simulated network latency.
  time.sleep(.4)
  with sqlite3.connect(DB,timeout=5) as c:
   cur=c.execute('INSERT INTO orders(trial,request,idem_key) VALUES (?,?,?) ON CONFLICT(idem_key) DO NOTHING',(trial,request,key))
   created=cur.rowcount==1
   row=c.execute('SELECT id FROM orders WHERE idem_key=?',(key,)).fetchone() if key else (cur.lastrowid,)
   oid=row[0]
  log('database_committed' if created else 'duplicate_suppressed',trial=trial,request=request,order_id=oid)
  data=json.dumps({'order_id':oid,'created':created}).encode()
  try:
   self.send_response(200); self.send_header('Content-Type','application/json'); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
   log('server_response_written',trial=trial,request=request)
  except (BrokenPipeError,ConnectionResetError): log('server_response_connection_closed',trial=trial,request=request)
server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/orders'
cases=[('control','control',False),('abort_only','abort',False),('abort_then_retry','retry',False),('same_key_retry','retry',True)]
results=[]
for case,mode,keyed in cases:
 for i in range(1,6):
  trial=f'{case}-{i}'
  out=subprocess.run(['node',str(ROOT/'client.mjs'),url,mode,trial,trial if keyed else '',str(epoch)],text=True,capture_output=True,check=True)
  with lock: trace.extend(json.loads(out.stdout))
  # Allow the aborted handler to finish before reading the database.
  time.sleep(.55)
  with sqlite3.connect(DB) as c: rows=c.execute('SELECT id,request,idem_key FROM orders WHERE trial=? ORDER BY id',(trial,)).fetchall()
  results.append({'case':case,'trial':trial,'rows':len(rows),'orders':rows})
server.shutdown(); server.server_close()
trace.sort(key=lambda e:e['ms'])
summary=[]
for case,_,_ in cases:
 rs=[r for r in results if r['case']==case]
 summary.append({'case':case,'trials':len(rs),'rows_per_trial':[r['rows'] for r in rs]})
# Assertions verify the limited, deliberately configured outcome, not all stacks.
assert all(r['rows']==(2 if r['case']=='abort_then_retry' else 1) for r in results)
for r in results:
 events=[e for e in trace if e.get('trial')==r['trial']]
 if r['case']!='control':
  abort=next(e['ms'] for e in events if e['event']=='client_abort_sent')
  commit=next(e['ms'] for e in events if e['event']=='database_committed')
  assert commit>abort
  assert any(e['event']=='client_error' and e.get('name')=='AbortError' for e in events)
report={'run_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'python':platform.python_version(),'node':subprocess.check_output(['node','--version'],text=True).strip(),'setup':{'transport':'HTTP/1.1 client to local Python HTTP server (server responds HTTP/1.0)','bind':'127.0.0.1 only','abort_after_ms':100,'handler_delay_before_commit_ms':400,'repetitions_per_case':5,'cancellation_propagation':'none','idempotency':'SQLite UNIQUE constraint on supplied key; durable within this local database'},'summary':summary,'results':results,'trace':trace}
(ROOT/'results.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'run_utc':report['run_utc'],'summary':summary,'first_aborted_trace':[e for e in trace if e.get('trial')=='abort_only-1']},indent=2))
