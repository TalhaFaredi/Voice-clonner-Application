"""Local diagnostic ASR. Downloads weights, but never uploads reference audio.

Does not change a voice, prompt, transcript, job or credit balance.
"""
import argparse
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--voice-id',required=True)
    args=parser.parse_args()
    db=sqlite3.connect(ROOT/'backend'/'storage'/'saas.sqlite3')
    voice=db.execute('SELECT user_id,ref_text FROM voices WHERE id=? AND deleted=0',(args.voice_id,)).fetchone()
    db.close()
    if not voice:raise ValueError('Voice not found')
    source=ROOT/'backend'/'storage'/'users'/voice[0]/'voices'/args.voice_id/'reference.wav'
    import soundfile as sf
    import librosa
    import torch
    from transformers import WhisperProcessor,WhisperForConditionalGeneration
    torch.set_num_threads(4)
    cache=ROOT/'backend'/'storage'/'asr-cache'
    processor=WhisperProcessor.from_pretrained('openai/whisper-base',cache_dir=cache)
    model=WhisperForConditionalGeneration.from_pretrained('openai/whisper-base',cache_dir=cache).eval()
    audio,sr=sf.read(source,dtype='float32')
    if sr!=16000:audio=librosa.resample(audio,orig_sr=sr,target_sr=16000)
    inputs=processor(audio,sampling_rate=16000,return_tensors='pt')
    with torch.inference_mode():tokens=model.generate(**inputs,task='transcribe',max_new_tokens=128)
    text=processor.batch_decode(tokens,skip_special_tokens=True)[0]
    print('Provided reference transcript:',voice[1],flush=True)
    print('Local ASR transcription (review for errors):',text,flush=True)


if __name__=='__main__':main()
