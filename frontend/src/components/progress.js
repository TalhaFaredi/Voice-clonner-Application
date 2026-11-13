import {esc,icon,waves,audio} from './ui.js';
import {BASE} from '../services/api.js';

const phases={preparing:'Preparing your recording',building_voice:'Learning the voice',
  creating_preview:'Generating a sample in your cloned voice',synthesizing:'Generating speech',saving:'Saving your audio'};

export function jobProgress(job,worker=null){
  if(['preview','rebuild'].includes(job.kind))job={...job,kind:'clone'};
  const complete=job.status==='completed',failed=job.status==='failed',waiting=job.status==='queued';
  const title=complete?(job.kind==='clone'?'Voice saved and ready to use':'Your speech is ready'):
    failed?'This attempt could not finish':waiting?'Getting your voice ready':phases[job.phase]||'Creating your audio';
  let message=complete?(job.kind==='clone'?'Saved to your private library. Listen to the generated sample or use this voice in the studio.':'Your recording is saved in your history.'):
    failed?job.error:waiting?(worker?.status==='loading'?'The voice models are warming up. Your saved job will start when they are ready.':!worker?'The audio worker is offline. Your job is safely saved and will start when it reconnects.':'Waiting for the audio engine to finish its current work. This page updates automatically.'):
    job.phase==='creating_preview'?'The clone is built. We are now synthesizing a real sample so you can hear it.':'You can leave this page; your voice and job progress stay saved.';
  const percent=Math.min(100,Math.max(0,job.progress||0));
  return `<section class="clone-progress ${complete?'is-complete':failed?'is-failed':'is-active'}" role="status" aria-live="polite" data-job-id="${esc(job.id)}" data-state="${esc(job.status)}">
    <div class="progress-heading"><span class="progress-symbol">${complete?icon('check'):failed?'!':icon('mic')}</span><div><strong>${title}</strong><p>${esc(message)}</p>${job.voice_label?`<small>${esc(job.voice_label)}</small>`:''}</div>${!complete&&!failed?'<span class="progress-spinner" aria-label="Processing"></span>':''}</div>
    ${!complete&&!failed?`<div class="progress-wave">${waves(35)}</div><div class="clone-progress-track ${waiting?'indeterminate':''}" role="progressbar" aria-label="Audio processing" ${waiting?'aria-valuetext="Waiting for audio engine"':`aria-valuenow="${percent}" aria-valuemin="0" aria-valuemax="100"`}><span class="fill-${waiting?'waiting':Math.round(percent/5)*5}"></span></div><div class="progress-steps"><span class="done">Recording saved</span><span class="${!waiting?'done':''}">Voice processing</span><span>Ready to listen</span></div>`:''}
    ${complete&&job.kind==='clone'?`<div class="completed-actions"><a class="button dark" href="#/studio?voice=${esc(job.voice_id)}">Use this voice ${icon('arrow')}</a><a class="button outline" href="#/voices">Open voice library</a></div>`:''}
    ${complete&&job.kind==='generate'?audio(job.id,BASE):''}
  </section>`;
}
