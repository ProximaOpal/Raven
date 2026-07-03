(function(){
  const KG_COLORS={atlas:'#81c675',cms:'#1e968a',lhcb:'#fcaf45',alice:'#14aae1',core:'#d9dbda'};
  const N8N_WEBHOOK='https://proximusraven.app.n8n.cloud/webhook/knowledge-ingester';
  const OUTER_R=266;
  const FAN_PER_HUB=14;
  let kgSelectedNodes=new Set(),kgActiveGlows=[],kgGlowIntensity=5;
  let kgIngestData=null;

  const KG_LABELS=[
    'RAW INGEST','TIER-0 BUF','SCHEMA VAL','INDEX SHRD','EDGE RELAY','SIGNAL MUX',
    'STREAM GATE','REPLICA A','REPLICA B','AUDIT LOG','HASH CHAIN','EVIDENCE PKG',
    'YOLO FILTER','QWEN-VL','BIOMETRIC','RF SENSOR','HITL QUEUE','ALERT DISP',
    'FORENSIC','TRAJECTORY','HOMOGRAPHY','CAM FEED','INCIDENT DB','SEARCH IDX',
    'TIER-1 ARC','TIER-2 ARC','COLD STORE','HOT CACHE','WRITE PATH','READ PATH',
    'MULTI-HOP','LATENCY','THROUGHPUT','DISCARD','TRIGGER-1','TRIGGER-2',
    'CMS VERTEX','ATLAS SCH','ALICE STR','LHCb SIG','CORE AGG','NA-EAST','EU-WEST',
    'APAC NODE','LATAM RING','AFRICA HUB','NORDIC EDGE','UK RELAY','BUFFER POOL'
  ];

  function kgGetOverlay(){return document.getElementById('kgOverlayLayer');}
  function kgGetSvg(){return document.getElementById('kgMainSvg');}

  function kgSvgPoint(e){
    const svg=kgGetSvg();if(!svg)return{x:0,y:0};
    const pt=svg.createSVGPoint();pt.x=e.clientX;pt.y=e.clientY;
    return pt.matrixTransform(svg.getScreenCTM().inverse());
  }
  function kgShowTip(e,title,sub,color){
    const tt=document.getElementById('kg-tooltip');
    if(!tt)return;
    document.getElementById('kgTtTitle').innerHTML=`<span class="tt-dot" style="background:${color}"></span>${title}`;
    document.getElementById('kgTtSub').textContent=sub;
    tt.classList.add('show');kgMoveTip(e);
  }
  function kgMoveTip(e){const tt=document.getElementById('kg-tooltip');if(!tt)return;tt.style.left=(e.clientX+14)+'px';tt.style.top=(e.clientY-10)+'px';}
  function kgHideTip(){const tt=document.getElementById('kg-tooltip');if(tt)tt.classList.remove('show');}

  function kgCreateGlow(x1,y1,x2,y2,color){
    const ol=kgGetOverlay();if(!ol)return null;
    const el=document.createElementNS('http://www.w3.org/2000/svg','path');
    el.style.fill='none';el.style.stroke=color;el.style.strokeWidth='1.8';
    el.style.filter=`drop-shadow(0 0 ${3*kgGlowIntensity/5}px ${color}) drop-shadow(0 0 ${8*kgGlowIntensity/5}px ${color})`;
    el.style.animation='glowPulse 1.4s ease-in-out infinite alternate';
    el.setAttribute('d',`M ${x1} ${y1} Q ${(x1+x2)/2-(y2-y1)*0.35} ${(y1+y2)/2+(x2-x1)*0.35} ${x2} ${y2}`);
    ol.appendChild(el);kgActiveGlows.push(el);return el;
  }
  function kgCreateRipple(x,y,color){
    const ol=kgGetOverlay();if(!ol)return;
    const el=document.createElementNS('http://www.w3.org/2000/svg','circle');
    el.setAttribute('cx',x);el.setAttribute('cy',y);el.setAttribute('r','0');
    el.style.fill='none';el.style.stroke=color;el.style.strokeWidth='1.5';
    el.style.animation='rippleOut .8s ease-out forwards';
    ol.appendChild(el);setTimeout(()=>el.remove(),900);
  }
  function kgCreateHubHL(cx,cy,color){
    const ol=kgGetOverlay();if(!ol)return;
    const el=document.createElementNS('http://www.w3.org/2000/svg','circle');
    el.setAttribute('cx',cx);el.setAttribute('cy',cy);el.setAttribute('r','9');
    el.style.fill='none';el.style.stroke=color;el.style.strokeWidth='3';
    el.style.filter=`drop-shadow(0 0 6px ${color})`;
    el.style.animation='nodeGlow 1.6s ease-in-out infinite';
    ol.appendChild(el);kgActiveGlows.push(el);
  }
  function kgClearOverlays(){
    kgActiveGlows.forEach(el=>{try{el.remove();}catch(e){}});
    kgActiveGlows=[];kgSelectedNodes.clear();
    const badge=document.getElementById('kgSelBadge');if(badge)badge.classList.remove('show');
  }
  function kgIlluminateHub(hubId,color){
    const hubEl=document.querySelector(`#kgNodeLayer circle[data-hub="${hubId}"][data-name]`);
    if(!hubEl)return;
    const hx=parseFloat(hubEl.getAttribute('cx')),hy=parseFloat(hubEl.getAttribute('cy'));
    kgCreateGlow(hx,hy,0,0,color);kgCreateHubHL(hx,hy,color);kgCreateRipple(hx,hy,color);
  }
  function kgUpdateBadge(){
    const badge=document.getElementById('kgSelBadge');if(!badge)return;
    if(kgSelectedNodes.size>0){badge.textContent=kgSelectedNodes.size+' SELECTED';badge.classList.add('show');}
    else{badge.classList.remove('show');}
  }

  function kgUpdateStats(data){
    if(!data)return;
    const stats=data.stats||data;
    document.querySelectorAll('[data-kg-stat]').forEach(el=>{
      const key=el.getAttribute('data-kg-stat');
      if(stats[key]!==undefined)el.textContent=stats[key];
    });
    const hud=document.getElementById('kgHud');
    if(hud&&data.message)hud.innerHTML=data.message;
  }

  function kgApplyIngestNodes(nodes){
    if(!nodes||!nodes.length)return;
    const layer=document.getElementById('kgNodeLayer');
    if(!layer)return;
    nodes.forEach((node,i)=>{
      const angle=(i/nodes.length)*Math.PI*2-Math.PI/2;
      const r=200;
      const cx=Math.cos(angle)*r, cy=Math.sin(angle)*r;
      const domain=node.domain||'core';
      const color=KG_COLORS[domain]||'#d9dbda';
      const hubId=node.id||'ing'+i;
      const g=document.createElementNS('http://www.w3.org/2000/svg','g');
      g.innerHTML=`<circle cx="${cx}" cy="${cy}" r="7.2" fill="#1a1a1a" stroke="${color}" stroke-width="2.4" data-hub="${hubId}" data-domain="${domain}" data-name="${node.name||hubId}" style="cursor:pointer;"/><circle cx="${cx}" cy="${cy}" r="3.6" fill="${color}" data-hub="${hubId}" data-domain="${domain}"/>`;
      layer.appendChild(g);
    });
  }

  async function kgFetchFromN8n(){
    const hud=document.getElementById('kgHud');
    const statusEl=document.getElementById('kgIngestStatus');
    if(statusEl)statusEl.textContent='Syncing…';
    if(hud)hud.innerHTML='Ingesting from <span>n8n webhook</span>…';
    try{
      const resp=await fetch(N8N_WEBHOOK,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({action:'fetch',source:'raven-soc',timestamp:new Date().toISOString()})
      });
      if(!resp.ok)throw new Error('HTTP '+resp.status);
      const data=await resp.json();
      kgIngestData=data;
      if(data.nodes)kgApplyIngestNodes(data.nodes);
      kgUpdateStats(data);
      if(statusEl){statusEl.textContent='Synced';statusEl.style.color='#81c675';}
      if(hud)hud.innerHTML='Data ingested from <span>n8n</span> · Click <span>nodes</span> to trace pathways';
      return data;
    }catch(err){
      console.warn('n8n webhook ingest failed:',err);
      if(statusEl){statusEl.textContent='Offline';statusEl.style.color='#fcaf45';}
      if(hud)hud.innerHTML='Webhook offline — using <span>cached graph</span> · Click <span>nodes</span> to trace';
      return null;
    }
  }

  async function kgPushToN8n(payload){
    try{
      await fetch(N8N_WEBHOOK,{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify(payload)
      });
    }catch(err){console.warn('n8n push failed:',err);}
  }

  function kgBuildGraphStructure(){
    const svg=kgGetSvg();if(!svg)return;
    const linkLayer=document.getElementById('kgLinkLayer');
    const fanLayer=document.getElementById('kgFanLayer');
    const labelLayer=document.getElementById('kgLabelLayer');
    if(!linkLayer||!fanLayer||!labelLayer)return;

    const hubs=[...document.querySelectorAll('#kgNodeLayer circle[data-hub][data-name]')];
    const seen=new Set();
    const hubData=[];
    hubs.forEach(h=>{
      const id=h.getAttribute('data-hub');
      if(seen.has(id))return;
      seen.add(id);
      hubData.push({
        id,
        cx:parseFloat(h.getAttribute('cx')),
        cy:parseFloat(h.getAttribute('cy')),
        domain:h.getAttribute('data-domain')||'core',
        color:KG_COLORS[h.getAttribute('data-domain')]||'#d9dbda'
      });
    });

    linkLayer.innerHTML='';
    hubData.forEach(h=>{
      const line=document.createElementNS('http://www.w3.org/2000/svg','line');
      line.setAttribute('x1','0');line.setAttribute('y1','0');
      line.setAttribute('x2',String(h.cx*0.92));line.setAttribute('y2',String(h.cy*0.92));
      line.setAttribute('stroke',h.color);line.setAttribute('stroke-width','1.1');
      line.setAttribute('opacity','.95');line.setAttribute('data-hub',h.id);
      linkLayer.appendChild(line);
    });

    fanLayer.innerHTML='';
    let fanIdx=0;
    hubData.forEach(h=>{
      const baseAng=Math.atan2(h.cy,h.cx);
      for(let f=0;f<FAN_PER_HUB;f++){
        const spread=(f-FAN_PER_HUB/2)*(Math.PI/180)*4.2;
        const ang=baseAng+spread;
        const ex=Math.cos(ang)*OUTER_R,ey=Math.sin(ang)*OUTER_R;
        const cpx=h.cx+(ex-h.cx)*0.55+(ey-h.cy)*0.12;
        const cpy=h.cy+(ey-h.cy)*0.55-(ex-h.cx)*0.12;
        const path=document.createElementNS('http://www.w3.org/2000/svg','path');
        path.setAttribute('d',`M ${h.cx} ${h.cy} Q ${cpx} ${cpy} ${ex} ${ey}`);
        path.setAttribute('stroke',h.color);
        path.setAttribute('class','kg-fan-line glow-active');
        path.style.animationDelay=(fanIdx*0.04)+'s';
        path.setAttribute('data-hub',h.id);
        fanLayer.appendChild(path);
        fanIdx++;
      }
    });

    labelLayer.innerHTML='';
    const labelCount=Math.min(KG_LABELS.length,72);
    for(let i=0;i<labelCount;i++){
      const ang=(i/labelCount)*Math.PI*2-Math.PI/2;
      const lx=Math.cos(ang)*OUTER_R,ly=Math.sin(ang)*OUTER_R;
      const rot=(ang*180/Math.PI)+90;
      const t=document.createElementNS('http://www.w3.org/2000/svg','text');
      t.setAttribute('x',String(lx));t.setAttribute('y',String(ly));
      t.setAttribute('transform',`rotate(${rot},${lx},${ly})`);
      t.setAttribute('text-anchor','middle');
      t.setAttribute('class','kg-circ-label');
      t.textContent=KG_LABELS[i%KG_LABELS.length];
      labelLayer.appendChild(t);
    }

    const ringLayer=svg.querySelector('.kg-ring-layer');
    if(ringLayer){
      [272,278,284].forEach(r=>{
        const c=document.createElementNS('http://www.w3.org/2000/svg','circle');
        c.setAttribute('cx','0');c.setAttribute('cy','0');c.setAttribute('r',String(r));
        c.setAttribute('class','kg-outer-ring');
        ringLayer.parentNode.insertBefore(c,ringLayer);
      });
    }
  }

  function kgStartAmbientGlow(){
    const lines=document.querySelectorAll('.kg-fan-line');
    lines.forEach((el,i)=>{
      el.classList.add('glow-active');
      el.style.animationDelay=(i*0.03)+'s';
    });
  }

  document.addEventListener('DOMContentLoaded',()=>{
    const nodeLayer=document.getElementById('kgNodeLayer');
    if(!nodeLayer)return;

    kgBuildGraphStructure();
    kgStartAmbientGlow();
    kgFetchFromN8n();

    const ingestBtn=document.getElementById('kg-btn-ingest');
    if(ingestBtn)ingestBtn.addEventListener('click',kgFetchFromN8n);

    nodeLayer.addEventListener('click',e=>{
      const ring=e.target.closest('[data-hub][data-name]');if(!ring)return;
      const hubId=ring.getAttribute('data-hub'),domain=ring.getAttribute('data-domain'),name=ring.getAttribute('data-name')||hubId.toUpperCase();
      const color=KG_COLORS[domain]||'#d9dbda';
      if(!e.shiftKey)kgClearOverlays();
      const p=kgSvgPoint(e);kgCreateRipple(p.x,p.y,color);
      kgIlluminateHub(hubId,color);kgSelectedNodes.add(hubId);kgUpdateBadge();
      kgPushToN8n({action:'node_select',hubId,domain,name,timestamp:new Date().toISOString()});
      const pi=document.getElementById('kgPanelInner');const panel=document.getElementById('kgInfoPanel');
      if(pi&&panel){
        const ingested=kgIngestData&&kgIngestData.nodes?kgIngestData.nodes.find(n=>(n.id||'')===hubId):null;
        pi.innerHTML=`<button style="position:absolute;top:14px;right:14px;background:#232323;border:none;border-radius:50%;width:28px;height:28px;color:#888;font-size:14px;cursor:pointer;display:flex;align-items:center;justify-content:center;" id="kgPC2">&#x2715;</button>
          <div style="font-size:9px;color:#fcaf45;letter-spacing:.8px;text-transform:uppercase;margin-bottom:6px;">HUB NODE · ${domain.toUpperCase()}</div>
          <div style="font-size:18px;font-weight:600;color:#f3f1ec;margin-bottom:12px;">${name}</div>
          <div style="display:inline-block;padding:3px 9px;border-radius:6px;font-size:10px;letter-spacing:.4px;margin-bottom:14px;background:${color}22;color:${color};border:1px solid ${color}44;">${domain.toUpperCase()} DOMAIN</div>
          ${ingested&&ingested.description?`<div style="font-size:11px;color:#a8a6a1;line-height:1.5;margin-bottom:14px;">${ingested.description}</div>`:''}
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px;">
            <div style="background:#1f1f1f;border-radius:8px;padding:10px;"><span style="font-size:20px;font-weight:700;color:#fff;display:block;">${ingested&&ingested.latency?ingested.latency:Math.floor(Math.random()*80+20)}ms</span><span style="font-size:9px;color:#666;letter-spacing:.4px;text-transform:uppercase;">Avg Latency</span></div>
            <div style="background:#1f1f1f;border-radius:8px;padding:10px;"><span style="font-size:20px;font-weight:700;color:#fff;display:block;">${ingested&&ingested.writes?ingested.writes:(Math.random()*9+0.5).toFixed(1)}K</span><span style="font-size:9px;color:#666;letter-spacing:.4px;text-transform:uppercase;">Writes/sec</span></div>
          </div>`;
        panel.classList.add('open');
        document.getElementById('kgPC2').addEventListener('click',()=>panel.classList.remove('open'));
      }
    });
    nodeLayer.addEventListener('mouseover',e=>{const ring=e.target.closest('[data-hub][data-name]');if(!ring)return;kgShowTip(e,ring.getAttribute('data-name')||'HUB',(ring.getAttribute('data-domain')||'').toUpperCase()+' DOMAIN',KG_COLORS[ring.getAttribute('data-domain')]||'#d9dbda');});
    nodeLayer.addEventListener('mousemove',e=>kgMoveTip(e));
    nodeLayer.addEventListener('mouseout',kgHideTip);

    const centerHub=document.getElementById('kgCenterHub');
    if(centerHub){
      centerHub.addEventListener('click',()=>{
        kgClearOverlays();
        const hubs=[...new Set([...document.querySelectorAll('#kgNodeLayer [data-hub][data-name]')].map(h=>h.getAttribute('data-hub')))];
        hubs.forEach((hubId,i)=>{
          const el=document.querySelector(`#kgNodeLayer circle[data-hub="${hubId}"][data-name]`);
          const domain=el?el.getAttribute('data-domain'):'core';
          const color=KG_COLORS[domain]||'#d9dbda';
          setTimeout(()=>{kgIlluminateHub(hubId,color);kgCreateRipple(0,0,color);},i*80);
        });
        kgSelectedNodes.add('CORE');kgUpdateBadge();
        kgPushToN8n({action:'pulse_all',timestamp:new Date().toISOString()});
        const cr=document.getElementById('kgCenterRingOuter');
        if(cr){cr.style.stroke='#fcaf45';cr.style.strokeWidth='8';setTimeout(()=>{cr.style.stroke='#e9e7e1';cr.style.strokeWidth='5';},800);}
      });
      centerHub.addEventListener('mouseover',e=>kgShowTip(e,'RAVEN DATA CENTRE','Click to pulse entire network','#f3f1ec'));
      centerHub.addEventListener('mousemove',e=>kgMoveTip(e));
      centerHub.addEventListener('mouseout',kgHideTip);
    }

    document.querySelectorAll('.kgt-btn[data-kgdomain]').forEach(btn=>{
      btn.addEventListener('click',()=>{
        document.querySelectorAll('.kgt-btn[data-kgdomain]').forEach(b=>b.classList.remove('active'));
        btn.classList.add('active');
        const domain=btn.getAttribute('data-kgdomain');kgClearOverlays();
        document.querySelectorAll('#kgNodeLayer circle[data-domain]').forEach(el=>{
          el.style.opacity=domain==='all'?'':(el.getAttribute('data-domain')===domain?'1':'0.06');
        });
        document.querySelectorAll('.kg-link-layer line').forEach(el=>{
          el.style.opacity=domain==='all'?'':'.15';
        });
        document.querySelectorAll('.kg-fan-line').forEach(el=>{
          el.style.opacity=domain==='all'?'':'.08';
        });
      });
    });

    const waveBtn=document.getElementById('kg-btn-wave');
    if(waveBtn)waveBtn.addEventListener('click',()=>{
      kgClearOverlays();
      const seen=new Set();
      document.querySelectorAll('#kgNodeLayer [data-hub][data-name]').forEach((h,i)=>{
        const id=h.getAttribute('data-hub');if(seen.has(id))return;seen.add(id);
        const domain=h.getAttribute('data-domain');const color=KG_COLORS[domain]||'#d9dbda';
        const cx=parseFloat(h.getAttribute('cx')),cy=parseFloat(h.getAttribute('cy'));
        setTimeout(()=>{kgCreateRipple(cx,cy,color);kgCreateHubHL(cx,cy,color);},i*60);
      });
    });

    const cascadeBtn=document.getElementById('kg-btn-cascade');
    if(cascadeBtn)cascadeBtn.addEventListener('click',()=>{
      kgClearOverlays();
      ['cms','atlas','lhcb','alice','core'].forEach((domain,di)=>{
        const seen=new Set();
        [...document.querySelectorAll(`#kgNodeLayer circle[data-domain="${domain}"][data-name]`)].forEach((h,hi)=>{
          const id=h.getAttribute('data-hub');if(seen.has(id))return;seen.add(id);
          setTimeout(()=>kgIlluminateHub(id,KG_COLORS[domain]),di*500+hi*120);
        });
      });
    });

    const clearBtn=document.getElementById('kg-btn-clear');
    if(clearBtn)clearBtn.addEventListener('click',()=>{
      kgClearOverlays();
      document.querySelectorAll('#kgNodeLayer circle[data-domain]').forEach(el=>el.style.opacity='');
      document.querySelectorAll('.kg-link-layer line').forEach(el=>el.style.opacity='');
      document.querySelectorAll('.kg-fan-line').forEach(el=>el.style.opacity='');
      document.querySelectorAll('.kgt-btn[data-kgdomain]').forEach(b=>b.classList.remove('active'));
      const allBtn=document.querySelector('.kgt-btn[data-kgdomain="all"]');if(allBtn)allBtn.classList.add('active');
      const panel=document.getElementById('kgInfoPanel');if(panel)panel.classList.remove('open');
    });

    const kgPanelClose=document.getElementById('kgPanelClose');
    if(kgPanelClose)kgPanelClose.addEventListener('click',()=>{const p=document.getElementById('kgInfoPanel');if(p)p.classList.remove('open');});

    const glowSlider=document.getElementById('kgGlowSlider');
    if(glowSlider)glowSlider.addEventListener('input',e=>{kgGlowIntensity=parseInt(e.target.value);});
  });
})();
