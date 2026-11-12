"""
Diagram vs Reality - Day 2, v2 (corrected measurement)
Diagram: "one HTTPS request = one round trip"
Reality: a cold HTTPS request pays TCP + TLS handshake before the HTTP
request bytes leave.

Method (real network, raw sockets + ssl, no frameworks):
- DNS resolved once up front, timed separately, IP reused (no DNS in timings).
- HTTP/1.1 proper framing: headers parsed to CRLFCRLF, status validated 200,
  body read by Content-Length or chunked transfer-encoding.
- 5 PAIRED trials, interleaved: each pair = (A) cold request on a fresh
  connection, then (B) two requests on one fresh connection.
- Definitions, each from its own t0:
    handshake_ms   = TCP connect + TLS wrap (no DNS)
    request_ms     = send -> full validated response (headers + body)
    cold_total_ms  = handshake + request (fresh conn, Connection: close)
    warm_req1_total_ms = handshake + request 1 (fresh conn, keep-alive)
    warm_req2_ms   = request 2 on the SAME conn (no handshake)
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
    def need(self, n):
        while len(self.b) < n:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError('connection closed mid-response')
            self.b += chunk
    def line(self):
        while b'\r\n' not in self.b:
            chunk = self.s.recv(65536)
            if not chunk:
                raise ConnectionError('connection closed mid-line')
            self.b += chunk
        ln, _, self.b = self.b.partition(b'\r\n')
        return ln
    def take(self, n):
        self.need(n)
        out, self.b = self.b[:n], self.b[n:]
        return out

def read_response(s):
    """Read one full HTTP/1.1 response. Returns (status, header_ms, total_ms)."""
    t = time.perf_counter()
    buf = Buf(s)
    status = buf.line().decode()
    if ' 200' not in status:
        raise AssertionError(f'unexpected status: {status}')
    headers = {}
    while True:
        ln = buf.line().decode()
        if ln == '':
            break
        k, _, v = ln.partition(': ')
        headers[k.strip().lower()] = v.strip()
    header_ms = (time.perf_counter() - t) * 1000
    if 'content-length' in headers:
        buf.take(int(headers['content-length']))
    elif headers.get('transfer-encoding', '').lower() == 'chunked':
        while True:
            size = int(buf.line().decode().split(';')[0].strip(), 16)
            if size == 0:
                while buf.line() != b'':  # trailers
                    pass
                break
            buf.take(size)
            buf.take(2)  # trailing CRLF
    else:
        raise AssertionError(f'cannot frame response: {headers}')
    total_ms = (time.perf_counter() - t) * 1000
    return status, round(header_ms, 1), round(total_ms, 1)

def new_conn():
    t = time.perf_counter()
    raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    raw.settimeout(10)
    raw.connect((IP, PORT))
    tcp_ms = (time.perf_counter() - t) * 1000
    t2 = time.perf_counter()
    s = CTX.wrap_socket(raw, server_hostname=HOST)
    tls_ms = (time.perf_counter() - t2) * 1000
    return s, tcp_ms, tls_ms

pairs = []
for i in range(5):
    t = time.perf_counter()
    s, tcp_ms, tls_ms = new_conn()
    handshake_ms = (time.perf_counter() - t) * 1000
    s.sendall(REQ_CLOSE)
    _, cold_hdr_ms, cold_req_ms = read_response(s)
    cold_total_ms = (time.perf_counter() - t) * 1000
    s.close()
    time.sleep(0.3)

    t = time.perf_counter()
    s2, tcp2, tls2 = new_conn()
    warm_hs_ms = (time.perf_counter() - t) * 1000
    s2.sendall(REQ_KEEP)
    _, w1_hdr_ms, w1_req_ms = read_response(s2)
    warm_req1_total_ms = (time.perf_counter() - t) * 1000
    t3 = time.perf_counter()
    s2.sendall(REQ_CLOSE)
    _, w2_hdr_ms, w2_req_ms = read_response(s2)
    warm_req2_ms = (time.perf_counter() - t3) * 1000
    s2.close()

    pairs.append({
        'pair': i + 1,
        'cold': {'tcp_ms': round(tcp_ms, 1), 'tls_ms': round(tls_ms, 1),
                 'handshake_ms': round(handshake_ms, 1),
                 'request_ms': cold_req_ms, 'total_ms': round(cold_total_ms, 1)},
        'warm': {'handshake_ms': round(warm_hs_ms, 1),
                 'req1_total_ms': round(warm_req1_total_ms, 1),
                 'req1_request_ms': w1_req_ms,
                 'req2_request_ms': round(warm_req2_ms, 1)},
    })
    time.sleep(0.4)

def med(path):
    vals = []
    for p in pairs:
        v = p
        for k in path:
            v = v[k]
        vals.append(v)
    return round(statistics.median(vals), 1)

results = {
    'setup': 'real HTTPS to example.com (IP %s); DNS resolved once (%.1fms, excluded); raw sockets + ssl; HTTP/1.1 framing validated (status 200, content-length/chunked); 5 interleaved cold/warm pairs' % (IP, DNS_MS),
    'pairs': pairs,
    'summary': {
        'cold_handshake_ms': med(('cold', 'handshake_ms')),
        'cold_request_ms': med(('cold', 'request_ms')),
        'cold_total_ms': med(('cold', 'total_ms')),
        'warm_req1_total_ms': med(('warm', 'req1_total_ms')),
        'warm_req2_request_ms': med(('warm', 'req2_request_ms')),
    },
}
c = results['summary']
if c['warm_req2_request_ms']:
    results['summary']['cold_total_over_warm_req2'] = round(c['cold_total_ms'] / c['warm_req2_request_ms'], 1)
print(json.dumps(results, indent=2))
with open('results.json', 'w') as f:
    json.dump(results, f, indent=2)
