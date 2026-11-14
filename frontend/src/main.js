import {api,BASE,setCSRF} from './services/api.js';
import {esc,toast,errorBox,icon,audio,number,badge} from './components/ui.js';
import {landing} from './pages/landing.js';
import {mountDemos} from './components/demos.js';
import {authPage} from './pages/auth.js';
import {layout} from './layouts/dashboard.js';
import {studio,historyList,heading,billingPage,settingsPage} from './pages/workspace.js';
import {voiceLibrary,voiceCards} from './pages/voices.js';
import {clonePage} from './pages/clone.js';
import {jobProgress} from './components/progress.js';

const app=document.getElementById('app');
let user=null, routeVersion=0, pollVersion=0;
let pageVoices=[],workerState=null,uploadURL=null;
const savedKey=kind=>`sonora:${user.id}:${kind}`;
const privatePages=new Set(['studio','voices','clone','history','billing','settings']);
const getPage=()=>location.hash.startsWith('#/')?(location.hash.slice(2).split('?')[0]||'home'):'home';
async function refreshUser(){ const result=await api('/auth/me');user=result.user;document.querySelectorAll('[data-user-credits]').forEach(el=>el.textContent=number(user.credits));return user; }
async function render(){
  const version=++routeVersion;pollVersion++;
  if(uploadURL){URL.revokeObjectURL(uploadURL);uploadURL=null;}
  const page=getPage();
  if(privatePages.has(page)&&!user){location.hash='/login';return;}
  if(page==='home'){app.innerHTML=landing();mountDemos(app);return;}
  if(['login','register','forgot','reset'].includes(page)){app.innerHTML=authPage(page);return;}
  if(!privatePages.has(page)){location.hash='/';return;}
  app.innerHTML=layout(user,page,'<div class="loading" role="status"><span class="spinner"></span> Opening your workspace…</div>');
  try{
    await refreshUser();
    let content;
    if(page==='studio') {const [stats,voices,options]=await Promise.all([api('/dashboard'),api('/voices'),api('/studio/options')]); pageVoices=voices;workerState=options.worker;content=studio(user,stats,voices,options);}
    if(page==='voices'){pageVoices=await api('/voices');content=voiceLibrary(pageVoices);}
    if(page==='clone'){const [voices,options]=await Promise.all([api('/voices'),api('/studio/options')]);pageVoices=voices;content=clonePage(voices,options);}
    if(page==='history')content=`${heading('EVERY GOOD TAKE, IN ONE PLACE','Your creations.','Listen again, download your audio, or make room for something new.')}<section>${historyList(await api('/jobs'))}</section><button class="button outline" id="history-next" data-page="1">Load older creations</button>`;
    if(page==='billing')content=billingPage(await api('/billing'),await api('/plans'));
    if(page==='settings')content=settingsPage(user);
    if(version!==routeVersion)return;
    app.innerHTML=layout(user,page,content);
    if(page==='history')watchQueue(page,version);
    if(page==='studio'){
      setupStudioVoice();
      const id=sessionStorage.getItem(savedKey('generation-job'));
      if(id){
        const previous=await api('/jobs/'+id).catch(()=>null);
        const selected=app.querySelector('#generation-form select[name=voice]')?.value;
        const previousVoice=previous?.voice_id?`clone:${previous.voice_id}`:`preset:${previous?.speaker}`;
        if(version===routeVersion&&previous&&previousVoice===selected)watchJob(id);
      }
    }
    if(page==='clone'||page==='voices')watchSavedVoices(version,page);
  }catch(error){if(version!==routeVersion)return;if(error.status===401){user=null;location.hash='/login';return;}app.innerHTML=layout(user,page,errorBox(error.message)+'<button class="button outline" data-action="reload">Try again</button>');}
}

function setupStudioVoice(){
  const select=app.querySelector('#generation-form select[name=voice]');if(!select)return;
  const requested=new URLSearchParams(location.hash.split('?')[1]||'').get('voice');
  const ready=pageVoices.filter(v=>v.status==='ready');
  const remembered=localStorage.getItem(savedKey('selected-voice'));
  const choice=requested?`clone:${requested}`:remembered|| (ready.length?`clone:${ready[0].id}`:'preset:ryan');
  if([...select.options].some(o=>o.value===choice))select.value=choice;
  else if(requested){select.value='';toast('That saved voice is not ready or no longer exists. Please choose a voice.',true);}
  else select.value=ready.length?`clone:${ready[0].id}`:'preset:ryan';
  const note=document.createElement('p');note.id='voice-selection-note';note.className='voice-selection-note';
  select.closest('.form-row').after(note);
  updateVoiceSelection();
}

