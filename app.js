/* ============================================================
   SILICA — Enterprise Workspace (frontend, prototype build)
   Client-side router + state + run engine. Run events are replayed
   from a recorded reference transcript; in production they arrive
   over WebSocket from the Silica Workflow Orchestrator.
   ============================================================ */
(function(){
'use strict';

const STAGES = ["Specification","RTL Design","Functional Verification","Synthesis","Floorplanning","Placement","Routing","Timing Analysis","Physical Verification","Tapeout Preparation"];
const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e=document.createElement(tag); if(cls) e.className=cls; if(html!==undefined) e.innerHTML=html; return e; };
const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');

/* ---------------- State ---------------- */
const state = {
  view: 'workspace',
  projects: [],          // {id, name, brief, node, created, lastStatus, runId}
  runs: {},              // id -> {projectId, status, transcript, artifacts:[], metrics:[], recoveries:0}
  activeRunId: null,
  openedRunId: null,
  files: [],             // pending upload in new-design form
  selNode: 'TSMC 16nm FinFET (illustrative)',
};
const LS_KEY = 'silica_state_v1';
function save(){ try{ localStorage.setItem(LS_KEY, JSON.stringify({projects:state.projects, runs:state.runs})); }catch(e){} }
function load(){
  try{
    const raw = localStorage.getItem(LS_KEY);
    if(raw){ const d=JSON.parse(raw); state.projects=d.projects||[]; state.runs=d.runs||{}; }
  }catch(e){}
  if(state.projects.length===0){ seed(); save(); }
}
function seed(){
  const now = Date.now();
  state.projects = [
    {id:'p_aes', name:'AES-128 Encryption Core', brief:'Compact AES-128 ECB, 128-bit datapath, 10 rounds, 400 MHz target.', node:'TSMC 16nm FinFET (illustrative)', created: now-2*864e5, lastStatus:'passed', runId:'r_aes'},
    {id:'p_riscv', name:'RV32I Microcontroller', brief:'8-bit peripheral RV32I core with UART, SPI, timer, 8 KB SRAM.', node:'SkyWater 130nm (illustrative)', created: now-6*864e5, lastStatus:'passed', runId:'r_riscv'},
    {id:'p_uart', name:'Multi-channel UART', brief:'4-channel UART with 256-byte FIFOs and auto-baud.', node:'TSMC 16nm FinFET (illustrative)', created: now-9*864e5, lastStatus:'failed', runId:'r_uart'},
  ];
  state.runs = {
    r_aes: {projectId:'p_aes', status:'passed', artifacts:[], metrics:[], recoveries:2, finishedAt: now-2*864e5},
    r_riscv: {projectId:'p_riscv', status:'passed', artifacts:[], metrics:[], recoveries:0, finishedAt: now-6*864e5},
    r_uart: {projectId:'p_uart', status:'failed', artifacts:[], metrics:[], recoveries:1, finishedAt: now-9*864e5, failReason:'Timing not met at 400 MHz (WNS -0.42 ns). Routing congestion in channel 3.'},
  };
}
load();

/* ---------------- Toast ---------------- */
let toastT;
function toast(title, body){
  const t=$('#toast'); $('#toast-t').textContent=title; $('#toast-b').textContent=body;
  t.classList.add('show'); clearTimeout(toastT); toastT=setTimeout(()=>t.classList.remove('show'), 4200);
}

/* ---------------- Router ---------------- */
const VIEW_NAMES = {workspace:'Workspace', new:'New Design', run:'Active Run', history:'Past Runs', artifacts:'Artifacts', settings:'Settings'};
function go(view, arg){
  state.view = view;
  document.querySelectorAll('.nav-item').forEach(b=>b.classList.toggle('active', b.dataset.view===view));
  $('#crumb-cur').textContent = VIEW_NAMES[view]||view;
  render();
  $('#view').scrollTop = 0;
}
document.querySelectorAll('.nav-item').forEach(b=>b.addEventListener('click', ()=>go(b.dataset.view)));
$('#top-new').addEventListener('click', ()=>go('new'));

/* ---------------- Run engine ---------------- */
const engine = {
  timer:null, idx:0, playing:false, speed:1, runId:null,
  start(runId){
    this.runId=runId; this.idx=0; this.playing=true; this.speed=1;
    state.activeRunId=runId;
    const run=state.runs[runId]; run.status='running'; run.artifacts=[]; run.metrics=[]; run.recoveries=0;
    updateRunPill(); save();
    this.next();
  },
  next(){
    if(!this.playing) return;
    const ev = window.SILICA_TRANSCRIPT.events[this.idx];
    if(!ev){ this.finish(); return; }
    applyEvent(ev, this.runId);
    this.idx++;
    const nxt = window.SILICA_TRANSCRIPT.events[this.idx];
    const gap = nxt ? Math.max(120, (nxt.t - ev.t)*130 / this.speed) : 300;
    this.timer = setTimeout(()=>this.next(), gap);
  },
  pause(){ this.playing=false; clearTimeout(this.timer); updateRunPill(); },
  resume(){ if(this.playing) return; this.playing=true; updateRunPill(); this.next(); },
  restart(){ clearTimeout(this.timer); this.idx=0; resetRunDOM(); this.playing=true; updateRunPill(); this.next(); },
  setSpeed(s){ this.speed=s; },
  finish(){
    this.playing=false; clearTimeout(this.timer);
    const run=state.runs[this.runId]; run.status='passed'; run.finishedAt=Date.now();
    const p = state.projects.find(x=>x.runId===this.runId); if(p) p.lastStatus='passed';
    state.activeRunId=null; updateRunPill(); save();
    toast('Run complete', window.SILICA_TRANSCRIPT.project + ' — all stages passed.');
    if(state.view==='run') renderRun();
  }
};
function updateRunPill(){
  const pill=$('#run-pill'), txt=$('#run-pill-text');
  const active = Object.values(state.runs).some(r=>r.status==='running');
  if(active){ pill.classList.add('live'); txt.textContent='Run in progress'; }
  else { pill.classList.remove('live'); txt.textContent='No active run'; }
  const rc = Object.values(state.runs).filter(r=>r.status==='running').length;
  $('#nav-run-count').textContent = rc ? rc : '—';
  $('#nav-hist-count').textContent = Object.keys(state.runs).length;
}
updateRunPill();

function applyEvent(ev, runId){
  const run = state.runs[runId];
  const runViewActive = state.view==='run';
  if(ev.type==='stage'){
    run.curStage = ev.stage;
    if(ev.status==='recovered') run.recoveries++;
    if(runViewActive) renderPipeline(ev.stage, ev.status, ev.name, ev.sub);
  }
  else if(ev.type==='task' && runViewActive){ setLive('task', ev.text); }
  else if(ev.type==='op' && runViewActive){ setLive('op', ev.text); }
  else if(ev.type==='log'){ if(runViewActive) appendLog(ev.level, ev.text); }
  else if(ev.type==='diag'){ if(runViewActive) showDiag(ev.kind, ev.text); }
  else if(ev.type==='agent'){
    if(runViewActive) appendAgent(ev.role, ev.text, ev.detail||null);
  }
  else if(ev.type==='artifact'){
    run.artifacts.push(ev);
    if(runViewActive) appendArtifact(ev);
  }
  else if(ev.type==='metric'){
    run.metrics.push(ev);
    if(runViewActive) renderMetrics(run);
  }
  else if(ev.type==='outcome'){
    run.outcome = ev;
    if(runViewActive) showOutcome(ev);
  }
}

/* ---------------- Render dispatcher ---------------- */
function render(){
  const v = $('#view-inner');
  if(state.view==='workspace'){ v.innerHTML = renderWorkspace(); bindRows(); }
  else if(state.view==='new'){ v.innerHTML = renderNew(); bindNew(); }
  else if(state.view==='run'){ renderRun(); return; }
  else if(state.view==='history'){ v.innerHTML = renderHistory(); bindRows(); }
  else if(state.view==='artifacts'){ v.innerHTML = renderArtifactsPage(); bindDownloads(); }
  else if(state.view==='settings'){ v.innerHTML = renderSettings(); }
}

/* ---------------- Workspace ---------------- */
function renderWorkspace(){
  const recent = state.projects.slice(0,4);
  const passed = state.projects.filter(p=>p.lastStatus==='passed').length;
  const failed = state.projects.filter(p=>p.lastStatus==='failed').length;
  const arts = Object.values(state.runs).reduce((a,r)=>a+(r.artifacts?r.artifacts.length:0),0);
  const recov = Object.values(state.runs).reduce((a,r)=>a+(r.recoveries||0),0);
  return `
  <div class="hero-strip">
    <div>
      <div class="kicker">Silica Enterprise Workspace</div>
      <h1>Describe a chip.<br><em>Silica engineers it to tapeout.</em></h1>
      <p>Specification through GDSII — orchestrated by autonomous agents that invoke real EDA tools, recover from failures, and verify every artifact.</p>
      <div class="cta-row">
        <button class="btn primary" id="ws-new">Start a new design</button>
        <button class="btn" id="ws-open">Open recent run</button>
      </div>
    </div>
    <div class="chip-mini" aria-hidden="true"><div class="ly"></div><div class="ly"></div><div class="ly"></div><div class="ly"></div><div class="core"></div></div>
  </div>
  <div class="stat-row">
    <div class="stat"><div class="v">${state.projects.length}</div><div class="l">Projects</div></div>
    <div class="stat"><div class="v">${passed}<small>pass</small> · ${failed}<small>fail</small></div><div class="l">Run outcomes</div></div>
    <div class="stat"><div class="v">${recov}</div><div class="l">Agent recoveries</div></div>
    <div class="stat"><div class="v">${arts||'—'}</div><div class="l">Artifacts generated</div></div>
  </div>
  <div class="grid-2">
    <div>
      <div class="card-head"><h3>Recent projects</h3><span class="kicker">${recent.length} total</span></div>
      <div class="proj-list">
        <div class="proj-head"><span>Project</span><span>Process node</span><span>Last run</span><span>Status</span><span></span></div>
        ${recent.map(p=>`
          <div class="proj-row" data-open="${p.id}">
            <div><div class="p-name">${esc(p.name)}<small>${esc(p.brief.slice(0,52))}${p.brief.length>52?'…':''}</small></div></div>
            <div class="p-node">${esc(p.node)}</div>
            <div class="p-time">${timeAgo(p.created)}</div>
            <div><span class="status ${p.lastStatus}"><span class="d"></span>${p.lastStatus}</span></div>
            <div><span class="kicker" style="color:var(--amber)">Open →</span></div>
          </div>`).join('')}
      </div>
    </div>
    <div>
      <div class="card-head"><h3>Recent activity</h3></div>
      <div class="card" style="padding:8px 24px">
        <div class="feed-item ok"><div class="t">2d ago</div><div class="i"></div><div class="txt"><b>AES-128 core</b> <span>passed all 10 stages; GDSII streamed out.</span></div></div>
        <div class="feed-item run"><div class="t">2d ago</div><div class="i"></div><div class="txt"><b>Agent recovery</b> <span>closed timing at synthesis via register retiming.</span></div></div>
        <div class="feed-item"><div class="t">6d ago</div><div class="i"></div><div class="txt"><b>RV32I MCU</b> <span>functional verification reached 96.4% line coverage.</span></div></div>
        <div class="feed-item fail"><div class="t">9d ago</div><div class="i"></div><div class="txt"><b>Multi-channel UART</b> <span>run failed — timing not met, routing congestion.</span></div></div>
      </div>
      <div class="card" style="margin-top:16px">
        <div class="card-head"><h3>Engineering note</h3></div>
        <p class="dim" style="font-size:13px;line-height:1.7">This is a <b style="color:var(--warn)">prototype frontend build</b>. Run views replay a recorded reference transcript to illustrate the live experience; no EDA backend is connected. Physical fabrication is performed externally by foundry partners.</p>
      </div>
    </div>
  </div>`;
}
function timeAgo(ts){ const d=Date.now()-ts; if(d<3600e3) return Math.max(1,Math.round(d/60e3))+'m ago'; if(d<864e5) return Math.round(d/3600e3)+'h ago'; return Math.round(d/864e5)+'d ago'; }

/* ---------------- New design ---------------- */
function renderNew(){
  const nodes = ['TSMC 16nm FinFET (illustrative)','TSMC 7nm FinFET (illustrative)','TSMC 5nm FinFET (illustrative)','Samsung 3nm GAA (illustrative)','SkyWater 130nm (open PDK)'];
  return `
  <div class="view-head">
    <div><h1 class="view-title">New chip design</h1><div class="view-sub" style="margin:0">Describe the chip you want to build. Silica will take it from specification through tapeout preparation.</div></div>
    <div class="actions"><button class="btn" id="np-cancel">Cancel</button></div>
  </div>
  <div class="form-grid">
    <div>
      <div class="field" id="f-brief">
        <label>Design brief <span class="req">*</span></label>
        <textarea id="np-brief" placeholder="e.g. A low-power AES-128 encrypt core, 128-bit data path, 10 iterative rounds, synchronous single-clock, target 400 MHz, TSMC 16nm. Include AXI4-lite register interface."></textarea>
        <div class="err">Please describe the chip (min 20 characters).</div>
        <div class="hint">Natural language. Mention interfaces, throughput, clock domain, and any hard constraints.</div>
      </div>
      <div class="field">
        <label>Upload existing RTL (optional)</label>
        <div class="drop" id="np-drop">
          <div class="ic"><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M12 16V4M6 10l6-6 6 6M4 20h16"/></svg></div>
          <div class="t">Drop Verilog / SystemVerilog files here</div>
          <div class="s">.v · .sv · .vhd · .vhdl — max 2 MB each</div>
          <input type="file" id="np-file" multiple accept=".v,.sv,.vhd,.vhdl" style="display:none">
        </div>
        <div class="file-list" id="np-files"></div>
      </div>
    </div>
    <div>
      <div class="card">
        <div class="card-head"><h3>Configuration</h3></div>
        <div class="field">
          <label>Target process node</label>
          <select id="np-node">${nodes.map(n=>`<option ${n===state.selNode?'selected':''}>${n}</option>`).join('')}</select>
        </div>
        <div class="option-grid">
          <div class="field" style="margin-bottom:0"><label>Target frequency</label><input type="text" id="np-freq" value="400 MHz"></div>
          <div class="field" style="margin-bottom:0"><label>Core voltage</label><input type="text" id="np-volt" value="0.90 V"></div>
        </div>
        <div class="field" style="margin-top:18px;margin-bottom:0">
          <label>Optimization priority</label>
          <div class="option-grid" id="np-prio">
            <div class="opt sel" data-p="balanced"><div class="o-t">Balanced</div><div class="o-s">timing / area / power</div></div>
            <div class="opt" data-p="speed"><div class="o-t">Speed</div><div class="o-s">max frequency</div></div>
            <div class="opt" data-p="area"><div class="o-t">Area</div><div class="o-s">minimize die size</div></div>
            <div class="opt" data-p="power"><div class="o-t">Power</div><div class="o-s">low-energy first</div></div>
          </div>
        </div>
      </div>
      <div class="start-bar">
        <div class="note">Starting a run dispatches the 10-stage engineering workflow. In this prototype the run view replays a recorded reference transcript.</div>
        <button class="btn amber" id="np-start">Start engineering run →</button>
      </div>
    </div>
  </div>`;
}
function bindNew(){
  $('#ws-new')?.addEventListener('click',()=>{});
  $('#np-cancel').addEventListener('click',()=>go('workspace'));
  const drop=$('#np-drop'), file=$('#np-file');
  drop.addEventListener('click',()=>file.click());
  drop.addEventListener('dragover',e=>{e.preventDefault();drop.classList.add('over');});
  drop.addEventListener('dragleave',()=>drop.classList.remove('over'));
  drop.addEventListener('drop',e=>{e.preventDefault();drop.classList.remove('over');addFiles(e.dataTransfer.files);});
  file.addEventListener('change',()=>{addFiles(file.files); file.value='';});
  document.querySelectorAll('#np-prio .opt').forEach(o=>o.addEventListener('click',()=>{
    document.querySelectorAll('#np-prio .opt').forEach(x=>x.classList.remove('sel')); o.classList.add('sel');
  }));
  $('#np-start').addEventListener('click', startRun);
  renderFileChips();
}
function addFiles(list){
  const ok=[], bad=[];
  for(const f of list){
    const ext=f.name.split('.').pop().toLowerCase();
    if(!['v','sv','vhd','vhdl'].includes(ext)){ bad.push({name:f.name, reason:'unsupported type'}); continue; }
    if(f.size>2*1024*1024){ bad.push({name:f.name, reason:'exceeds 2 MB'}); continue; }
    ok.push({name:f.name, size:f.size});
  }
  state.files = state.files.concat(ok);
  renderFileChips();
  if(bad.length) toast('File rejected', bad.map(b=>b.name+' — '+b.reason).join('; '));
}
function renderFileChips(){
  const c=$('#np-files'); if(!c) return;
  c.innerHTML = state.files.map((f,i)=>`<div class="file-chip"><span class="nm">${esc(f.name)}</span><span class="sz">${(f.size/1024).toFixed(1)} KB</span><button class="rm" data-i="${i}">×</button></div>`).join('');
  c.querySelectorAll('.rm').forEach(b=>b.addEventListener('click',()=>{state.files.splice(+b.dataset.i,1);renderFileChips();}));
}
function startRun(){
  const brief=$('#np-brief').value.trim();
  const fb=$('#f-brief');
  if(brief.length<20){ fb.classList.add('error'); $('#np-brief').focus(); toast('Input needed','Please describe the chip you want to build.'); return; }
  fb.classList.remove('error');
  let name = brief.split(/[,\.\n]/)[0].trim();
  if(name.length>34){ name=name.slice(0,34); const sp=name.lastIndexOf(' '); if(sp>12) name=name.slice(0,sp); }
  name = name || 'Untitled design';
  const id='p_'+Date.now().toString(36), rid='r_'+Date.now().toString(36);
  state.projects.unshift({id, name, brief, node:$('#np-node').value, created:Date.now(), lastStatus:'running', runId:rid});
  state.runs[rid]={projectId:id, status:'running', artifacts:[], metrics:[], recoveries:0};
  state.files=[]; save();
  go('run');
  engine.start(rid);
  toast('Run started', name + ' — dispatching 10-stage workflow.');
}

/* ---------------- Run view ---------------- */
function renderRun(){
  const v=$('#view-inner');
  const running = engine.playing && state.activeRunId;
  const runId = state.activeRunId || state.openedRunId || (state.projects[0]&&state.projects[0].runId);
  const run = state.runs[runId];
  const proj = state.projects.find(p=>p.runId===runId);
  v.innerHTML = `
  <div class="view-head">
    <div>
      <h1 class="view-title" style="margin-bottom:4px">${proj?esc(proj.name):'Engineering run'}</h1>
      <div class="kicker" style="margin-top:2px">${proj?esc(proj.node):''} · ${run?esc(run.status):''} ${run&&run.recoveries?`· ${run.recoveries} agent recoveries`:''}</div>
    </div>
    <div class="actions">
      <button class="btn sm" id="run-speed">1×</button>
      <button class="btn sm" id="run-pause">${running?'Pause':'Resume'}</button>
      <button class="btn sm" id="run-restart">Replay</button>
    </div>
  </div>
  <div class="run-layout">
    <div class="pipeline card" id="pipeline" style="padding:14px 12px">
      <div class="kicker" style="padding:4px 12px 12px">Workflow · 10 stages</div>
      ${STAGES.map((s,i)=>`<div class="stage pending" data-stage="${i}"><div class="s-ic"></div><div><div class="s-num">0${i+1}</div><div class="s-name">${s}</div><div class="s-sub" data-sub></div></div></div>`).join('')}
    </div>
    <div class="run-panel">
      <div id="outcome-slot"></div>
      <div class="live-card" id="live-card">
        <div class="live-head"><span class="stage-tag" id="live-stage">Stage 01</span><h3 id="live-title">Awaiting dispatch</h3></div>
        <div class="live-body">
          <div class="live-task" id="live-task">The workflow orchestrator is initializing the 10-stage pipeline.</div>
          <div class="live-op" id="live-op">—</div>
          <div class="diag fail" id="diag-fail"><span class="tag">Failure diagnosed</span><span id="diag-fail-t"></span></div>
          <div class="diag recover" id="diag-recover"><span class="tag">Recovery action</span><span id="diag-recover-t"></span></div>
        </div>
      </div>
      <div class="term">
        <div class="term-bar"><span class="dots"><i></i><i></i><i></i></span><span>tool output · live</span><span class="spacer"></span><button id="term-toggle">Expand</button></div>
        <div class="term-body" id="term-body"><div class="ln"><span class="ts">--:--:--</span>silica-orchestrator v0.9.3 — awaiting events<span class="cursor"></span></div></div>
      </div>
      <div class="card">
        <div class="card-head"><h3>Agent activity &amp; recovery</h3><span class="kicker" id="agt-count">0 decisions</span></div>
        <div id="agt-list"></div>
      </div>
      <div class="card" id="metrics-card" style="display:none">
        <div class="card-head"><h3>Reported metrics</h3><span class="kicker">estimated vs tool-reported</span></div>
        <div class="metric-grid" id="metrics-grid"></div>
      </div>
      <div class="card">
        <div class="card-head"><h3>Artifacts</h3><span class="kicker" id="art-count">0 generated</span></div>
        <div id="art-list"><div class="faint mono" style="font-size:11px;padding:8px 0">No artifacts yet — they appear as stages complete.</div></div>
      </div>
    </div>
  </div>`;
  bindRunControls();
  // If replaying, fast-forward state to current idx
  if(engine.runId && engine.idx>0){
    for(let i=0;i<engine.idx;i++) applyEvent(window.SILICA_TRANSCRIPT.events[i], engine.runId);
  }
  // If completed run opened from history, show full final state
  if(run && run.status==='passed'){
    window.SILICA_TRANSCRIPT.events.forEach(ev=>applyEvent(ev, runId));
    const pb=$('#run-pause'); if(pb){ pb.style.display='none'; }
  }
}
function bindRunControls(){
  $('#run-pause').addEventListener('click', function(){
    if(engine.playing){ engine.pause(); this.textContent='Resume'; }
    else { engine.resume(); this.textContent='Pause'; }
  });
  $('#run-restart').addEventListener('click',()=>{ engine.restart(); });
  $('#run-speed').addEventListener('click', function(){
    const s = engine.speed>=4?1:engine.speed*2; engine.setSpeed(s); this.textContent=s+'×';
  });
  const tb=$('#term-body');
  $('#term-toggle').addEventListener('click', function(){
    const open = tb.style.maxHeight!=='520px';
    tb.style.maxHeight = open?'520px':'260px'; this.textContent=open?'Collapse':'Expand';
  });
}
function resetRunDOM(){ renderRun(); }
function renderPipeline(i, status, name, sub){
  const st = document.querySelectorAll(`#pipeline .stage`);
  st.forEach((s,idx)=>{
    if(idx<i) s.className='stage passed';
    else if(idx===i) s.className='stage '+status;
    else s.className='stage pending';
  });
  if(sub){ const el=st[i].querySelector('[data-sub]'); if(el) el.textContent=sub; }
  const ls=$('#live-stage'); if(ls) ls.textContent='Stage 0'+(i+1)+' · '+(name||STAGES[i]);
  const lt=$('#live-title'); if(lt && status!=='passed') lt.textContent=(name||STAGES[i])+(status==='running'?' in progress':(status==='failed'?' — issue detected':''));
}
function setLive(kind, text){
  if(kind==='task'){ const e=$('#live-task'); if(e) e.textContent=text; }
  if(kind==='op'){ const e=$('#live-op'); if(e) e.innerHTML='<b>$</b> '+esc(text); }
}
function appendLog(level, text){
  const tb=$('#term-body'); if(!tb) return;
  const cur=tb.querySelector('.cursor'); if(cur) cur.remove();
  const ts=new Date().toTimeString().slice(0,8);
  const ln=el('div','ln '+level,`<span class="ts">${ts}</span><span class="${level}">${esc(text)}</span><span class="cursor"></span>`);
  tb.appendChild(ln); tb.scrollTop=tb.scrollHeight;
}
function showDiag(kind, text){
  const box = kind==='fail'?$('#diag-fail'):$('#diag-recover');
  if(!box) return;
  box.querySelector('span:last-child').textContent=text;
  box.classList.add('show');
  if(kind==='fail'){ const r=$('#diag-recover'); if(r) r.classList.remove('show'); }
}
let agtN=0;
function appendAgent(role, text, detail){
  const list=$('#agt-list'); if(!list) return;
  agtN++;
  const cls = role.includes('Verification')?'tool':(text.includes('Recovery')||text.includes('Retrying')?'recover':(text.includes('Diagnos')||text.includes('fail')?'fail':'result'));
  const item=el('div','agt-item '+cls, `<div class="a-t">${new Date().toTimeString().slice(3,8)}</div>
    <div><div class="a-role">${esc(role)}</div><div class="a-text">${esc(text)}</div>
    ${detail?`<button class="a-toggle">+ Technical detail</button><div class="a-detail">${esc(detail)}</div>`:''}
    </div>`);
  list.appendChild(item);
  const tgl=item.querySelector('.a-toggle');
  if(tgl) tgl.addEventListener('click',()=>{ item.classList.toggle('exp'); tgl.textContent=item.classList.contains('exp')?'− Hide detail':'+ Technical detail'; });
  const c=$('#agt-count'); if(c) c.textContent=agtN+' decisions';
}
function appendArtifact(ev){
  const list=$('#art-list'); if(!list) return;
  if(list.querySelector('.faint')) list.innerHTML='';
  const row=el('div','art-row',`
    <div class="a-nm">${esc(ev.name)}<small>${esc(ev.desc)}</small></div>
    <div class="a-st"><span class="chk ${ev.check}">${ev.check}</span></div>
    <div class="a-sz">${esc(ev.size)}</div>
    <div class="a-st mono" style="color:var(--ink-faint)">${esc(ev.status)}</div>
    <div><button class="btn sm dl" data-name="${esc(ev.name)}">Download</button></div>`);
  list.appendChild(row);
  row.querySelector('.dl').addEventListener('click',()=>downloadArtifact(ev));
  const c=$('#art-count'); if(c) c.textContent=(list.querySelectorAll('.art-row').length)+' generated';
}
function renderMetrics(run){
  const card=$('#metrics-card'), grid=$('#metrics-grid');
  if(!card||!grid) return;
  card.style.display='block';
  grid.innerHTML = run.metrics.map(m=>`<div class="metric-cell"><div class="mv">${esc(m.value)}<small>${esc(m.unit)}</small></div><div class="ml">${esc(m.label)}</div><div class="mq">${esc(m.qualifier)}</div></div>`).join('');
}
function showOutcome(ev){
  const slot=$('#outcome-slot'); if(!slot) return;
  slot.innerHTML=`<div class="outcome-banner ${ev.kind}"><div class="o-ic">${ev.kind==='pass'?'✓':'!'}</div>
    <div><h3>${esc(ev.title)}</h3><p>${esc(ev.text)}</p></div></div>`;
  const lt=$('#live-title'); if(lt) lt.textContent='Run complete';
}
function downloadArtifact(ev){
  const content = `# SILICA artifact — ${ev.name}\n# ${ev.desc}\n# Status: ${ev.status} · Check: ${ev.check}\n# This is a placeholder file generated by the prototype frontend.\n# In production this streams from S3-compatible artifact storage via presigned URL.\n\n(generated sample content)\n`;
  const blob=new Blob([content],{type:'text/plain'});
  const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download=ev.name.split('/').pop(); a.click();
  toast('Download started', ev.name);
}

/* ---------------- History ---------------- */
function renderHistory(){
  const runs = Object.entries(state.runs).sort((a,b)=>(b[1].finishedAt||0)-(a[1].finishedAt||0));
  return `
  <div class="view-head"><div><h1 class="view-title">Past runs</h1><div class="view-sub" style="margin:0">Reopen any run to inspect stages, agent decisions, recoveries, and artifacts.</div></div></div>
  <div class="proj-list">
    <div class="proj-head"><span>Project / Run</span><span>Process node</span><span>Finished</span><span>Outcome</span><span></span></div>
    ${runs.map(([rid,r])=>{
      const p=state.projects.find(x=>x.id===r.projectId)||{name:'Unknown',node:'—'};
      return `<div class="proj-row" data-open-run="${rid}">
        <div><div class="p-name">${esc(p.name)}<small>run ${rid.slice(-4)} · ${r.recoveries||0} recoveries${r.failReason?' · '+esc(r.failReason.slice(0,40))+'…':''}</small></div></div>
        <div class="p-node">${esc(p.node)}</div>
        <div class="p-time">${r.finishedAt?timeAgo(r.finishedAt):'—'}</div>
        <div><span class="status ${r.status}"><span class="d"></span>${r.status}</span></div>
        <div><span class="kicker" style="color:var(--amber)">Inspect →</span></div>
      </div>`;
    }).join('')}
  </div>`;
}
function bindRows(){
  document.querySelectorAll('[data-open]').forEach(r=>r.addEventListener('click',()=>{
    const p=state.projects.find(x=>x.id===r.dataset.open); if(!p) return;
    state.activeRunId=null; state.openedRunId=p.runId; go('run');
  }));
  document.querySelectorAll('[data-open-run]').forEach(r=>r.addEventListener('click',()=>{
    state.activeRunId=null; state.openedRunId=r.dataset.openRun; go('run');
  }));
}

/* ---------------- Artifacts page ---------------- */
function renderArtifactsPage(){
  const all=[];
  Object.values(state.runs).forEach(r=>(r.artifacts||[]).forEach(a=>all.push(a)));
  if(!all.length) return `<div class="view-head"><div><h1 class="view-title">Artifacts</h1></div></div>
    <div class="empty"><span class="serif">No artifacts yet</span><p class="dim" style="max-width:380px;margin:0 auto">Start an engineering run and generated files — RTL, netlists, reports, GDSII — will appear here.</p><br><button class="btn primary" id="af-new">Start a new design</button></div>`;
  return `<div class="view-head"><div><h1 class="view-title">Artifacts</h1><div class="view-sub" style="margin:0">${all.length} generated files across runs.</div></div></div>
    <div class="card">${all.map(a=>`<div class="art-row"><div class="a-nm">${esc(a.name)}<small>${esc(a.desc)}</small></div><div class="a-st"><span class="chk ${a.check}">${a.check}</span></div><div class="a-sz">${esc(a.size)}</div><div class="a-st mono" style="color:var(--ink-faint)">${esc(a.status)}</div><div><button class="btn sm dl2" data-name="${esc(a.name)}">Download</button></div></div>`).join('')}</div>`;
}
function bindDownloads(){
  const b=$('#af-new'); if(b) b.addEventListener('click',()=>go('new'));
  document.querySelectorAll('.dl2').forEach(b=>b.addEventListener('click',()=>{
    const name=b.dataset.name; downloadArtifact({name, desc:'artifact', status:'generated', check:'pass'});
  }));
}

/* ---------------- Settings ---------------- */
function renderSettings(){
  return `<div class="view-head"><div><h1 class="view-title">Settings</h1></div></div>
  <div class="card" style="max-width:640px">
    <div class="card-head"><h3>Account</h3></div>
    <div class="field"><label>Signed in as</label><input type="text" value="Suhas Hanamannavar · webofjee@gmail.com" disabled></div>
    <div class="field"><label>Default process node</label><select><option>TSMC 16nm FinFET (illustrative)</option><option>SkyWater 130nm (open PDK)</option></select></div>
    <div class="field" style="margin-bottom:0"><label>Workspace</label><button class="btn" id="reset-state">Reset local prototype data</button></div>
  </div>
  <p class="dim" style="margin-top:16px;font-size:12.5px;max-width:640px">Prototype build: settings are stored locally in this browser. No EDA backend or user account system is connected.</p>`;
}
document.addEventListener('click', e=>{
  if(e.target.id==='reset-state'){ localStorage.removeItem(LS_KEY); load(); toast('Reset','Prototype data cleared and re-seeded.'); go('workspace'); }
  if(e.target.id==='ws-new') go('new');
  if(e.target.id==='ws-open'){ state.activeRunId=null; state.openedRunId=state.projects[0]&&state.projects[0].runId; go('run'); }
});

/* ---------------- Boot ---------------- */
render();
})();
