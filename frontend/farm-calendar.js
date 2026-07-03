(function() {
  const SC_ICONS = {
    camera:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#1a3a5c"/><g fill="#fff"><rect x="8" y="12" width="20" height="14" rx="2"/><circle cx="18" cy="19" r="4" fill="#1a3a5c"/><path d="M22 12 L26 9 L26 12 Z"/></g></svg>`,
    shield:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#2dbba0"/><g fill="#fff"><path d="M18 6 L28 10 L28 18 Q28 26 18 30 Q8 26 8 18 L8 10 Z"/></g></svg>`,
    lock:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#4a9eff"/><g fill="#fff"><rect x="12" y="16" width="12" height="10" rx="2"/><path d="M14 16 L14 13 Q14 9 18 9 Q22 9 22 13 L22 16" fill="none" stroke="#fff" stroke-width="2"/></g></svg>`,
    alert:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#e5392d"/><g fill="#fff"><path d="M18 8 L30 28 L6 28 Z"/><rect x="16.5" y="14" width="3" height="8" rx="1"/><circle cx="18" cy="24" r="1.5"/></g></svg>`,
    radar:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#7d3c98"/><g fill="none" stroke="#fff" stroke-width="1.5"><circle cx="18" cy="18" r="8"/><circle cx="18" cy="18" r="4"/><line x1="18" y1="18" x2="24" y2="12"/></g></svg>`,
    biometric:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#0e8a6e"/><g fill="none" stroke="#fff" stroke-width="1.4"><ellipse cx="18" cy="16" rx="6" ry="7"/><path d="M10 28 Q18 22 26 28"/></g></svg>`,
    patrol:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#34495e"/><g fill="#fff"><circle cx="18" cy="12" r="4"/><path d="M10 28 L18 18 L26 28 Z"/></g></svg>`,
    fence:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#c0522a"/><g fill="none" stroke="#fff" stroke-width="1.5"><line x1="10" y1="12" x2="10" y2="26"/><line x1="18" y1="10" x2="18" y2="26"/><line x1="26" y1="12" x2="26" y2="26"/><line x1="8" y1="16" x2="28" y2="16"/><line x1="8" y1="22" x2="28" y2="22"/></g></svg>`,
    drone:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#2980b9"/><g fill="#fff"><circle cx="18" cy="18" r="3"/><circle cx="10" cy="10" r="2"/><circle cx="26" cy="10" r="2"/><circle cx="10" cy="26" r="2"/><circle cx="26" cy="26" r="2"/><line x1="12" y1="12" x2="16" y2="16" stroke="#fff" stroke-width="1.2"/><line x1="24" y1="12" x2="20" y2="16" stroke="#fff" stroke-width="1.2"/><line x1="12" y1="24" x2="16" y2="20" stroke="#fff" stroke-width="1.2"/><line x1="24" y1="24" x2="20" y2="20" stroke="#fff" stroke-width="1.2"/></g></svg>`,
    access:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#16a085"/><g fill="#fff"><rect x="10" y="14" width="16" height="12" rx="1"/><rect x="14" y="18" width="4" height="4" fill="#16a085"/><line x1="22" y1="20" x2="24" y2="20" stroke="#16a085" stroke-width="2"/></g></svg>`,
    incident:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#d35400"/><g fill="#fff"><rect x="10" y="8" width="16" height="20" rx="2"/><line x1="14" y1="13" x2="22" y2="13" stroke="#d35400" stroke-width="1.5"/><line x1="14" y1="17" x2="22" y2="17" stroke="#d35400" stroke-width="1.5"/><line x1="14" y1="21" x2="18" y2="21" stroke="#d35400" stroke-width="1.5"/></g></svg>`,
    rf:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#e03f8e"/><g fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round"><path d="M8 22 Q18 10 28 22"/><path d="M12 22 Q18 14 24 22"/><path d="M16 22 Q18 18 20 22"/></g></svg>`,
    audit:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#b8860b"/><g fill="#fff"><path d="M12 8 L24 8 L24 28 L18 26 L12 28 Z"/><path d="M15 14 L21 14 M15 18 L21 18 M15 22 L18 22" stroke="#b8860b" stroke-width="1.5"/></g></svg>`,
    cctv:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#1a5e2a"/><g fill="#fff"><rect x="6" y="14" width="14" height="10" rx="2"/><path d="M20 17 L28 14 L28 24 L20 21 Z"/><circle cx="13" cy="19" r="2" fill="#1a5e2a"/></g></svg>`,
    perimeter:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#c0392b"/><g fill="none" stroke="#fff" stroke-width="1.5"><rect x="9" y="9" width="18" height="18" rx="2" stroke-dasharray="4 3"/><circle cx="18" cy="18" r="3" fill="#fff"/></g></svg>`,
    threat:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#8e44ad"/><g fill="#fff"><circle cx="18" cy="18" r="8" fill="none" stroke="#fff" stroke-width="1.5"/><circle cx="18" cy="18" r="2"/><line x1="18" y1="6" x2="18" y2="10" stroke="#fff" stroke-width="1.5"/><line x1="18" y1="26" x2="18" y2="30" stroke="#fff" stroke-width="1.5"/><line x1="6" y1="18" x2="10" y2="18" stroke="#fff" stroke-width="1.5"/><line x1="26" y1="18" x2="30" y2="18" stroke="#fff" stroke-width="1.5"/></g></svg>`,
    backup:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#27ae60"/><g fill="none" stroke="#fff" stroke-width="1.5"><ellipse cx="18" cy="20" rx="8" ry="5"/><path d="M10 20 L10 14 Q10 8 18 8 Q26 8 26 14 L26 20"/></g></svg>`,
    report:`<svg width="36" height="36" viewBox="0 0 36 36"><rect width="36" height="36" rx="9" fill="#e67e22"/><g fill="#fff"><rect x="11" y="8" width="14" height="20" rx="2"/><rect x="14" y="14" width="8" height="2" fill="#e67e22"/><rect x="14" y="18" width="6" height="2" fill="#e67e22"/><rect x="14" y="22" width="8" height="2" fill="#e67e22"/></g></svg>`
  };

  const SC_SUBS = [
    {name:"Perimeter Scan",day:1,iconKey:"perimeter",dot:"sc-dot-teal",severity:"low",analysis:"Routine perimeter sweep completed. All 12 zones nominal. No breach signatures detected."},
    {name:"CCTV Health Check",day:2,iconKey:"cctv",dot:"sc-dot-teal",severity:"low",analysis:"42 cameras online. 2 cameras flagged for lens cleaning at Gate C3 and Apron B."},
    {name:"Threat Assessment",day:3,iconKey:"threat",dot:"sc-dot-amber",severity:"medium",analysis:"Elevated RF activity near north fence. Cross-referencing with biometric logs."},
    {name:"Access Audit",day:5,iconKey:"access",dot:"sc-dot-teal",severity:"low",analysis:"147 access events reviewed. 3 after-hours entries flagged for HITL review."},
    {name:"Drone Patrol",day:7,iconKey:"drone",dot:"sc-dot-blue",severity:"low",analysis:"Autonomous drone patrol covered 8.2km perimeter. Thermal anomalies: 0."},
    {name:"RF Sweep",day:9,iconKey:"rf",dot:"sc-dot-pink",severity:"medium",analysis:"Wi-Fi probe requests spiked 340% near Terminal 2. Possible wardriving attempt."},
    {name:"Biometric Sync",day:10,iconKey:"biometric",dot:"sc-dot-teal",severity:"low",analysis:"Embedding index refreshed. 1,204 profiles verified. Match latency: 18ms avg."},
    {name:"Incident Review",day:11,iconKey:"incident",dot:"sc-dot-red",severity:"high",analysis:"3 open incidents require operator sign-off. Priority: Proximity alert EPWA C1."},
    {name:"Fence Integrity",day:12,iconKey:"fence",dot:"sc-dot-amber",severity:"medium",analysis:"Vibration sensor triggered at sector 7-B. Physical inspection scheduled 06:00."},
    {name:"Patrol Log",day:14,iconKey:"patrol",dot:"sc-dot-teal",severity:"low",analysis:"Night patrol completed 4 checkpoints. All guard posts confirmed active."},
    {name:"Lock Rotation",day:15,iconKey:"lock",dot:"sc-dot-blue",severity:"low",analysis:"Credential rotation cycle initiated for 28 access points. ETA 2 hours."},
    {name:"Radar Calibration",day:16,iconKey:"radar",dot:"sc-dot-teal",severity:"low",analysis:"RF spatial grid recalibrated. Detection radius extended to 450m."},
    {name:"Alert Triage",day:18,iconKey:"alert",dot:"sc-dot-red",severity:"high",analysis:"12 alerts in queue. 2 CRITICAL (proximity), 4 HIGH (unidentified), 6 MEDIUM."},
    {name:"Shield Update",day:20,iconKey:"shield",dot:"sc-dot-teal",severity:"low",analysis:"Firewall rules updated. 3 new IoT devices whitelisted after fingerprint scan."},
    {name:"Camera Deploy",day:22,iconKey:"camera",dot:"sc-dot-blue",severity:"low",analysis:"New PTZ camera commissioned at Apron C. Stream latency: 42ms."},
    {name:"Audit Chain Verify",day:25,iconKey:"audit",dot:"sc-dot-amber",severity:"medium",analysis:"Cryptographic audit chain verified. 4,892 records intact. Latest hash block valid."},
    {name:"Backup Snapshot",day:28,iconKey:"backup",dot:"sc-dot-teal",severity:"low",analysis:"Full evidence package snapshot completed. 2.4TB archived to cold storage."},
    {name:"Monthly Report",day:30,iconKey:"report",dot:"sc-dot-amber",severity:"low",analysis:"SOC monthly digest ready. 847 incidents processed, 99.2% auto-resolved."}
  ];

  const SC_MONTHS=["January","February","March","April","May","June","July","August","September","October","November","December"];
  const now=new Date();
  let scYear=now.getFullYear(),scMonth=now.getMonth(),scSel=null;

  function scBuild(){
    const grid=document.getElementById('fcCalGrid');
    if(!grid)return;
    grid.innerHTML='';
    document.getElementById('fcNavMonth').textContent=SC_MONTHS[scMonth]+' '+scYear;
    const firstDow=new Date(scYear,scMonth,1).getDay();
    const offset=firstDow===0?6:firstDow-1;
    const dim=new Date(scYear,scMonth+1,0).getDate();
    const prevDim=new Date(scYear,scMonth,0).getDate();
    const isCurr=(scYear===now.getFullYear()&&scMonth===now.getMonth());
    for(let i=0;i<offset;i++){grid.appendChild(scMakeCell(prevDim-offset+1+i,'fc-other-month',[],false));}
    for(let d=1;d<=dim;d++){
      const isToday=isCurr&&d===now.getDate();
      const isSel=scSel&&scSel.y===scYear&&scSel.m===scMonth&&scSel.d===d;
      const subs=SC_SUBS.filter(s=>s.day===d);
      let cls='';if(isToday)cls+=' fc-today';if(isSel)cls+=' fc-selected';
      grid.appendChild(scMakeCell(d,cls.trim(),subs,true));
    }
    const total=offset+dim,rem=total%7===0?0:7-(total%7);
    for(let d=1;d<=rem;d++){grid.appendChild(scMakeCell(d,'fc-other-month',[],false));}
    scBuildLegend();
  }

  function scMakeCell(dayNum,extraClass,subs,clickable){
    const el=document.createElement(clickable?'button':'div');
    el.className='fc-day-cell'+(extraClass?' '+extraClass:'');
    if(subs&&subs.length>0){
      const sub=subs[0];
      const iconWrap=document.createElement('div');iconWrap.className='fc-day-icon-wrap';
      iconWrap.innerHTML=SC_ICONS[sub.iconKey]||'';el.appendChild(iconWrap);
      const dot=document.createElement('div');dot.className='fc-day-dot '+sub.dot;el.appendChild(dot);
    }else{
      const spacer=document.createElement('div');spacer.className='fc-day-icon-spacer';el.appendChild(spacer);
    }
    const numEl=document.createElement('span');numEl.className='fc-day-num';numEl.textContent=dayNum;el.appendChild(numEl);
    if(clickable){el.addEventListener('click',()=>scOpenModal(dayNum,subs||[]));}
    return el;
  }

  function scSeverityColor(sev){
    return {low:'#2dbba0',medium:'#f5a623',high:'#e5392d'}[sev]||'#888';
  }

  function scOpenModal(day,subs){
    scSel={y:scYear,m:scMonth,d:day};scBuild();
    document.getElementById('fcModalDate').textContent=SC_MONTHS[scMonth].slice(0,3).toUpperCase()+' · '+scYear;
    document.getElementById('fcModalDayNum').textContent=day;
    const c=document.getElementById('fcModalSubs');c.innerHTML='';
    if(!subs.length){
      const e=document.createElement('div');e.className='fc-modal-empty';e.textContent='No security events scheduled';
      c.appendChild(e);
      const analysis=document.getElementById('fcModalAnalysis');
      if(analysis){analysis.style.display='none';}
    }else{
      subs.forEach(s=>{
        const item=document.createElement('div');item.className='fc-modal-sub-item';
        item.innerHTML=`<div class="fc-modal-sub-icon">${SC_ICONS[s.iconKey]||''}</div><div class="fc-modal-sub-info"><div class="fc-modal-sub-name">${s.name}</div><div class="fc-modal-sub-desc" style="color:${scSeverityColor(s.severity)}">${s.severity.toUpperCase()} SEVERITY</div></div>`;
        c.appendChild(item);
      });
      const analysis=document.getElementById('fcModalAnalysis');
      if(analysis){
        analysis.style.display='block';
        analysis.innerHTML=`<div class="fc-analysis-label">Daily Analysis</div><div class="fc-analysis-text">${subs.map(s=>s.analysis).join(' ')}</div><div class="fc-analysis-metrics"><div class="fc-metric"><span class="fc-metric-val">${subs.length}</span><span class="fc-metric-lbl">Events</span></div><div class="fc-metric"><span class="fc-metric-val" style="color:${scSeverityColor(subs.reduce((a,s)=>s.severity==='high'?'high':s.severity==='medium'&&a!=='high'?'medium':a,'low'))}">${subs.filter(s=>s.severity==='high').length||subs.filter(s=>s.severity==='medium').length||0}</span><span class="fc-metric-lbl">Priority</span></div><div class="fc-metric"><span class="fc-metric-val">${Math.floor(Math.random()*40+60)}%</span><span class="fc-metric-lbl">Coverage</span></div></div>`;
      }
    }
    document.getElementById('fcModalOverlay').classList.add('open');
  }

  function scCloseModal(){document.getElementById('fcModalOverlay').classList.remove('open');}

  function scBuildLegend(){
    const bar=document.getElementById('fcLegendBar');if(!bar)return;bar.innerHTML='';
    [{label:'Surveillance',cls:'sc-dot-teal'},{label:'Alerts',cls:'sc-dot-amber'},{label:'Access Control',cls:'sc-dot-blue'},{label:'RF/Threat',cls:'sc-dot-pink'},{label:'Critical',cls:'sc-dot-red'}].forEach(t=>{
      const el=document.createElement('div');el.className='fc-legend-item';
      el.innerHTML=`<div class="fc-legend-dot ${t.cls}"></div><span>${t.label}</span>`;bar.appendChild(el);
    });
  }

  window.farmCalInit = function() {
    document.getElementById('fcPrevBtn').addEventListener('click',()=>{scMonth--;if(scMonth<0){scMonth=11;scYear--;}scSel=null;scBuild();});
    document.getElementById('fcNextBtn').addEventListener('click',()=>{scMonth++;if(scMonth>11){scMonth=0;scYear++;}scSel=null;scBuild();});
    document.getElementById('fcTodayBtn').addEventListener('click',()=>{scYear=now.getFullYear();scMonth=now.getMonth();scSel=null;scBuild();});
    document.getElementById('fcModalClose').addEventListener('click',scCloseModal);
    document.getElementById('fcModalOverlay').addEventListener('click',e=>{if(e.target===document.getElementById('fcModalOverlay'))scCloseModal();});
    scBuild();
  };
})();
