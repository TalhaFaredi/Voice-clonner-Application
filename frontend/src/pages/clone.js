import {heading} from './workspace.js';
import {icon} from '../components/ui.js';
import {voiceCards} from './voices.js';

export function clonePage(voices){
  return `${heading('SOMETHING ONLY YOU CAN SAY','Create a voice of your own.','Upload a recording, create a reusable clone, and hear a real generated sample.')}
    <div class="clone-grid"><section class="panel"><div class="panel-title"><h2>Create a saved voice</h2><span class="badge">1,000 credits · sample included</span></div>
      <form id="clone-form">
        <label>Voice name<input name="name" placeholder="e.g. My storytelling voice" maxlength="80" required></label>
        <label class="upload-zone" for="sample">${icon('mic')}<strong>Choose your voice recording</strong><span>One speaker, clear speech, no background music</span><small>WAV, MP3, M4A, OGG, FLAC, WebM · Max 20 MB · 3–120 seconds</small><input id="sample" name="audio" type="file" accept=".wav,.mp3,.m4a,.ogg,.flac,.webm" required></label>
        <audio id="upload-preview" controls hidden preload="metadata"></audio>
        <label>Cloning method<select name="clone_mode"><option value="text_conditioned">Accurate clone · recording + exact transcript</option><option value="speaker_embedding">Quick voice-only clone · lower similarity</option></select></label>
        <label id="reference-transcript-label">Exact words spoken in the recording<textarea name="ref_text" maxlength="4000" required placeholder="Transcribe the uploaded recording exactly. This is NOT the new speech you want to generate."></textarea></label>
        <p class="reference-guidance" id="reference-guidance">Matching the transcript to the recording helps preserve the voice. A different script here can reduce accuracy. Use 10–30 seconds of clean, natural speech when possible.</p>
        <details class="reference-details"><summary>Change the included sample sentence (optional)</summary><label>New speech for the generated sample<textarea name="preview_text" maxlength="250" placeholder="Hello. This is a short preview of my saved voice."></textarea></label><small>Write this short sentence in your preferred supported language. This is separate from the recording transcript.</small></details>
        <label class="checkbox"><input type="checkbox" name="consent" required><span>I own this voice, or have explicit permission from its owner to create and use a clone.</span></label>
        <div class="form-error" role="alert"></div><div class="editor-bottom"><span class="privacy-note">${icon('check')} Saved privately to your account</span><button class="button dark" type="submit">Create & save voice ${icon('arrow')}</button></div>
      </form><div id="active-job"></div>
    </section><aside class="tips-panel"><span class="eyebrow">A BETTER MATCH STARTS HERE</span><h2>Hear your clone.<br>Then give it a script.</h2><ol><li><b>Upload a clear recording.</b><p>Use one speaker without music, long silence, or strong background noise.</p></li><li><b>Match its exact words.</b><p>The reference transcript must describe what the recording actually says. Enter new speech later in the studio.</p></li><li><b>Listen to the generated sample.</b><p>After processing, the clone is saved below with a synthesized preview. Original recordings are labeled separately.</p></li><li><b>Choose “Use this voice”.</b><p>The studio will select your clone instead of a preset narrator.</p></li></ol></aside></div>
    <section class="saved-clones-section"><div class="section-heading"><h2>Your saved clones</h2><a href="#/voices">View full library ${icon('arrow')}</a></div><div id="saved-voices">${voiceCards(voices)}</div></section>`;
}
