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

    def generate(self, job, folder, output):
        import soundfile as sf
        import numpy as np
        if folder:
            from qwen_tts import VoiceClonePromptItem
            prompts = self.torch.load(folder/'prompt.pt',map_location='cpu',weights_only=True)
            prompts = [VoiceClonePromptItem(**p) for p in prompts['items']]
        pieces=[]
        for chunk in script_chunks(job['text']):
            if folder:
                audio,sr = self.base.generate_voice_clone(text=chunk,language=job['language'],voice_clone_prompt=prompts)
            else:
                audio,sr = self.preset.generate_custom_voice(text=chunk,language=job['language'],
                            speaker=job['speaker'],instruct=job['instruct'] or None)
            if pieces:pieces.append(np.zeros(round(sr*0.12),dtype=np.float32))
            pieces.append(audio[0])
        waveform=np.concatenate(pieces)
        temporary = output.with_suffix('.partial.wav')
        sf.write(temporary,waveform,sr)
        temporary.replace(output)
        return len(waveform)/sr
