import hashlib
import hmac
import io
import json
import os
import tempfile
import time
import unittest
import uuid
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

from app import create_app
from app.models.database import rows, transaction
from app.services.credits import change
from app.worker import claim, execute, recover_stale
from app.routes.billing import apply_event


def sample():
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(24000)
        out.writeframes(b'\x10\x01'*96000)
    buffer.seek(0)
    return buffer


class SaasTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.app=create_app({'TESTING':True,'STORAGE':self.root,'DATABASE':self.root/'test.sqlite3',
                             'STRIPE_SECRET_KEY':'sk_test_fixture','STRIPE_WEBHOOK_SECRET':'whsec_fixture'})
        self.client=self.app.test_client()
        response=self.client.post('/api/auth/register',json={'name':'Alex Morgan','email':'alex@example.com','password':'A secure password 123!'})
        self.assertEqual(response.status_code,200,response.json)
        self.user=response.json['user'];self.csrf=response.json['csrf']
        self.headers={'X-CSRF-Token':self.csrf}

    def tearDown(self):
        self.temp.cleanup()

    def generate(self,key=None,text='A little story worth telling.',client=None,headers=None):
        return (client or self.client).post('/api/generations',json={'text':text,'speaker':'ryan','language':'english'},
                  headers={**(headers or self.headers),'Idempotency-Key':key or uuid.uuid4().hex})

    def test_registration_login_csrf_logout_and_profile(self):
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],5000)
        self.assertEqual(self.client.patch('/api/account',json={'name':'Changed'}).status_code,403)
        self.assertEqual(self.client.patch('/api/account',json={'name':'Alex'},headers=self.headers).status_code,200)
        self.assertEqual(self.client.post('/api/auth/logout',headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/dashboard').status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'alex@example.com','password':'bad'}).status_code,401)
        self.assertEqual(self.client.post('/api/auth/login',json={'email':'alex@example.com','password':'A secure password 123!'}).status_code,200)

    def test_idempotent_generation_and_insufficient_credit(self):
        key=uuid.uuid4().hex
        first=self.generate(key,text='Hello')
        second=self.generate(key,text='Hello')
        self.assertEqual(first.status_code,202,first.json)
        self.assertEqual(first.json['id'],second.json['id'])
        self.assertEqual(self.generate(key,text='Different').status_code,409)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],4995)
        self.assertEqual(self.generate(text='x'*5000).status_code,402)

    def test_atomic_credits_under_concurrent_reservations(self):
        def charge(i):
            with self.app.app_context():
                try:
                    with transaction() as db:
                        change(db,self.user['id'],-1000,'Concurrent test',f'charge:{i}')
                    return True
                except Exception:
                    return False
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(charge,range(8)))
        self.assertEqual(sum(results),5)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],0)

    def test_long_scripts_are_chunked_without_losing_text(self):
        from app.services.engine import script_chunks
        for text in ['A thoughtful sentence. '*200, '这是一个清晰的声音。'*100, 'hello'*300]:
            chunks=script_chunks(text)
            self.assertTrue(all(0<len(chunk)<=300 for chunk in chunks))
            self.assertEqual(''.join(chunks).replace(' ',''),text.replace(' ',''))

    def test_clone_preview_has_token_and_duration_limits(self):
        import types
        import numpy as np
        from app.services.engine import QwenEngine
        engine=QwenEngine.__new__(QwenEngine)
        engine.base=Mock();engine.torch=Mock()
        engine.torch.load.return_value={'items':[]}
        engine.base.generate_voice_clone.return_value=([np.zeros(24000*4,dtype=np.float32)],24000)
        job=dict(kind='preview',text='Hello, this is my saved voice.',language='auto')
        folder=self.root/'fixture-voice';folder.mkdir()
        output=folder/'preview.wav'
        with patch.dict('sys.modules',{'qwen_tts':types.SimpleNamespace(VoiceClonePromptItem=dict)}):
            self.assertEqual(engine.generate(job,folder,output),4)
            self.assertEqual(engine.base.generate_voice_clone.call_args.kwargs['max_new_tokens'],384)
            output.unlink()
            engine.base.generate_voice_clone.return_value=([np.zeros(24000*40,dtype=np.float32)],24000)
            with self.assertRaisesRegex(RuntimeError,'short-sample budget'):
                engine.generate(job,folder,output)
            self.assertFalse(output.exists())

    def test_clone_generation_history_and_private_downloads(self):
        response=self.client.post('/api/voices',data={'name':'My voice','ref_text':'This is my reference sample.',
                    'consent':'true','audio':(sample(),'sample.wav')},headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(response.status_code,202,response.json)
        engine=Mock()
        def fake_clone(folder,ref_text): (folder/'prompt.pt').write_bytes(b'fake-test-prompt')
        def fake_generate(job,folder,out,progress=None): out.write_bytes(sample().read());return 4
        engine.clone.side_effect=fake_clone;engine.generate.side_effect=fake_generate
        with self.app.app_context():
            job=claim('test-worker');execute(job,engine)
        voices=self.client.get('/api/voices').json
        self.assertEqual(voices[0]['status'],'ready')
        self.assertEqual(voices[0]['clone_mode'],'text_conditioned')
        self.assertEqual(voices[0]['reference_duration'],4)
        self.assertIn('/preview/',voices[0]['preview_url'])
        self.assertEqual(voices[0]['latest_job']['progress'],100)
        voice_id=voices[0]['id']
        with self.client.get('/api/audio/preview/'+voice_id) as response:
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.data.startswith(b'RIFF'))
        self.assertEqual(self.client.patch('/api/voices/'+voice_id,json={'name':'Narration'},headers=self.headers).status_code,200)
        response=self.client.post('/api/generations',json={'text':'Welcome to my story','voice_id':voice_id},
                       headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
        self.assertEqual(response.status_code,202,response.json)
        with self.app.app_context():execute(claim('test-worker'),engine)
        identifier=response.json['id']
        with self.client.get('/api/audio/generation/'+identifier+'?download=1') as response:
            self.assertEqual(response.status_code,200)
            self.assertTrue(response.data.startswith(b'RIFF'))
            self.assertIn('attachment',response.headers['Content-Disposition'])
        other=self.app.test_client()
        registered=other.post('/api/auth/register',json={'name':'Other','email':'other@example.com','password':'Another strong password!'})
        other_headers={'X-CSRF-Token':registered.json['csrf'],'Idempotency-Key':uuid.uuid4().hex}
        self.assertEqual(other.get('/api/voices').json,[])
        self.assertEqual(other.get('/api/jobs').json,[])
        self.assertEqual(other.get('/api/audio/generation/'+identifier).status_code,404)
        self.assertEqual(other.get('/api/audio/voice/'+voice_id).status_code,404)
        self.assertEqual(other.get('/api/audio/preview/'+voice_id).status_code,404)
        self.assertEqual(other.post('/api/voices/'+voice_id+'/preview',json={},headers=other_headers).status_code,404)
        self.assertEqual(other.post('/api/voices/'+voice_id+'/rebuild',json={'ref_text':'Not mine'},headers=other_headers).status_code,404)
        self.assertEqual(other.delete('/api/voices/'+voice_id,headers=other_headers).status_code,404)
        self.assertEqual(other.post('/api/generations',json={'text':'Trying','voice_id':voice_id},headers=other_headers).status_code,404)
        self.assertEqual(self.client.delete('/api/voices/'+voice_id,headers=self.headers).status_code,200)
        self.assertEqual(self.client.delete('/api/jobs/'+identifier,headers=self.headers).status_code,200)
        self.assertFalse((self.root/'users'/self.user['id']/'generated'/(identifier+'.wav')).exists())

    def test_reference_transcript_mode_and_silent_recording_validation(self):
        for data in [dict(name='Accurate clone',consent='true',clone_mode='text_conditioned',audio=(sample(),'voice.wav')),
                     dict(name='Silent sample',consent='true',audio=(self.silent_sample(),'voice.wav'))]:
            response=self.client.post('/api/voices',data=data,headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,400,response.json)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],5000)

    def test_reference_correction_preserves_voice_and_charges_no_credits(self):
        response=self.client.post('/api/voices',data=dict(name='My saved voice',ref_text='Original supplied transcript.',consent='true',audio=(sample(),'voice.wav')),
                       headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
        voice_id=response.json['voice_id']
        engine=Mock()
        def clone(folder,text):(folder/'prompt.pt').write_bytes(text.encode())
        def generate(job,folder,out,progress=None):out.write_bytes(sample().read());return 4
        engine.clone.side_effect=clone;engine.generate.side_effect=generate
        with self.app.app_context():execute(claim('test'),engine)
        folder=self.root/'users'/self.user['id']/'voices'/voice_id
        before=(folder/'reference.wav').read_bytes()
        headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex}
        data=dict(ref_text='Correct words actually in the recording.',clone_mode='text_conditioned')
        url='/api/voices/'+voice_id+'/rebuild'
        first=self.client.post(url,json=data,headers=headers)
        self.assertEqual(first.status_code,202,first.json)
        self.assertEqual(self.client.post(url,json=data,headers=headers).json['id'],first.json['id'])
        self.assertEqual(first.json['cost'],0)
        with self.app.app_context():execute(claim('test'),engine)
        voice=self.client.get('/api/voices').json[0]
        self.assertEqual(voice['id'],voice_id)
        self.assertEqual(voice['ref_text'],data['ref_text'])
        self.assertEqual(voice['original_ref_text'],'Original supplied transcript.')
        self.assertEqual((folder/'prompt.previous.pt').read_bytes(),b'Original supplied transcript.')
        self.assertEqual((folder/'reference.wav').read_bytes(),before)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],4000)

    def silent_sample(self):
        data=sample();raw=bytearray(data.read());raw[44:]=b'\0'*(len(raw)-44)
        return io.BytesIO(raw)

    def test_existing_voice_can_get_one_included_preview_and_survives_reopen(self):
        response=self.client.post('/api/voices',data=dict(name='Saved clone',ref_text='A matching transcript.',consent='true',audio=(sample(),'ref.wav')),
                       headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
        engine=Mock()
        def speech(job,folder,out,progress=None):out.write_bytes(sample().read());return 4
        engine.generate.side_effect=speech
        with self.app.app_context():execute(claim('test'),engine)
        voice_id=response.json['voice_id']
        (self.root/'users'/self.user['id']/'voices'/voice_id/'preview.wav').unlink()
        url='/api/voices/'+voice_id+'/preview'
        first=self.client.post(url,json={},headers=self.headers)
        second=self.client.post(url,json={},headers=self.headers)
        self.assertEqual(first.status_code,202,first.json)
        self.assertEqual(first.json['id'],second.json['id'])
        self.assertEqual(first.json['cost'],0)
        with self.app.app_context():execute(claim('test'),engine)
        self.assertTrue(self.client.post(url,json={},headers=self.headers).json['already_ready'])
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],4000)
        # A fresh application instance reads the same durable voice and preview metadata.
        reopened=create_app(self.app.config)
        with reopened.app_context():
            self.assertEqual(rows('SELECT status FROM voices WHERE id=?',(voice_id,),one=True)['status'],'ready')

    def test_failures_and_stale_workers_refund_once(self):
        response=self.generate(text='Refund me')
        engine=Mock();engine.generate.side_effect=RuntimeError('fixture failure')
        with self.app.app_context():
            job=claim('dead-worker');execute(job,engine);execute(job,engine)
            self.assertEqual(rows('SELECT credits FROM users WHERE id=?',(self.user['id'],),one=True)['credits'],5000)
        response=self.generate(text='Stale job')
        with self.app.app_context():
            job=claim('stopped-worker')
            with transaction() as db:db.execute('UPDATE jobs SET heartbeat=0 WHERE id=?',(job['id'],))
            recover_stale();recover_stale()
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],5000)

    def test_invalid_audio_and_consent_do_not_spend_credits(self):
        for data in [{'name':'Test','consent':'false','audio':(sample(),'sample.wav')},
                     {'name':'Test','consent':'true','audio':(io.BytesIO(b'not audio'),'sample.exe')},
                     {'name':'Test','consent':'true','audio':(io.BytesIO(b'not audio'),'sample.wav')},
                     {'name':'Test','consent':'true','audio':(io.BytesIO(b'#EXTM3U\nfile:///private/reference.wav\n'),'playlist.wav')}]:
            response=self.client.post('/api/voices',data=data,headers={**self.headers,'Idempotency-Key':uuid.uuid4().hex})
            self.assertEqual(response.status_code,400,response.json)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],5000)

    def test_password_reset_is_single_use_and_revokes_sessions(self):
        with self.app.app_context(),patch('app.routes.auth.smtplib.SMTP') as smtp:
            self.app.config['SMTP_HOST']='smtp.example.com'
            response=self.client.post('/api/auth/forgot-password',json={'email':'alex@example.com'},headers=self.headers)
            self.assertEqual(response.status_code,200,response.json)
            message=smtp.return_value.__enter__.return_value.send_message.call_args.args[0]
            token=message.get_content().split('token=')[1].split()[0]
        data={'token':token,'password':'A replacement password!'}
        self.assertEqual(self.client.post('/api/auth/reset-password',json=data,headers=self.headers).status_code,200)
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)
        self.assertEqual(self.client.post('/api/auth/reset-password',json=data).status_code,400)

    def test_verified_invoices_allocate_once_and_reject_forged_webhooks(self):
        self.assertEqual(self.client.post('/api/billing/webhook',data='{}').status_code,400)
        subscription={'id':'sub_test','status':'active','customer':'cus_test',
                      'items':{'data':[{'price':{'id':'price_starter'},'quantity':1,'current_period_end':2000000000}]}}
        event={'id':'evt_fixture','type':'invoice.paid','data':{'object':{'id':'in_test','customer':'cus_test',
               'subscription':'sub_test','billing_reason':'subscription_cycle','amount_paid':1200,'currency':'usd',
               'lines':{'data':[{'price':{'id':'price_starter'},'proration':False}]}}}}
        with patch.dict(os.environ,{'STRIPE_STARTER_MONTHLY_PRICE':'price_starter'}),self.app.app_context():
            with transaction() as db:db.execute('UPDATE users SET customer_id=? WHERE id=?',('cus_test',self.user['id']))
            apply_event(event,subscription);apply_event(event,subscription)
            # A different event for the same invoice cannot allocate twice either.
            event['id']='evt_duplicate_invoice';apply_event(event,subscription)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],55000)
        self.assertEqual(len(self.client.get('/api/billing').json['payments']),1)

    def test_checkout_and_portal_use_stripe_and_pending_checkout_is_reused(self):
        with patch.dict(os.environ,{'STRIPE_STARTER_MONTHLY_PRICE':'price_starter'}), \
             patch('stripe.Customer.create',return_value={'id':'cus_checkout'}) as customer, \
             patch('stripe.checkout.Session.create',return_value={'id':'cs_test','url':'https://checkout.stripe.com/fixture','expires_at':time.time()+1800}) as checkout:
            for _ in range(2):
                response=self.client.post('/api/billing/checkout',json={'plan':'starter','interval':'month'},headers=self.headers)
                self.assertEqual(response.status_code,200,response.json)
            checkout.assert_called_once();customer.assert_called_once()
        with patch('stripe.billing_portal.Session.create',return_value={'url':'https://billing.stripe.com/fixture'}) as portal:
            self.assertEqual(self.client.post('/api/billing/portal',json={},headers=self.headers).status_code,200)
            portal.assert_called_once()

    def test_signed_webhook_retries_and_annual_credits(self):
        subscription={'id':'sub_annual','customer':'cus_annual','status':'active',
                      'items':{'data':[{'price':{'id':'price_annual'},'quantity':1,'current_period_end':2000000000}]}}
        event={'id':'evt_signed','object':'event','type':'invoice.paid','data':{'object':{
               'id':'in_annual','object':'invoice','customer':'cus_annual','billing_reason':'subscription_cycle',
               'parent':{'subscription_details':{'subscription':'sub_annual'}},'amount_paid':12000,'currency':'usd',
               'lines':{'data':[{'pricing':{'price_details':{'price':'price_annual'}},'proration':False}]}}}}
        payload=json.dumps(event);stamp=int(time.time())
        signature=hmac.new(b'whsec_fixture',f'{stamp}.{payload}'.encode(),hashlib.sha256).hexdigest()
        with self.app.app_context(),transaction() as db:
            db.execute('UPDATE users SET customer_id=? WHERE id=?',('cus_annual',self.user['id']))
        with patch.dict(os.environ,{'STRIPE_STARTER_YEARLY_PRICE':'price_annual'}), \
             patch('stripe.Subscription.retrieve',return_value=subscription):
            for _ in range(2):
                response=self.client.post('/api/billing/webhook',data=payload,headers={'Stripe-Signature':f't={stamp},v1={signature}'})
                self.assertEqual(response.status_code,200,response.json)
        self.assertEqual(self.client.get('/api/auth/me').json['user']['credits'],605000)

    def test_production_cookie_flags_and_expired_session(self):
        self.app.config['APP_ENV']='production'
        response=self.client.post('/api/auth/login',json={'email':'alex@example.com','password':'A secure password 123!'},headers=self.headers)
        cookie=response.headers['Set-Cookie']
        for expected in ('Secure','HttpOnly','SameSite=Lax'):self.assertIn(expected,cookie)
        with self.app.app_context(),transaction() as db:db.execute('UPDATE sessions SET expires=0')
        self.assertEqual(self.client.get('/api/auth/me').status_code,401)

    def test_hostile_origin_and_missing_credentials_are_rejected(self):
        self.assertEqual(self.client.get('/api/dashboard',headers={'Origin':'https://attacker.example'}).status_code,403)
        self.app.config['STRIPE_SECRET_KEY']=''
        self.assertEqual(self.client.post('/api/billing/checkout',json={'plan':'starter'},headers=self.headers).status_code,503)


if __name__=='__main__':unittest.main()