function updateVoiceSelection(){
  const select=app.querySelector('#generation-form select[name=voice]');if(!select)return;
  const [type,id]=select.value.split(':');
  pollVersion++;
  const oldResult=document.getElementById('active-job');if(oldResult)oldResult.replaceChildren();
  const voice=pageVoices.find(v=>v.id===id);
  const note=document.getElementById('voice-selection-note');
  note.classList.toggle('preset-selected',type!=='clone');
  note.textContent=type==='clone'?`Using your saved clone: ${voice?.name||'selected voice'}. No preset narrator will be used.`:
    select.value?`Using preset narrator: ${id.replaceAll('_',' ')}. Choose a saved clone above to use your own voice.`:'Choose a voice to continue.';
  const instruct=app.querySelector('#generation-form input[name=instruct]');instruct.disabled=type==='clone';
  app.querySelector('#generation-form button[type=submit]').disabled=!select.value;
  if(select.value)localStorage.setItem(savedKey('selected-voice'),select.value);
}

async function refreshSavedVoices(page,version){
  const [voices,options]=await Promise.all([api('/voices'),api('/studio/options')]);
  if(version!==routeVersion||getPage()!==page)return;
  pageVoices=voices;workerState=options.worker;
  const target=document.getElementById('saved-voices');if(!target)return;
  const signature=JSON.stringify(voices.map(v=>[v.id,v.name,v.status,v.preview_url,v.preview_error,v.latest_job?.progress]));
  if(target.dataset.signature!==signature){
    let grid=target.querySelector('.voice-grid');
    if(!grid||!voices.length){target.innerHTML=voiceCards(voices);grid=target.querySelector('.voice-grid');}
    if(grid){
      for(const old of [...grid.children])if(!voices.some(v=>v.id===old.dataset.voiceId))old.remove();
      voices.forEach((voice,index)=>{
        const key=JSON.stringify([voice.name,voice.status,voice.preview_url,voice.preview_error,voice.latest_job?.progress,voice.ref_text,voice.clone_mode]);
        let card=grid.querySelector(`[data-voice-id="${voice.id}"]`);
        if(card?.dataset.signature!==key){
          const template=document.createElement('template');template.innerHTML=voiceCards([voice]);
          const replacement=template.content.querySelector('article');replacement.dataset.signature=key;
          if(card)card.replaceWith(replacement);else grid.insertBefore(replacement,grid.children[index]||null);
          card=replacement;
        }
      });
    }
    target.dataset.signature=signature;
  }
  if(page==='clone'){
    const id=sessionStorage.getItem(savedKey('clone-job'));
    let job=voices.find(v=>['queued','processing'].includes(v.latest_job?.status))?.latest_job;
    job ||= voices.find(v=>v.latest_job?.id===id)?.latest_job;
    job ||= voices[0]?.latest_job;
    if(job){
      const progress=document.getElementById('active-job');
      const progressSignature=JSON.stringify([job.id,job.status,job.phase,job.progress,job.error,workerState?.status]);
      if(progress.dataset.signature!==progressSignature){progress.innerHTML=jobProgress(job,workerState);progress.dataset.signature=progressSignature;}
      const busy=['queued','processing'].includes(job.status);
      const button=app.querySelector('#clone-form button[type=submit]');button.disabled=busy;
      button.innerHTML=busy?'Creating your saved voice…':`Create & save voice ${icon('arrow')}`;
      if(job.status==='completed'&&sessionStorage.getItem(savedKey('clone-notified'))!==job.id){
        sessionStorage.setItem(savedKey('clone-notified'),job.id);
        localStorage.setItem(savedKey('selected-voice'),`clone:${job.voice_id}`);await refreshUser();
      }
    }
  }
}

async function watchSavedVoices(version,page){
  while(version===routeVersion&&getPage()===page){
    try{await refreshSavedVoices(page,version);}catch(error){if(version===routeVersion)toast(error.message,true);}
    await new Promise(resolve=>setTimeout(resolve,3000));
  }
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
      const voice=pageVoices.find(v=>v.id===job.voice_id);
      target.innerHTML=jobProgress({...job,voice_label:job.voice_id?`Saved clone: ${voice?.name||'your voice'}`:`Preset narrator: ${job.speaker}`},workerState);
      if(['completed','failed'].includes(job.status)){
        await refreshUser();document.querySelectorAll('[data-user-credits]').forEach(el=>el.textContent=number(user.credits));
        toast(job.status==='completed'?'Your audio job is complete.':job.error,job.status==='failed');return;
      }
    }catch(error){toast(error.message,true);return;}
    await new Promise(resolve=>setTimeout(resolve,2500));
  }
}

