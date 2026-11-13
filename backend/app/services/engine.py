"""Qwen3-TTS integration. Imported only by the independent GPU worker."""
from dataclasses import asdict


def script_chunks(text,limit=300):
    """Keep each synthesis pass comfortably within the model's audio token budget."""
    import re
    chunks,current=[],''
    for token in re.findall(r'\S+\s*',text):
        for start in range(0,len(token),limit):
            part=token[start:start+limit]
            if len(current)+len(part)>limit and current.strip():
                chunks.append(current.strip());current=''
            current+=part
            if len(current)>100 and re.search(r'[.!?。！？]\s*$',current):
                chunks.append(current.strip());current=''
    if current.strip():chunks.append(current.strip())
    return chunks


class QwenEngine:
    def __init__(self, config):
        import torch
        from qwen_tts import Qwen3TTSModel
        self.torch = torch
        device = config['TTS_DEVICE']
        dtype = torch.bfloat16 if device.startswith('cuda') else torch.float32
        self.base = Qwen3TTSModel.from_pretrained(config['CLONE_MODEL'],device_map=device,dtype=dtype)
        self.preset = Qwen3TTSModel.from_pretrained(config['PRESET_MODEL'],device_map=device,dtype=dtype)

    def clone(self, folder, ref_text):
        prompts = self.base.create_voice_clone_prompt(ref_audio=str(folder/'reference.wav'),
                    ref_text=ref_text or None,x_vector_only_mode=not bool(ref_text))
        temporary = folder/'prompt.partial.pt'
        self.torch.save({'items':[asdict(p) for p in prompts]},temporary)
        temporary.replace(folder/'prompt.pt')

    def generate(self, job, folder, output, progress=None):
        import soundfile as sf
        import numpy as np
        if folder:
            from qwen_tts import VoiceClonePromptItem
            prompts = self.torch.load(folder/'prompt.pt',map_location='cpu',weights_only=True)
            prompts = [VoiceClonePromptItem(**p) for p in prompts['items']]
        pieces=[]
        is_preview=job['kind'] in ('clone','preview')
        chunks=script_chunks(job['text'])
        for index,chunk in enumerate(chunks):
            if progress:progress(index,len(chunks))
            if folder:
                audio,sr = self.base.generate_voice_clone(text=chunk,language=job['language'],voice_clone_prompt=prompts,
                                  max_new_tokens=384 if is_preview else 2048)
            else:
                audio,sr = self.preset.generate_custom_voice(text=chunk,language=job['language'],
                            speaker=job['speaker'],instruct=job['instruct'] or None)
            if pieces:pieces.append(np.zeros(round(sr*0.12),dtype=np.float32))
            pieces.append(audio[0])
        waveform=np.concatenate(pieces)
        if is_preview and len(waveform)/sr>max(15,min(30,len(job['text'].split())*1.5)):
            raise RuntimeError('The preview ran beyond its short-sample budget. Verify the reference transcript before retrying.')
        temporary = output.with_suffix('.partial.wav')
        sf.write(temporary,waveform,sr)
        temporary.replace(output)
        return len(waveform)/sr
