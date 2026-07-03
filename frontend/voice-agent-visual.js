(function(){
  const canvas=document.getElementById('vaCanvas');
  if(!canvas)return;
  const ctx=canvas.getContext('2d');
  let W,H,cx,cy,t=0,active=false;
  const particles=[];
  const RIBBON_L=28,RIBBON_R=28;

  function resize(){
    const wrap=canvas.parentElement;
    W=wrap.clientWidth;H=wrap.clientHeight;
    canvas.width=W;canvas.height=H;
    cx=W/2;cy=H/2;
  }
  window.addEventListener('resize',resize);
  resize();

  for(let i=0;i<120;i++){
    const ang=Math.random()*Math.PI*2;
    const dist=40+Math.random()*90;
    particles.push({
      x:Math.cos(ang)*dist,y:Math.sin(ang)*dist,
      tx:Math.cos(ang)*(120+Math.random()*80),
      ty:Math.sin(ang)*(120+Math.random()*80),
      hue:ang>0?320:180,
      size:.6+Math.random()*1.2,
      phase:Math.random()*Math.PI*2
    });
  }

  function ribbonY(x,side,offset){
    const amp=active?38:28;
    const freq=.012;
    const wave=Math.sin(x*freq+t*2+offset)*amp;
    const wave2=Math.sin(x*freq*1.7+t*1.3+offset*2)*amp*.35;
    return cy+wave+wave2+(side==='l'?-8:8);
  }

  function drawRibbon(side,color){
    const steps=RIBBON_L+RIBBON_R;
    const count=side==='l'?RIBBON_L:RIBBON_R;
    for(let r=0;r<count;r++){
      ctx.beginPath();
      const spread=(r-count/2)*2.2;
      for(let x=0;x<=W;x+=4){
        const px=side==='l'?x:W-x;
        const rx=side==='l'?px:W-px;
        const y=ribbonY(rx,side,spread)+spread;
        if(x===0)ctx.moveTo(px,y);else ctx.moveTo(px-4,ribbonY(rx-4,side,spread)+spread),ctx.lineTo(px,y);
      }
      ctx.strokeStyle=color;
      ctx.globalAlpha=.08+(r/count)*.12;
      ctx.lineWidth=.8;
      ctx.stroke();
    }
    ctx.globalAlpha=1;
  }

  function drawNetwork(){
    particles.forEach((p,i)=>{
      const pulse=.5+.5*Math.sin(t*2+p.phase);
      const x=cx+p.x+(p.tx-p.x)*pulse*.15;
      const y=cy+p.y+(p.ty-p.y)*pulse*.15;
      const ex=cx+p.tx,ey=cy+p.ty;
      const grad=ctx.createLinearGradient(x,y,ex,ey);
      grad.addColorStop(0,`hsla(${p.hue},100%,60%,${.15+.2*pulse})`);
      grad.addColorStop(1,`hsla(${p.hue},100%,50%,0)`);
      ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(ex,ey);
      ctx.strokeStyle=grad;ctx.lineWidth=.6;ctx.stroke();
      ctx.beginPath();ctx.arc(x,y,p.size,0,Math.PI*2);
      ctx.fillStyle=`hsla(${p.hue},100%,65%,${.5+.4*pulse})`;
      ctx.fill();
      if(i%4===0){
        particles.forEach((q,j)=>{
          if(j<=i||j-i>8)return;
          const dx=x-(cx+q.x),dy=y-(cy+q.y);
          if(dx*dx+dy*dy>2500)return;
          ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(cx+q.x,cy+q.y);
          ctx.strokeStyle=`rgba(255,255,255,${.02+.02*pulse})`;ctx.lineWidth=.3;ctx.stroke();
        });
      }
    });
  }

  function drawHub(){
    const r=active?72:68;
    const glow=ctx.createRadialGradient(cx,cy,r*.3,cx,cy,r*1.8);
    glow.addColorStop(0,'rgba(0,255,255,.25)');
    glow.addColorStop(.5,'rgba(180,0,255,.12)');
    glow.addColorStop(1,'rgba(0,0,0,0)');
    ctx.beginPath();ctx.arc(cx,cy,r*1.6,0,Math.PI*2);
    ctx.fillStyle=glow;ctx.fill();

    ctx.beginPath();ctx.arc(cx,cy,r,0,Math.PI*2);
    ctx.fillStyle='#0a0e18';ctx.fill();
    ctx.strokeStyle='rgba(0,255,255,.15)';ctx.lineWidth=2;ctx.stroke();

    const micScale=active?1.08:1;
    ctx.save();ctx.translate(cx,cy);ctx.scale(micScale,micScale);
    ctx.fillStyle='#00ffff';
    ctx.shadowColor='#00ffff';ctx.shadowBlur=active?24:14;
    ctx.beginPath();
    ctx.moveTo(-8,-10);ctx.lineTo(-8,-18+8);ctx.quadraticCurveTo(-8,-18,0,-18);
    ctx.quadraticCurveTo(8,-18,8,-10);ctx.lineTo(8,6);ctx.quadraticCurveTo(8,10,0,10);
    ctx.quadraticCurveTo(-8,10,-8,6);ctx.closePath();ctx.fill();
    ctx.shadowBlur=0;
    ctx.strokeStyle='#00ffff';ctx.lineWidth=2;ctx.lineCap='round';
    ctx.beginPath();ctx.arc(0,4,12,Math.PI,0);ctx.stroke();
    ctx.beginPath();ctx.moveTo(0,16);ctx.lineTo(0,24);ctx.stroke();
    ctx.beginPath();ctx.moveTo(-10,24);ctx.lineTo(10,24);ctx.stroke();
    ctx.restore();
  }

  function frame(){
    t+=.016;
    ctx.fillStyle='#080c14';
    ctx.fillRect(0,0,W,H);
    drawRibbon('l','#00ffff');
    drawRibbon('r','#ff00ff');
    drawNetwork();
    drawHub();
    requestAnimationFrame(frame);
  }

  window.vaSetVisualActive=function(on){active=!!on;};
  const orb=document.getElementById('orb2');
  if(orb){
    new MutationObserver(()=>{
      window.vaSetVisualActive(orb.classList.contains('active'));
    }).observe(orb,{attributes:true,attributeFilter:['class']});
  }
  frame();
})();
