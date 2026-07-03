import { Conversation } from 'https://esm.sh/@elevenlabs/client';
const AGENT='agent_1401kph0cebdfd8bse7t79byespf';
let vc2=null,tc2=null,muted2=false;

const orb2=document.getElementById('orb2');
const st2=document.getElementById('st2');
const bCall2=document.getElementById('bCall2');
const bMute2=document.getElementById('bMute2');
const bEnd2=document.getElementById('bEnd2');
const bChat2=document.getElementById('bChat2');
const chatOverlay2=document.getElementById('chatOverlay2');
const cMsgs2=document.getElementById('cMsgs2');
const cIn2=document.getElementById('cIn2');
const cSend2=document.getElementById('cSend2');
const cDot2=document.getElementById('cDot2');

if(orb2)orb2.onclick=()=>{if(!vc2&&!tc2)startVoice2();};
if(bCall2)bCall2.onclick=()=>startVoice2();
if(bEnd2)bEnd2.onclick=()=>doEnd2();
if(bMute2)bMute2.onclick=()=>doMute2();
if(bChat2)bChat2.onclick=()=>toggleChat2();
if(cSend2)cSend2.onclick=()=>sendText2();
if(cIn2)cIn2.addEventListener('keydown',e=>{if(e.key==='Enter')sendText2();});

function setStatus2(t,err=false){if(st2){st2.textContent=t;st2.className='va-status'+(err?' err':'');}}
function setVoiceUI2(on){
  if(orb2)orb2.classList.toggle('active',on);
  if(bCall2)bCall2.style.display=on?'none':'flex';
  if(bMute2)bMute2.style.display=on?'flex':'none';
  if(bEnd2)bEnd2.style.display=on?'flex':'none';
}
function addMsg2(txt,who){
  const ti=cMsgs2.querySelector('.typing');if(ti&&who==='a')ti.remove();
  const d=document.createElement('div');d.className='msg '+who;d.textContent=txt;
  cMsgs2.appendChild(d);cMsgs2.scrollTop=cMsgs2.scrollHeight;
}
function setOnline2(on){if(cDot2){cDot2.style.background=on?'#4caf50':'#888';cDot2.style.boxShadow=on?'0 0 6px #4caf50':'none';}}

async function startVoice2(){
  if(vc2||tc2){doEnd2();return;}
  if(bCall2)bCall2.disabled=true;
  setStatus2('Connecting…');
  try{await navigator.mediaDevices.getUserMedia({audio:true});}
  catch(e){setStatus2('Mic denied',true);if(bCall2)bCall2.disabled=false;return;}
  try{
    vc2=await Conversation.startSession({
      agentId:AGENT,
      onConnect:()=>{setVoiceUI2(true);setStatus2('🎙 Listening…');if(bCall2)bCall2.disabled=false;},
      onDisconnect:()=>{vc2=null;setVoiceUI2(false);setStatus2('Call ended');muted2=false;if(bCall2)bCall2.disabled=false;},
      onError:(e)=>{setStatus2('Error: '+(e?.message||String(e)),true);vc2=null;setVoiceUI2(false);if(bCall2)bCall2.disabled=false;},
      onMessage:(msg)=>{if(msg.source==='ai'&&msg.message)addMsg2(msg.message,'a');},
      onModeChange:(m)=>{if(!vc2)return;setStatus2(m.mode==='speaking'?'🔊 Agent speaking…':'🎙 Listening…');},
    });
  }catch(e){setStatus2('Connection failed: '+(e?.message||e),true);if(bCall2)bCall2.disabled=false;vc2=null;}
}
async function doEnd2(){
  if(vc2){await vc2.endSession();vc2=null;}
  if(tc2){await tc2.endSession();tc2=null;}
  setVoiceUI2(false);setStatus2('Tap orb or press Start call');muted2=false;setOnline2(false);
}
function doMute2(){
  if(!vc2)return;muted2=!muted2;vc2.setMicMuted(muted2);
  if(bMute2)bMute2.classList.toggle('on',muted2);
  if(document.getElementById('muteLabel2'))document.getElementById('muteLabel2').textContent=muted2?'Unmute':'Mute';
}
async function toggleChat2(){
  const isOpen=chatOverlay2.classList.contains('open');
  if(isOpen){chatOverlay2.classList.remove('open');if(bChat2)bChat2.classList.remove('on');return;}
  chatOverlay2.classList.add('open');if(bChat2)bChat2.classList.add('on');
  if(!tc2)await startText2();
}
async function startText2(){
  addMsg2('Connecting to agent…','sys');setOnline2(false);
  try{
    tc2=await Conversation.startSession({
      agentId:AGENT,overrides:{conversation:{textOnly:true}},
      onConnect:()=>{const s=cMsgs2.querySelector('.msg.sys');if(s)s.remove();setOnline2(true);addMsg2('Hello! How can I help?','a');},
      onDisconnect:()=>{tc2=null;setOnline2(false);addMsg2('Chat ended.','sys');},
      onError:(e)=>{addMsg2('Error: '+(e?.message||e),'sys');tc2=null;setOnline2(false);},
      onMessage:(msg)=>{if(msg.source==='ai'&&msg.message)addMsg2(msg.message,'a');},
    });
  }catch(e){addMsg2('Could not connect: '+e,'sys');tc2=null;}
}
async function sendText2(){
  const txt=cIn2.value.trim();if(!txt)return;
  cIn2.value='';addMsg2(txt,'u');
  const t=document.createElement('div');t.className='typing';t.innerHTML='<span></span><span></span><span></span>';cMsgs2.appendChild(t);cMsgs2.scrollTop=cMsgs2.scrollHeight;
  if(!tc2)await startText2();
  if(tc2){try{await tc2.sendUserMessage(txt);}catch(e){const ti=cMsgs2.querySelector('.typing');if(ti)ti.remove();addMsg2('Failed to send.','sys');}}
}
