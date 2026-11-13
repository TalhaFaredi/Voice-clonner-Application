export function mountDemos(root) {
  const preset=root.querySelector('.floating-player');
  if(preset) preset.innerHTML=`<div class="demo-player"><b>Hear it for yourself</b><small>Ryan · English · AI-generated preset demo</small><audio controls preload="none" aria-label="Qwen preset speech demonstration" src="/public/audio/preset-demo.wav"></audio></div>`;
  const cloning=root.querySelector('.feature-lime');
  if(cloning) cloning.insertAdjacentHTML('beforeend',`<div class="clone-demo"><small>Saved clone · synthetic reference sample</small><audio controls preload="none" aria-label="Saved voice clone demonstration" src="/public/audio/clone-demo.wav"></audio></div>`);
}
