import os
os.environ.setdefault('PRIVATE_PASSWORD','test-only-password')
os.environ.setdefault('SESSION_SECRET','testing-secret-with-more-than-32-characters')
import tempfile
os.environ['DATABASE_URL']='sqlite:///'+tempfile.mktemp(suffix='.db')
from fastapi.testclient import TestClient
from app.main import app

def test_private_demo_flow():
    with TestClient(app) as client:
        assert client.get('/health').json()['execution_enabled'] is False
        assert client.get('/dashboard').status_code==401
        assert client.post('/auth/login',json={'password':'incorrect'}).status_code==401
        token=client.post('/auth/login',json={'password':'test-only-password'}).json()['token']
        headers={'Authorization':f'Bearer {token}'}
        dash=client.get('/dashboard',headers=headers).json()
        assert dash['mode']=='demo' and dash['account_equity']==10482
        assert len(client.get('/strategies',headers=headers).json())==3
        assert client.get('/risk',headers=headers).json()['paused'] is True
        created=client.post('/strategies',headers=headers,json={'name':'Sandbox Strategy','category':'Swing','allocation':0,'max_positions':2}).json()
        assert created['status']=='draft'
        assert client.patch('/strategies/'+created['id'],headers=headers,json={'description':'Demo updated'}).status_code==200
        assert client.patch('/risk',headers=headers,json={'max_daily_loss_pct':1,'risk_per_trade_pct':0.25,'max_exposure_pct':60,'paused':True}).status_code==200
        assert client.post('/strategies',headers=headers,json={'name':'Overallocated Strategy','category':'Swing','allocation':500,'max_positions':2}).status_code==400
        assert client.get('/audit',headers=headers).json()[0]['action']=='risk.updated'
        assert client.post('/orders',headers=headers,json={}).status_code==405
