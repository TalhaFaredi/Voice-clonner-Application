import {api,BASE,setCSRF} from './services/api.js';
import {esc,toast,errorBox,icon,audio,number,badge} from './components/ui.js';
import {landing} from './pages/landing.js';
import {mountDemos} from './components/demos.js';
import {authPage} from './pages/auth.js';
import {layout} from './layouts/dashboard.js';
import {studio,voiceLibrary,clonePage,historyList,heading,billingPage,settingsPage} from './pages/workspace.js';

const app=document.getElementById('app');
let user=null, routeVersion=0, pollVersion=0;
const privatePages=new Set(['studio','voices','clone','history','billing','settings']);
const getPage=()=>location.hash.startsWith('#/')?(location.hash.slice(2).split('?')[0]||'home'):'home';
async function refreshUser(){ const result=await api('/auth/me');user=result.user;document.querySelectorAll('[data-user-credits]').forEach(el=>el.textContent=number(user.credits));return user; }
async function render(){
  const version=++routeVersion;pollVersion++;
  const page=getPage();
  if(privatePages.has(page)&&!user){location.hash='/login';return;}
  if(page==='home'){app.innerHTML=landing();mountDemos(app);return;}
  if(['login','register','forgot','reset'].includes(page)){app.innerHTML=authPage(page);return;}
  if(!privatePages.has(page)){location.hash='/';return;}
  app.innerHTML=layout(user,page,'<div class="loading" role="status"><span class="spinner"></span> Opening your workspace…</div>');
  try{
    await refreshUser();
    let content;
    if(page==='studio') {const [stats,voices,options]=await Promise.all([api('/dashboard'),api('/voices'),api('/studio/options')]); content=studio(user,stats,voices,options);}
    if(page==='voices')content=voiceLibrary(await api('/voices'));
    if(page==='clone')content=clonePage();
    if(page==='history')content=`${heading('EVERY GOOD TAKE, IN ONE PLACE','Your creations.','Listen again, download your audio, or make room for something new.')}<section>${historyList(await api('/jobs'))}</section><button class="button outline" id="history-next" data-page="1">Load older creations</button>`;
    if(page==='billing')content=billingPage(await api('/billing'),await api('/plans'));
    if(page==='settings')content=settingsPage(user);
    if(version!==routeVersion)return;
    app.innerHTML=layout(user,page,content);
    if(page==='history'||page==='voices')watchQueue(page,version);
  }catch(error){if(version!==routeVersion)return;if(error.status===401){user=null;location.hash='/login';return;}app.innerHTML=layout(user,page,errorBox(error.message)+'<button class="button outline" data-action="reload">Try again</button>');}
}

async function watchQueue(page,version){
  const jobs=await api('/jobs').catch(()=>[]);
  if(!jobs.some(j=>['queued','processing'].includes(j.status)))return;
  setTimeout(()=>{if(version===routeVersion&&getPage()===page)render();},6000);
}

async function watchJob(id){
  const version=++pollVersion;
  while(version===pollVersion){
    try{
      const job=await api('/jobs/'+id);if(version!==pollVersion)return;
      const target=document.getElementById('active-job');if(!target)return;
      target.innerHTML=`<div class="job-progress"><div>${icon(job.kind==='clone'?'mic':'sound')}<strong>${job.status==='completed'?(job.kind==='clone'?'Your voice is ready.':'Your words, brought to life.'):job.status==='failed'?'Something interrupted this take.':'Your audio is on its way.'}</strong>${badge(job.status)}</div><p>${job.status==='queued'?'Safely queued. The audio worker will pick this up shortly.':job.status==='processing'?'The voice engine is working. You can keep exploring your workspace.':job.status==='failed'?esc(job.error):job.kind==='clone'?'<a href="#/voices">Open your voice library →</a>':'Your audio is saved in your history.'}</p>${job.status==='completed'&&job.kind==='generate'?audio(job.id,BASE):''}</div>`;
      if(['completed','failed'].includes(job.status)){
        await refreshUser();document.querySelectorAll('[data-user-credits]').forEach(el=>el.textContent=number(user.credits));
        toast(job.status==='completed'?'Your audio job is complete.':job.error,job.status==='failed');return;
      }
    }catch(error){toast(error.message,true);return;}
    await new Promise(resolve=>setTimeout(resolve,2500));
  }
}

