export const esc = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export const number = n => Number(n||0).toLocaleString();
export const date = n => new Date(n*1000).toLocaleDateString(undefined,{month:'short',day:'numeric',year:'numeric'});
export const logo = `<span class="brand-mark" aria-hidden="true"><i></i><i></i><i></i><i></i></span><span>mellifon<span class="brand-dot">.</span></span>`;
export const icon = (name) => {
  const paths = {grid:'M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z',
    sound:'M4 9v6m4-10v14m4-17v20m4-16v12m4-9v6',
    mic:'M12 3a3 3 0 0 0-3 3v6a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11v1a7 7 0 0 0 14 0v-1M12 19v3m-4 0h8',
    clock:'M12 8v5l3 2M22 12a10 10 0 1 1-20 0 10 10 0 0 1 20 0',
    card:'M3 8h18M3 4h18v16H3zM6 15h5',settings:'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8M12 2v3m0 14v3M2 12h3m14 0h3M5 5l2 2m10 10 2 2M5 19l2-2M17 7l2-2',
    arrow:'M5 12h14m-5-5 5 5-5 5',plus:'M12 4v16M4 12h16',download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',check:'m5 12 4 4L19 6',logout:'M9 4H3v16h6m5-12 4 4-4 4M8 12h13'};
  return `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${(paths[name]||paths.sound).split(/(?=M)/).map(p=>`<path d="${p}"/>`).join('')}</svg>`;
};
export function waves(count=44) { return `<div class="waveform" aria-hidden="true">${Array.from({length:count},(_,i)=>`<i class="bar b${i%11}"></i>`).join('')}</div>`; }
export function badge(status) { return `<span class="badge ${esc(status)}">${esc(status)}</span>`; }
export function empty(title,text,action='') {return `<div class="empty">${icon('sound')}<h3>${esc(title)}</h3><p>${esc(text)}</p>${action}</div>`;}
export function audio(id,base) {return `<div class="audio-row"><audio controls preload="none" crossorigin="use-credentials" src="${base}/audio/generation/${esc(id)}"></audio><a class="icon-button" href="${base}/audio/generation/${esc(id)}?download=1" title="Download WAV">${icon('download')}</a></div>`;}
export function toast(message,error=false) {const el=document.getElementById('toast');el.textContent=message;el.className=error?'show error':'show';clearTimeout(el.timer);el.timer=setTimeout(()=>el.className='',5500);}
export function errorBox(message) {return `<div class="alert" role="alert">${esc(message)}</div>`;}
