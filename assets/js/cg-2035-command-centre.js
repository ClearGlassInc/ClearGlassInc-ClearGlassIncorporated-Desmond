import { VisualEngine } from '../cg-visual/render/engine.js';

(function(){
  function qs(sel, root=document){ return root.querySelector(sel); }
  function qsa(sel, root=document){ return Array.from(root.querySelectorAll(sel)); }

  function init(){
    const root=qs('#cg2035-command');
    if(!root || root.dataset.ready==='1') return;
    root.dataset.ready='1';

    const stage=qs('#cg2035-stage',root);
    const graphSvg=qs('#cg2035-graph',root);
    const coreLabel=qs('#cg2035-core-state',root);
    const insight=qs('[data-cg35-insight]',root);
    const fps=qs('[data-cg35-fps]',root);
    const commandForm=qs('#cg2035-command-form',root);
    const commandInput=qs('#cg2035-command-input',root);
    const commandSubmit=qs('.cg35-command-submit',root);

    let engine=null;
    let nodeEls=[];
    let edgeEls=[];
    let projectionEls=[];
    let anomalyEls=[];

    function makeSvg(tag, attrs, cls){
      const el=document.createElementNS('http://www.w3.org/2000/svg',tag);
      if(cls) el.setAttribute('class',cls);
      Object.keys(attrs||{}).forEach(k=>el.setAttribute(k,String(attrs[k])));
      return el;
    }

    function buildGraphLayer(){
      if(!graphSvg || !engine) return;
      graphSvg.innerHTML='';
      nodeEls=[];edgeEls=[];projectionEls=[];anomalyEls=[];
      const nodes=engine.sim.graph.nodes;
      const edges=engine.sim.graph.edges;

      edges.forEach((e,i)=>{
        const line=makeSvg('line',{x1:0,y1:0,x2:0,y2:0,'data-i':i},'cg35-edge');
        graphSvg.appendChild(line); edgeEls.push(line);
      });
      nodes.forEach((n,i)=>{
        const g=makeSvg('g',{transform:'translate(50 50)','data-node':i},'cg35-node-group');
        const ring=makeSvg('circle',{cx:0,cy:0,r:2.2},i<3?'cg35-ring':'cg35-ring');
        const circle=makeSvg('circle',{cx:0,cy:0,r:1.4},i<3?'cg35-node core':'cg35-node');
        if(i>2) circle.classList.add('grow');
        const label=makeSvg('text',{x:0,y:4,'text-anchor':'middle',fill:'#8fb1cf','font-size':'1.7','font-family':'ui-monospace,Menlo,monospace'},'cg35-svg-label');
        label.textContent=(n.id||'NODE').toUpperCase().slice(0,14);
        g.appendChild(ring); g.appendChild(circle); g.appendChild(label);
        graphSvg.appendChild(g);
        nodeEls.push({g,circle,ring,node:n});
      });

      for(let i=0;i<3;i++){
        const p=makeSvg('circle',{cx:50,cy:50,r:2.3},'cg35-predict-node');
        graphSvg.appendChild(p); projectionEls.push(p);
      }
    }

    function syncGraph(){
      if(!engine || !graphSvg) return;
      const sim=engine.sim;
      const nodes=sim.graph.nodes;
      const edges=sim.graph.edges;
      nodes.forEach((n,i)=>{
        const el=nodeEls[i]; if(!el) return;
        const z=0.86 + Math.min(.28,n.importance*.22);
        const x=n.x*100, y=(1-n.y)*100;
        el.g.setAttribute('transform','translate('+x.toFixed(3)+' '+y.toFixed(3)+') scale('+z.toFixed(3)+')');
        el.circle.setAttribute('r',(1.15+n.importance*1.85).toFixed(2));
        el.ring.setAttribute('r',(2.4+n.importance*1.8).toFixed(2));
        el.ring.style.opacity=String(.15+n.importance*.42);
      });
      edges.forEach((e,i)=>{
        const el=edgeEls[i],a=nodes.find(n=>n.id===e.a),b=nodes.find(n=>n.id===e.b);
        if(!el||!a||!b) return;
        el.setAttribute('x1',(a.x*100).toFixed(3));el.setAttribute('y1',((1-a.y)*100).toFixed(3));
        el.setAttribute('x2',(b.x*100).toFixed(3));el.setAttribute('y2',((1-b.y)*100).toFixed(3));
        if(((a.importance+b.importance)/2)>.78) el.classList.add('hot'); else el.classList.remove('hot');
      });

      const clock=sim.world.clock;
      projectionEls.forEach((p,i)=>{
        const base=nodes[(i*2+1)%Math.max(1,nodes.length)]||nodes[0];
        const px=Math.max(8,Math.min(92,(base?.x||.5)*100 + Math.sin(clock*.34+i)*8));
        const py=Math.max(8,Math.min(92,(1-(base?.y||.5))*100 + Math.cos(clock*.28+i)*7));
        p.setAttribute('cx',px.toFixed(2));p.setAttribute('cy',py.toFixed(2));
        p.setAttribute('r',(2.3+i*.8).toFixed(2));
      });

      if(coreLabel){
        coreLabel.textContent=sim.world.systemState==='CRITICAL'?'ANOMALY FIELD ELEVATED':
          sim.world.systemState==='ELEVATED'?'CORRELATION PRESSURE':'SYSTEM NOMINAL';
      }
      const act=Math.min(99,Math.round((sim.world.activity||0)*16));
      const e=Math.min(99,Math.round((sim.world.entropy||0)*100));
      if(insight){
        const queue=sim.queue.size;
        const signals=sim.signals.signals.length;
        insight.innerHTML='<b>Observable intelligence state:</b> topology '+(act>60?'reorganizing':'stabilizing')+
          ' · '+signals+' signal packets · queue '+queue+' · entropy '+e+'%.';
      }
      if(fps){
        const q=sim.world.performance?.tier||'BALANCED';
        fps.textContent='VISUAL TIER '+q+' · '+(engine.backend?.kind||'initializing').toUpperCase();
      }
    }

    function syncPanels(){
      if(!engine) return;
      const sim=engine.sim;
      const clock=sim.world.clock;
      const phases=['RETRIEVE','CORRELATE','ANALYZE','POLICY','CONFIDENCE','OVERSIGHT'];
      qsa('[data-agent-index]',root).forEach((row)=>{
        const idx=Number(row.getAttribute('data-agent-index'))||0;
        const phase=phases[Math.floor((clock*0.7+idx*1.3))%phases.length];
        const state=(sim.world.systemState==='CRITICAL'&&idx===2)?'ESCALATED':(sim.world.systemState==='ELEVATED'&&idx===1?'WATCH':'ACTIVE');
        const st=qs('[data-agent-state]',row), ph=qs('[data-agent-phase]',row);
        if(st) st.textContent=state;
        if(ph) ph.textContent=phase;
      });

      const activity=Math.min(99,Math.round((sim.world.activity||0)*18));
      const confidence=Math.min(99,Math.round(58+(1-(sim.world.entropy||0))*36));
      const anomaly=sim.anomalies.items.filter(a=>a.state!=='CLEARED').length;
      const jobs=sim.ai.jobs.filter(j=>j.state==='RUNNING').length;
      const set=(name,val)=>{const el=qs('[data-cg35-value="'+name+'"]',root);if(el)el.textContent=String(val);};
      set('activity',activity+'%');
      set('confidence',confidence+'%');
      set('anomaly',String(anomaly).padStart(2,'0'));
      set('jobs',String(jobs).padStart(2,'0'));

      const alert=qs('[data-cg35-alerts]',root);
      if(alert){
        alert.innerHTML='';
        const items=anomaly?[
          ['Anomaly field','Simulation event requires correlation.'],
          ['Predictive edge','Projection confidence is simulated only.']
        ]:[
          ['No active simulation anomaly','Graph field is within the current demo envelope.'],
          ['Predictive layer','Future-state links remain projections, not facts.']
        ];
        items.forEach(([a,b])=>{
          const d=document.createElement('div');d.className='cg35-alert';
          const strong=document.createElement('b');strong.textContent=a;
          const small=document.createElement('span');small.textContent=b;
          d.append(strong,small);alert.appendChild(d);
        });
      }
    }

    function injectCommand(command){
      if(!engine || !command) return;
      const q=command.toLowerCase();
      engine.sim.emit({type:'pipeline',source:'sentinel-console',label:command});
      engine.sim.emit({type:q.includes('risk')||q.includes('threat')?'anomaly':'signal',source:'sentinel-console',magnitude:q.includes('risk')?0.72:0.48});
      if(q.includes('graph')||q.includes('network')||q.includes('map')){
        engine.sim.emit({type:'node',source:'sentinel-console',magnitude:0.62,label:command});
        engine.sim.emit({type:'edge',source:'sentinel-console',magnitude:0.38,label:'projection'});
      }
      const note=qs('[data-cg35-command-note]',root);
      if(note) note.textContent='Accepted · observable pipeline → INPUT → CLASSIFY → RETRIEVE → ANALYZE → POLICY → CONFIDENCE → OVERSIGHT';
    }

    function loop(){
      if(!engine) return;
      syncGraph();
      syncPanels();
      requestAnimationFrame(loop);
    }

    commandForm?.addEventListener('submit',(ev)=>{
      ev.preventDefault();
      const cmd=(commandInput?.value||'').trim();
      if(!cmd) return;
      injectCommand(cmd);
      if(commandInput) commandInput.value='';
      commandSubmit?.setAttribute('aria-label','Command accepted');
      setTimeout(()=>commandSubmit?.setAttribute('aria-label','Run command'),900);
    });

    (async()=>{
      try{
        engine=new VisualEngine({
          host:stage,
          scenes:['FIELD','GRAPH','NETWORK','ANOMALY','PROVENANCE','AI_PIPELINE'],
          seed:20350926,
          startTier:'BALANCED'
        });
        await engine.init();
        buildGraphLayer();
        const first=qs('[data-agent-state]',root); if(first) first.textContent='ACTIVE';
        loop();
      }catch(err){
        const note=qs('[data-cg35-command-note]',root);
        if(note) note.textContent='Visual engine unavailable · static 2035 shell retained';
      }
    })();
  }

  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',init,{once:true});
  else init();
})();
