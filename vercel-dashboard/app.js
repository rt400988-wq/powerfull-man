const KEY='powerfull-man-demo-leads';
const seed=[{id:'demo-1',company:'Example Business',name:'Test Lead',consent:'test_consent',source:'manual demo',blocked:false}];
let leads=JSON.parse(localStorage.getItem(KEY)||'null')||seed;
const $=s=>document.querySelector(s);
function save(){localStorage.setItem(KEY,JSON.stringify(leads))}
function render(){
  $('#lead-count').textContent=leads.length;$('#consent-count').textContent=leads.filter(x=>['consented','opted_in','test_consent'].includes(x.consent)&&!x.blocked).length;$('#blocked-count').textContent=leads.filter(x=>x.blocked||x.consent==='opted_out').length;$('#event-count').textContent=Number(localStorage.getItem('pm-events')||0);
  $('#lead-table').innerHTML=leads.map(x=>`<tr><td><b>${x.company}</b></td><td>${x.name}</td><td class="${x.blocked?'blocked':'consent'}">${x.blocked?'blocked':x.consent}</td><td>${x.source}</td><td><button class="ghost" data-id="${x.id}">${x.blocked?'Restore':'Opt out'}</button></td></tr>`).join('');
  $('#lead-table').querySelectorAll('button').forEach(b=>b.onclick=()=>{const x=leads.find(y=>y.id===b.dataset.id);x.blocked=!x.blocked;x.consent=x.blocked?'opted_out':'test_consent';save();render();log(x.blocked?'Lead blocked':'Lead restored')});
}
function log(text){const n=Number(localStorage.getItem('pm-events')||0)+1;localStorage.setItem('pm-events',n);$('#activity').innerHTML=`<p>● ${text} · ${new Date().toLocaleString()}</p>`+$('#activity').innerHTML;render()}
function service(name,state,detail){return `<div class="service"><span class="dot ${state?'ok':'off'}"></span><span class="muted">${state?'ONLINE':'STANDBY'}</span><b>${name}</b><small>${detail}</small></div>`}
async function refresh(){let api='standby';try{const r=await fetch('/api/health');if(r.ok)api='online'}catch{}$('#services').innerHTML=service('Dashboard',true,'Vercel protected')+service('Supabase',false,'Ready to connect')+service('API',api==='online','Serverless check')+service('Outreach',false,'Inbox-only mode');$('#last-updated').textContent='Updated '+new Date().toLocaleTimeString()}
$('#add-demo').onclick=()=>{leads.push({id:'demo-'+Date.now(),company:'New Demo Co.',name:'Consenting Test',consent:'test_consent',source:'manual demo',blocked:false});save();log('Test lead added');render()};
$('#run-cycle').onclick=()=>{const eligible=leads.filter(x=>x.consent==='test_consent'&&!x.blocked).length;log(`Safe cycle checked ${eligible} consenting lead${eligible===1?'':'s'}`)};$('#refresh').onclick=()=>{render();refresh()};render();refresh();
