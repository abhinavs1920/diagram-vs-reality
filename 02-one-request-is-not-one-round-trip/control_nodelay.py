"""
Diagram vs Reality - Episode 02 follow-up control.

Question: does the client socket's TCP_NODELAY setting change the cold-request
latency recorded in run.py / results.json?

Method: identical paired design as run.py, with the two variants interleaved
per pair - default socket (Nagle on) vs TCP_NODELAY=1 set before connect.
5 pairs per variant. TLS version and cipher recorded per connection.
Host: example.com (real network). DNS resolved once, excluded from timings.

Writes results_control.json in the current directory.
"""
import socket, ssl, time, json, statistics

HOST, PORT = 'example.com', 443
CTX = ssl.create_default_context()

t0 = time.perf_counter()
IP = socket.getaddrinfo(HOST, PORT, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
DNS_MS = (time.perf_counter() - t0) * 1000

REQ_KEEP  = b'GET / HTTP/1.1\r\nHost: example.com\r\nConnection: keep-alive\r\n\r\n'
REQ_CLOSE = b'GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n'

class Buf:
    def __init__(self, s):
        self.s = s
        self.b = b''
    def _more(self):
        chunk = self.s.recv(65536)
        if not chunk:
            raise ConnectionError('closed mid-response')
        self.b += chunk
    def need(self, n):
        while len(self.b) < n:
            self._more()
    def line(self):
        while b'\r\n' not in self.b:
            self._more()
        ln, _, self.b = self.b.partition(b'\r\n')
        return ln
    def take(self, n):
        self.need(n)
        out, self.b = self.b[:n], self.b[n:]
        return out

def read_response(s):
    t = time.perf_counter()
    buf = Buf(s)
    status = buf.line().decode()
    if ' 200' not in status:
        raise AssertionError(f'status: {status}')
    headers = {}
    while True:
        ln = buf.line().decode()
        if ln == '':
            break
        k, _, v = ln.partition(': ')
        headers[k.strip().lower()] = v.strip()
    if 'content-length' in headers:
        buf.take(int(headers['content-length']))
    elif headers.get('transfer-encoding', '').lower() == 'chunked':
        while True:
            size = int(buf.line().decode().split(';')[0].strip(), 16)
            if size == 0:
                while buf.line() != b'':
                    pass
                break
            buf.take(size)
            buf.take(2)
    else:
        raise AssertionError(f'cannot frame: {headers}')
    return (time.perf_counter() - t) * 1000

def new_conn(nodelay):
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.settimeout(10)
    if nodelay:
        raw.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    t = time.perf_counter()
    raw.connect((IP, PORT))
    tcp_ms = (time.perf_counter() - t) * 1000
    t2 = time.perf_counter()
    s = CTX.wrap_socket(raw, server_hostname=HOST)
    tls_ms = (time.perf_counter() - t2) * 1000
    return s, tcp_ms, tls_ms, s.version(), s.cipher()[0]

def run_pair(nodelay, pair_no):
    t = time.perf_counter()
    s, tcp_ms, tls_ms, ver, cipher = new_conn(nodelay)
    hs = (time.perf_counter() - t) * 1000
    s.sendall(REQ_CLOSE)
    cold_req = read_response(s)
    cold_total = (time.perf_counter() - t) * 1000
    s.close()
    time.sleep(0.3)

    t = time.perf_counter()
    s2, _, _, _, _ = new_conn(nodelay)
    warm_hs = (time.perf_counter() - t) * 1000
    s2.sendall(REQ_KEEP)
    w1_req = read_response(s2)
    warm_r1_total = (time.perf_counter() - t) * 1000
    t3 = time.perf_counter()
    s2.sendall(REQ_CLOSE)
    w2_req = read_response(s2)
    warm_r2 = (time.perf_counter() - t3) * 1000
    s2.close()

    return {'pair': pair_no, 'nodelay': nodelay, 'tls_version': ver, 'cipher': cipher,
            'cold': {'tcp_ms': round(tcp_ms,1), 'tls_ms': round(tls_ms,1),
                     'handshake_ms': round(hs,1), 'request_ms': round(cold_req,1),
                     'total_ms': round(cold_total,1)},
            'warm': {'handshake_ms': round(warm_hs,1),
                     'req1_total_ms': round(warm_r1_total,1),
                     'req2_request_ms': round(w2_req,1)}}

pairs = []
for i in range(5):
    for nd in (False, True):
        try:
            pairs.append(run_pair(nd, i + 1))
        except Exception as e:
            pairs.append({'pair': i + 1, 'nodelay': nd, 'error': str(e)})
        time.sleep(0.4)

def med(pairs, nodelay, section, key):
    vals = [p[section][key] for p in pairs if p.get('nodelay') == nodelay and section in p]
    return round(statistics.median(vals), 1) if vals else None

out = {
    'setup': f'CONTROL: same paired design as v2, interleaved variants; default (Nagle on) vs TCP_NODELAY=1 before connect; host example.com ({IP}); DNS {DNS_MS:.1f}ms excluded; 5 pairs per variant',
    'pairs': pairs,
    'summary': {
        'nagle_default': {
            'cold_handshake_ms': med(pairs, False, 'cold', 'handshake_ms'),
            'cold_request_ms': med(pairs, False, 'cold', 'request_ms'),
            'cold_total_ms': med(pairs, False, 'cold', 'total_ms'),
            'warm_req2_ms': med(pairs, False, 'warm', 'req2_request_ms'),
            'tls_version': next((p['tls_version'] for p in pairs if p.get('nodelay') == False and 'tls_version' in p), None),
        },
        'nodelay': {
            'cold_handshake_ms': med(pairs, True, 'cold', 'handshake_ms'),
            'cold_request_ms': med(pairs, True, 'cold', 'request_ms'),
            'cold_total_ms': med(pairs, True, 'cold', 'total_ms'),
            'warm_req2_ms': med(pairs, True, 'warm', 'req2_request_ms'),
            'tls_version': next((p['tls_version'] for p in pairs if p.get('nodelay') == True and 'tls_version' in p), None),
        },
    },
}
print(json.dumps(out, indent=2))
with open('results_control.json', 'w') as f:
    json.dump(out, f, indent=2)