let transcribeRun=0;
async function transcribeSample(){
  const file=document.getElementById('sample')?.files[0];if(!file)return;
  const run=++transcribeRun,status=document.getElementById('transcribe-status');
  const textarea=app.querySelector('#clone-form textarea[name=ref_text]');
  const language=document.getElementById('transcribe-language').value;
  const mode=app.querySelector('#clone-form select[name=clone_mode]');
  if(mode.value!=='text_conditioned'){mode.value='text_conditioned';mode.dispatchEvent(new Event('change',{bubbles:true}));}
  status.className='transcribe-status is-working';status.innerHTML='<span class="mini-spinner"></span>Transcribing your recording with MAI-Transcribe-2…';
  textarea.readOnly=true;
  const data=new FormData();data.set('audio',file);data.set('language',language);
  try{
    const result=await api('/voices/transcribe',{method:'POST',data});
    if(run!==transcribeRun)return;
    textarea.value=result.text;
    const names=JSON.parse(document.getElementById('transcribe-language').dataset.names||'{}');
    const detected=result.detected_language?` · detected: ${result.detected_language}`:'';
    status.className='transcribe-status is-done';
    status.textContent=`Transcribed (${language==='auto'?'auto-detected language':names[language]||language}${detected}). Check it below and fix any mistakes.`;
  }catch(error){
    if(run!==transcribeRun)return;
    status.className='transcribe-status is-failed';status.textContent=error.message+' You can still type the transcript yourself.';
  }finally{if(run===transcribeRun)textarea.readOnly=false;}
}

app.addEventListener('input',event=>{if(event.target.id==='script'){document.getElementById('char-count').textContent=[...event.target.value].length;document.getElementById('credit-cost').textContent=number([...event.target.value.trim()].length)+' credits';}});
app.addEventListener('change',event=>{
  if(event.target.id==='sample'){
    const file=event.target.files[0];const label=event.target.closest('.upload-zone').querySelector('strong');label.textContent=file?.name||'Choose your voice recording';
    if(uploadURL)URL.revokeObjectURL(uploadURL);
    const preview=document.getElementById('upload-preview');preview.hidden=!file;
    if(file){uploadURL=URL.createObjectURL(file);preview.src=uploadURL;}
    document.getElementById('retranscribe').hidden=!file;
    if(file)transcribeSample();
  }
  if(event.target.id==='transcribe-language'&&document.getElementById('sample')?.files[0])transcribeSample();
  if(event.target.matches('#generation-form select[name=voice]'))updateVoiceSelection();
  if(event.target.matches('#clone-form select[name=clone_mode]')){
    const accurate=event.target.value==='text_conditioned';
    const transcript=app.querySelector('#clone-form textarea[name=ref_text]');transcript.required=accurate;transcript.disabled=!accurate;
    document.getElementById('reference-transcript-label').hidden=!accurate;
    document.getElementById('reference-guidance').textContent=accurate?'More accurate, but takes longer. Check that the transcript matches exactly what is spoken in the recording, not the new speech you want to generate.':
      'Faster: voice-only mode skips the transcript and uses only the sound of the voice, so it usually finishes earlier. Similarity may be lower than the transcription version.';
  }
});
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
      sessionStorage.setItem(savedKey('generation-job'),job.id);
      delete form.dataset.key;await refreshUser();watchJob(job.id);
    }
    if(form.id==='clone-form'){
      const data=new FormData(form);data.set('consent',form.elements.consent.checked?'true':'false');
      const job=await api('/voices',{method:'POST',data,key:form.dataset.key||=crypto.randomUUID()});
      sessionStorage.setItem(savedKey('clone-job'),job.id);
      delete form.dataset.key;await refreshUser();
      document.getElementById('active-job').innerHTML=jobProgress(job,workerState);
      await refreshSavedVoices('clone',routeVersion);
    }
    if(form.id==='profile-form'){const result=await api('/account',{method:'PATCH',data:values});user=result.user;toast('Your profile is updated.');render();}
    if(form.id==='password-form'){const result=await api('/account/password',{method:'POST',data:values});user=result.user;toast('Password updated. Other sessions have been signed out.');form.reset();}
    if(form.classList.contains('rebuild-voice-form')){
      const job=await api('/voices/'+form.dataset.voiceId+'/rebuild',{method:'POST',data:values,key:form.dataset.key||=crypto.randomUUID()});
      sessionStorage.setItem(savedKey('clone-job'),job.id);delete form.dataset.key;
      await refreshSavedVoices(getPage(),routeVersion);
      toast('Rebuilding your saved voice with the corrected reference. No extra credits charged.');
    }
  }catch(error){if(errorEl)errorEl.textContent=error.message;else toast(error.message,true);if(error.status&&error.status<500)delete form.dataset.key;}
  finally{if(form.id!=='clone-form'||!document.querySelector('.clone-progress.is-active')){button.disabled=false;button.innerHTML=original;}}
});

app.addEventListener('click',event=>{if(event.target.closest('#retranscribe')){event.preventDefault();transcribeSample();}});
app.addEventListener('click',async event=>{
  const button=event.target.closest('[data-action],#history-next');if(!button)return;
  const action=button.dataset.action;button.disabled=true;
  try{
    if(action==='logout'){await api('/auth/logout',{method:'POST',data:{}});user=null;setCSRF('');location.hash='/';}
    if(action==='reload')await render();
    if(action==='preview-voice'){
      const job=await api('/voices/'+button.dataset.id+'/preview',{method:'POST',data:{}});
      if(job.id)sessionStorage.setItem(savedKey('clone-job'),job.id);
      await refreshSavedVoices(getPage(),routeVersion);
      toast(job.already_ready?'Your generated sample is available.':'Creating a sample with your saved clone. No extra credits are charged.');
    }
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
