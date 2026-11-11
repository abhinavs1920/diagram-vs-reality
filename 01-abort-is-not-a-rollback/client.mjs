// Local client. Built-in Node fetch, no dependencies.
const [url, mode, trial, key, epoch] = process.argv.slice(2);
const events=[];
function log(event, extra={}) { events.push({ms:Date.now()-Number(epoch),event,trial,...extra}); }
async function send(label, abort) {
 const c = new AbortController();
 const timer=abort ? setTimeout(()=>{log('client_abort_sent',{request:label}); c.abort();},100) : null;
 log('client_request_started',{request:label});
 try {
  const r=await fetch(url,{method:'POST',signal:c.signal,headers:{'content-type':'application/json',...(key ? {'idempotency-key':key} : {})},body:JSON.stringify({trial,request:label})});
  const data=await r.json(); log('client_response',{request:label,status:r.status,...data});
 } catch(e) { log('client_error',{request:label,name:e.name}); }
 finally { if(timer) clearTimeout(timer); }
}
await send('first',mode!=='control');
if(mode==='retry') await send('retry',false);
console.log(JSON.stringify(events));
