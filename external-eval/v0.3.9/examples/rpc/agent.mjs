// Complete JavaScript candidate generator for the Python-hosted RPC example.
// TEST ONLY: no language model or provider credentials.
import readline from 'node:readline';
const lines=readline.createInterface({input:process.stdin});
for await(const line of lines){
 let q;try{
  q=JSON.parse(line);if(q.protocol!=='rveval.rpc.v2')throw Error('version');
  let result;
  if(q.op==='describe')result={name:'JavaScript arithmetic agent',version:'test-only-v2',test_only:true};
  else if(q.op==='reset')result={reset:true};
  else if(q.op==='act')result={candidate:q.payload.task.request_type==='stateful'?
    {kind:'tool_call',name:'increment',arguments:{n:1}}:
    {kind:'final_answer',content:q.payload.task.x+q.payload.task.y}};
  else throw Error('unsupported');
  console.log(JSON.stringify({protocol:'rveval.rpc.v2',request_id:q.request_id,ok:true,result}));
 }catch(e){console.log(JSON.stringify({protocol:'rveval.rpc.v2',request_id:q?.request_id??null,ok:false,error:{category:'UNSUPPORTED',code:'REFERENCE_WORKER_ERROR'}}));}
}