app.addEventListener('input',event=>{if(event.target.id==='script'){document.getElementById('char-count').textContent=[...event.target.value].length;document.getElementById('credit-cost').textContent=number([...event.target.value.trim()].length)+' credits';}});
app.addEventListener('change',event=>{if(event.target.id==='sample'){const label=event.target.closest('.upload-zone').querySelector('strong');label.textContent=event.target.files[0]?.name||'Drop your voice sample here';}});
app.addEventListener('submit',async event=>{
  event.preventDefault();
  const form=event.target,button=form.querySelector('[type="submit"],button'),errorEl=form.querySelector('.form-error');
  const values=Object.fromEntries(new FormData(form));if(errorEl)errorEl.textContent='';
  const original=button.innerHTML;button.disabled=true;button.textContent='Working…';
  try{
    if(form.id==='auth-form'){
      const page=form.dataset.page;
      const path={login:'/auth/login',register:'/auth/register',forgot:'/auth/forgot-password',reset:'/auth/reset-password'}[page];
      if(page==='reset')values.token=new URLSearchParams(location.hash.split('?')[1]||'').get('token')||'';
      const result=await api(path,{method:'POST',data:values});
      if(result.user){user=result.user;location.hash='/studio';}
      else {toast(result.message);if(page==='reset')location.hash='/login';}
    }
    if(form.id==='generation-form'){
      const [kind,value]=values.voice.split(':');delete values.voice;
      values[kind==='clone'?'voice_id':'speaker']=value;
      const job=await api('/generations',{method:'POST',data:values,key:form.dataset.key||=crypto.randomUUID()});
      delete form.dataset.key;await refreshUser();watchJob(job.id);
    }
    if(form.id==='clone-form'){
      const data=new FormData(form);data.set('consent',form.elements.consent.checked?'true':'false');
      const job=await api('/voices',{method:'POST',data,key:form.dataset.key||=crypto.randomUUID()});
      delete form.dataset.key;await refreshUser();watchJob(job.id);
    }
    if(form.id==='profile-form'){const result=await api('/account',{method:'PATCH',data:values});user=result.user;toast('Your profile is updated.');render();}
    if(form.id==='password-form'){const result=await api('/account/password',{method:'POST',data:values});user=result.user;toast('Password updated. Other sessions have been signed out.');form.reset();}
  }catch(error){if(errorEl)errorEl.textContent=error.message;else toast(error.message,true);if(error.status&&error.status<500)delete form.dataset.key;}
  finally{button.disabled=false;button.innerHTML=original;}
});

app.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action],#history-next');if(!button)return;
  const action=button.dataset.action;button.disabled=true;
  try{
    if(action==='logout'){await api('/auth/logout',{method:'POST',data:{}});user=null;setCSRF('');location.hash='/';}
    if(action==='reload')await render();
    if(action==='rename-voice'){
      const name=prompt('A new name for this voice',button.dataset.name);if(!name)return;
      await api('/voices/'+button.dataset.id,{method:'PATCH',data:{name}});toast('Voice renamed.');render();
    }
    if(action==='delete-voice'||action==='delete-job'){
      if(!confirm(action==='delete-voice'?'Delete this voice and its reference sample? Generated audio stays in your history.':'Delete this item and its generated audio?'))return;
      await api((action==='delete-voice'?'/voices/':'/jobs/')+button.dataset.id,{method:'DELETE'});toast('Deleted.');render();
    }
    if(action==='checkout'){
      const result=await api('/billing/checkout',{method:'POST',data:{plan:button.dataset.plan,interval:document.getElementById('billing-interval').value}});
      location.assign(result.url);
    }
    if(action==='portal'){const result=await api('/billing/portal',{method:'POST',data:{}});location.assign(result.url);}
    if(button.id==='history-next'){
      const jobs=await api('/jobs?page='+button.dataset.page);button.dataset.page=Number(button.dataset.page)+1;
      if(!jobs.length){button.hidden=true;toast('You’ve reached the start of your history.');return;}
      button.insertAdjacentHTML('beforebegin',historyList(jobs));
    }
  }catch(error){toast(error.message,true);}finally{button.disabled=false;}
});

window.addEventListener('hashchange',()=>{if(!location.hash.startsWith('#/')&&document.getElementById(location.hash.slice(1)))return;window.scrollTo(0,0);render();});
// Marketing and authentication pages never wait on an API roundtrip to become visible.
if(!privatePages.has(getPage()))render();
else app.innerHTML='<main class="loading" role="status"><span class="spinner"></span> Opening your workspace…</main>';
try{await refreshUser();}catch(error){if(error.status!==401)toast(error.message,true);}
if(privatePages.has(getPage()))render();
