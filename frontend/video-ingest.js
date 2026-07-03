(function(){
  const store={files:[],urls:[]};
  let rafId=null;
  let lastCapture=0;
  const CAPTURE_INTERVAL_MS=100;
  let inFlight=false;

  function getApiBase(){
    return window.API_BASE||'http://localhost:8000';
  }

  function logDebug(level,source,message,extra){
    if(typeof window.ravenAppendLog==='function'){
      window.ravenAppendLog(level,source,message,extra);
    }
  }

  function captureAndAnalyze(videoEl,cameraId){
    if(inFlight||!videoEl||videoEl.paused||videoEl.readyState<2)return;
    const w=videoEl.videoWidth||640,h=videoEl.videoHeight||480;
    if(!w||!h)return;
    const c=document.createElement('canvas');
    c.width=w;c.height=h;
    c.getContext('2d').drawImage(videoEl,0,0,w,h);
    const b64=c.toDataURL('image/jpeg',.82).split(',')[1];
    inFlight=true;
    logDebug('DEBUG','VideoIngest',`Frame capture CAM-${String(cameraId).padStart(2,'0')} (${w}x${h})`);
    fetch(`${getApiBase()}/api/incidents/analyze`,{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({camera_id:cameraId,image_b64:b64})
    }).then(r=>r.ok?r.json():null).then(data=>{
      inFlight=false;
      if(!data)return;
      if(data.status==='skipped'){
        if(typeof window.showToast==='function'){
          window.showToast('Frame Skipped',data.reason||'No targets detected','info');
        }
        logDebug('DEBUG','VideoIngest',data.reason||'Frame skipped by YOLO');
        return;
      }
      if(data.id){
        if(typeof window.refreshDashboard==='function')window.refreshDashboard();
        if(typeof window.showToast==='function'){
          const sev=data.severity||'info';
          const isCritical=String(sev).toUpperCase()==='CRITICAL';
          window.showToast(
            isCritical?'Security Alert':`[${sev}] Threat Detected`,
            `Incident #${data.id} · CAM-${String(cameraId).padStart(2,'0')} · ${data.threat_type||'Activity'}`,
            sev,
            isCritical
          );
        }
        logDebug('INFO','VideoIngest',`Incident #${data.id} created (${data.severity})`);
      }
    }).catch(err=>{
      inFlight=false;
      logDebug('ERROR','VideoIngest',String(err));
    });
  }

  function analyzeLoop(videoEl,cameraId){
    stopAnalyzeLoop();
    lastCapture=0;
    function tick(ts){
      if(!videoEl||videoEl.paused){
        rafId=requestAnimationFrame(tick);
        return;
      }
      if(ts-lastCapture>=CAPTURE_INTERVAL_MS){
        lastCapture=ts;
        captureAndAnalyze(videoEl,cameraId);
      }
      rafId=requestAnimationFrame(tick);
    }
    rafId=requestAnimationFrame(tick);
    setTimeout(()=>captureAndAnalyze(videoEl,cameraId),300);
  }

  function stopAnalyzeLoop(){
    if(rafId){cancelAnimationFrame(rafId);rafId=null;}
    inFlight=false;
  }

  function bindUpload(inputEl,onLoaded){
    if(!inputEl)return;
    inputEl.addEventListener('change',()=>{
      const file=inputEl.files&&inputEl.files[0];
      if(!file||!file.type.startsWith('video/'))return;
      store.urls.forEach(u=>URL.revokeObjectURL(u));
      const url=URL.createObjectURL(file);
      store.files.unshift({name:file.name,url,file});
      store.urls.unshift(url);
      inputEl.value='';
      if(onLoaded)onLoaded(url,file.name);
    });
  }

  function playOnElement(videoEl,placeholderEl,url,loop=true){
    if(!videoEl)return null;
    if(placeholderEl)placeholderEl.style.display='none';
    videoEl.style.display='block';
    videoEl.src=url;
    videoEl.loop=loop;
    videoEl.muted=true;
    videoEl.playsInline=true;
    videoEl.play().catch(()=>{});
    return videoEl;
  }

  function playOnCameraFeed(camId,url){
    const feed=document.getElementById(`feed-cam-${camId}`);
    if(!feed)return;
    let vid=feed.parentElement.querySelector('video.cam-stream');
    if(!vid){
      vid=document.createElement('video');
      vid.className='camera-feed cam-stream';
      vid.id=`vid-cam-${camId}`;
      vid.playsInline=true;vid.muted=true;vid.loop=true;
      vid.style.cssText='width:100%;height:100%;object-fit:cover;position:absolute;inset:0;';
      feed.style.display='none';
      feed.parentElement.insertBefore(vid,feed);
    }
    vid.src=url;vid.play().catch(()=>{});
    return vid;
  }

  function setupDashboard(){
    const upload=document.getElementById('btn-cloud-upload');
    const play=document.getElementById('btn-cloud-play');
    const fileIn=document.getElementById('cloud-video-input');
    const video=document.getElementById('main-cctv-video');
    const ph=document.getElementById('cctv-placeholder');
    bindUpload(fileIn,(url)=>{
      playOnElement(video,ph,url);
      analyzeLoop(video,1);
    });
    if(play)play.addEventListener('click',()=>{
      if(!store.files.length){alert('Upload a video first.');return;}
      const v=playOnElement(video,ph,store.files[0].url);
      analyzeLoop(v,1);
    });
    if(upload&&fileIn)upload.addEventListener('click',()=>fileIn.click());
  }

  function setupCameraGrid(){
    const upload=document.getElementById('btn-grid-upload');
    const play=document.getElementById('btn-grid-play');
    const fileIn=document.getElementById('grid-video-input');
    bindUpload(fileIn,(url)=>{
      [1,2,3,4].forEach(id=>playOnCameraFeed(id,url));
      const v=document.getElementById('vid-cam-1')||document.getElementById('main-cctv-video');
      if(v)analyzeLoop(v,1);
    });
    if(play)play.addEventListener('click',()=>{
      if(!store.files.length){alert('Upload a video first.');return;}
      const url=store.files[0].url;
      [1,2,3,4].forEach(id=>playOnCameraFeed(id,url));
      const v=document.getElementById('vid-cam-1');
      if(v)analyzeLoop(v,1);
    });
    if(upload&&fileIn)upload.addEventListener('click',()=>fileIn.click());
  }

  document.addEventListener('DOMContentLoaded',()=>{
    setupDashboard();
    setupCameraGrid();
  });

  window.ravenVideoStore=store;
  window.ravenStopVideoAnalyze=stopAnalyzeLoop;
})();
