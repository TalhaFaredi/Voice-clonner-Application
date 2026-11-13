import {esc,date,icon,empty} from '../components/ui.js';
import {BASE} from '../services/api.js';
import {heading} from './workspace.js';

function mediaURL(path){return BASE.replace(/\/api\/?$/,'')+path;}

export function voiceCards(voices){
  if(!voices.length)return empty('Your saved voices will appear here.','Create a clone above. It stays in your account after you reload or sign in again.');
  return `<div class="voice-grid saved-voice-grid">${voices.map((v,i)=>{
    const active=['queued','processing'].includes(v.status)||['queued','processing'].includes(v.latest_job?.status),ready=v.status==='ready';
    const label=active&&ready?'Creating sample':ready?'Saved & ready':v.status==='failed'?'Needs attention':v.latest_job?.status==='processing'?'Creating voice':'Waiting to start';
    return `<article class="voice-card saved-voice-card ${active?'voice-in-progress':''}" data-voice-id="${esc(v.id)}">
      <div class="voice-top"><span class="voice-avatar tone-${i%4}">${esc(v.name[0].toUpperCase())}</span><span class="badge ${esc(v.status)}">${active?'<span class="mini-spinner"></span>':''}${label}</span></div>
      <h2>${esc(v.name)}</h2><p>Private saved clone · ${date(v.created_at)}</p>
      <p class="clone-mode">${v.clone_mode==='text_conditioned'?'Recording + transcript':'Voice-only embedding'}${v.reference_duration?' · '+v.reference_duration.toFixed(1)+'s reference':''}</p>
      ${ready?`<a class="button dark full use-saved-voice" href="#/studio?voice=${esc(v.id)}">Use this voice ${icon('arrow')}</a>`:''}
      ${v.preview_url?`<div class="voice-preview"><label>Generated clone sample</label><audio controls preload="none" crossorigin="use-credentials" src="${esc(mediaURL(v.preview_url))}"></audio><small>This is synthesized speech using the saved clone.</small></div>`:active?'<div class="voice-pending"><span class="progress-spinner"></span><span>Your recording is saved. Creating the clone and its preview…</span></div>':ready?'<p class="voice-tip">Use this voice in the studio to generate and hear new speech.</p>':''}
      ${ready&&!active&&!v.preview_url?`<button class="button outline full" data-action="preview-voice" data-id="${esc(v.id)}">Create included voice sample</button>`:''}
      ${v.preview_error?`<p class="voice-tip">${esc(v.preview_error)}</p>`:''}
      ${v.status==='failed'?`<p class="inline-error">${esc(v.latest_job?.error||'The clone could not be created. Credits were returned; try a clearer sample.')}</p>`:''}
      <details class="reference-details"><summary>Original reference recording</summary><audio controls preload="none" crossorigin="use-credentials" src="${esc(mediaURL(v.reference_url||'/api/audio/voice/'+v.id))}"></audio><small>This is your upload, not generated clone speech.</small></details>
      ${!active?`<details class="reference-details"><summary>Correct transcript / rebuild voice</summary><form class="rebuild-voice-form" data-voice-id="${esc(v.id)}"><label>Exact words in this recording<textarea name="ref_text" maxlength="4000">${esc(v.ref_text)}</textarea></label><label>Cloning method<select name="clone_mode"><option value="text_conditioned" ${v.clone_mode==='text_conditioned'?'selected':''}>Recording + exact transcript</option><option value="speaker_embedding" ${v.clone_mode==='speaker_embedding'?'selected':''}>Voice only · lower similarity</option></select></label><small>No extra credits. Up to three corrections are included. Your original transcript and previous prompt are preserved.</small><div class="form-error" role="alert"></div><button type="submit" class="button outline full">Rebuild this saved voice</button></form></details>`:''}
      <div class="voice-actions"><button class="text-button" data-action="rename-voice" data-id="${esc(v.id)}" data-name="${esc(v.name)}">Rename</button><button class="text-button danger" data-action="delete-voice" data-id="${esc(v.id)}" ${active?'disabled':''}>Delete</button></div>
    </article>`;
  }).join('')}</div>`;
}

export function voiceLibrary(voices){
  return `${heading('A COLLECTION THAT SOUNDS LIKE YOU','Your voice library.','Your clones are saved to this account and ready to use in the studio.',`<a class="button dark" href="#/clone">${icon('plus')} Clone a voice</a>`)}<section id="saved-voices">${voiceCards(voices)}</section>`;
}
