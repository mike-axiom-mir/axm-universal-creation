'use strict';

const Flow=require('./upgrade-program/creative-flow');
const MAX_STDIN=64*1024*1024;
let chunks=[],bytes=0;
process.stdin.on('data',(chunk)=>{bytes+=chunk.length;if(bytes>MAX_STDIN){process.stderr.write('creative flow request exceeds 64 MiB\n');process.exitCode=2;process.stdin.pause();return;}chunks.push(chunk);});
process.stdin.on('end',()=>{if(process.exitCode)return;try{const text=Buffer.concat(chunks).toString('utf8'),request=text.trim()?JSON.parse(text):{};const result=Flow.run(request);process.stdout.write(JSON.stringify(result));}catch(error){process.stderr.write(String(error&&error.stack||error)+'\n');process.exitCode=1;}});
