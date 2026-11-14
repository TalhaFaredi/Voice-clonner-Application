import {heading} from './workspace.js';
import {icon,esc} from '../components/ui.js';
import {voiceCards} from './voices.js';

export function clonePage(voices,options={}){
  const langs=options.transcribe_languages||{auto:'Detect automatically'};
  const sttNote=options.transcribe_ready===false?'Automatic transcription is not configured (OPENROUTER_API_KEY missing). Type the transcript yourself.':'After you choose a file, it is transcribed automatically with MAI-Transcribe-2.';
  return `${heading('SOMETHING ONLY YOU CAN SAY','Create a voice of your own.','Upload a recording, create a reusable clone, and hear a real generated sample.')}
    <div class="clone-grid"><section class="panel"><div class="panel-title"><h2>Create a saved voice</h2><span class="badge">1,000 credits · sample included</span></div>
      <form id="clone-form">
        <label>Voice name<input name="name" placeholder="e.g. My storytelling voice" maxlength="80" required></label>
        <label class="upload-zone" for="sample">${icon('mic')}<strong>Choose your voice recording</strong><span>One speaker, clear speech, no background music</span><small>WAV, MP3, M4A, OGG, FLAC, WebM · Max 20 MB · 3–120 seconds</small><input id="sample" name="audio" type="file" accept=".wav,.mp3,.m4a,.ogg,.flac,.webm" required></label>
        <audio id="upload-preview" controls hidden preload="metadata"></audio>
        <div class="form-row transcribe-row"><label>Language spoken in the recording<select id="transcribe-language" name="transcribe_language" data-names="${esc(JSON.stringify(langs))}">${Object.entries(langs).map(([code,name])=>`<option value="${esc(code)}">${esc(name)}</option>`).join('')}</select></label><button type="button" class="button outline" id="retranscribe" hidden>${icon('sound')} Transcribe again</button></div>
        <p class="transcribe-status" id="transcribe-status">${esc(sttNote)}</p>
        <label>Cloning method<select name="clone_mode"><option value="text_conditioned">Accurate clone · recording + transcript · takes longer</option><option value="speaker_embedding">Fast voice-only clone · no transcript · lower similarity</option></select></label>
        <div class="mode-compare" role="note"><div><strong>${icon('check')} With transcription · more accurate</strong><p>Uses your recording and its exact transcript, so the clone sounds closer to the original voice. It can take some time, because the recording is transcribed first and the model does more work.</p></div><div><strong>${icon('arrow')} Without transcription · faster</strong><p>Uses only the sound of the voice, so it usually finishes earlier, but similarity may be lower.</p></div><small>Processing time depends on the model and your hardware (CPU or GPU). For speed, choose voice-only. For the best match, choose the transcription version.</small></div>
        <label id="reference-transcript-label">Transcription of the recording <span class="muted">(edit if anything is wrong)</span><textarea name="ref_text" maxlength="4000" required rows="5" placeholder="The transcription of your uploaded recording appears here. You can also type it yourself."></textarea></label>
        <p class="reference-guidance" id="reference-guidance">Matching the transcript to the recording helps preserve the voice. A different script here can reduce accuracy. Use 10–30 seconds of clean, natural speech when possible.</p>
        <label>Text to speak in your cloned voice <span class="muted">(used for the generated sample)</span><textarea name="preview_text" maxlength="250" rows="3" placeholder="Hello. This is a short preview of my saved voice."></textarea></label>
        <p class="reference-guidance">Write up to 250 characters in a supported language. This is the new speech your clone will say. Leave it empty to use the default sentence.</p>
        <label class="checkbox"><input type="checkbox" name="consent" required><span>I own this voice, or have explicit permission from its owner to create and use a clone.</span></label>
        <div class="form-error" role="alert"></div><div class="editor-bottom"><span class="privacy-note">${icon('check')} Saved privately to your account</span><button class="button dark" type="submit">Create & save voice ${icon('arrow')}</button></div>
      </form><div id="active-job"></div>
    </section><aside class="tips-panel"><span class="eyebrow">A BETTER MATCH STARTS HERE</span><h2>Hear your clone.<br>Then give it a script.</h2><ol><li><b>Upload a clear recording.</b><p>Use one speaker without music, long silence, or strong background noise.</p></li><li><b>Match its exact words.</b><p>The reference transcript must describe what the recording actually says. Enter new speech later in the studio.</p></li><li><b>Listen to the generated sample.</b><p>After processing, the clone is saved below with a synthesized preview. Original recordings are labeled separately.</p></li><li><b>Choose “Use this voice”.</b><p>The studio will select your clone instead of a preset narrator.</p></li></ol></aside></div>
    <section class="saved-clones-section"><div class="section-heading"><h2>Your saved clones</h2><a href="#/voices">View full library ${icon('arrow')}</a></div><div id="saved-voices">${voiceCards(voices)}</div></section>`;
}
