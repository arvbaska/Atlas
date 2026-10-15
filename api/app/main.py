"""Iteration 1: demo-only control centre. No order routing or broker connectivity."""
from __future__ import annotations
import os, hmac, secrets, json
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from typing import Optional
from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, Column, String, Float, Integer, ForeignKey, DateTime, Text, func
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./trading_demo.db')
PRIVATE_PASSWORD = os.getenv('PRIVATE_PASSWORD', '')
SESSION_SECRET = os.getenv('SESSION_SECRET', '')
if not PRIVATE_PASSWORD or not SESSION_SECRET:
    raise RuntimeError('Set PRIVATE_PASSWORD and SESSION_SECRET environment variables')
if len(SESSION_SECRET) < 32:
    raise RuntimeError('SESSION_SECRET must contain at least 32 characters')
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith('sqlite') else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()
signer = URLSafeTimedSerializer(SESSION_SECRET, salt='private-dashboard')

def now(): return datetime.now(timezone.utc)
class Strategy(Base):
    __tablename__='strategies'
    id=Column(String,primary_key=True)
    name=Column(String,nullable=False)
    category=Column(String,nullable=False)
    status=Column(String,nullable=False,default='draft')
    version=Column(Integer,nullable=False,default=1)
    allocation=Column(Float,nullable=False,default=0)
    max_positions=Column(Integer,nullable=False,default=3)
    description=Column(String,nullable=False,default='')
class RiskPolicy(Base):
    __tablename__='risk_policies'
    id=Column(String,primary_key=True)
    name=Column(String,nullable=False)
    max_daily_loss_pct=Column(Float,nullable=False)
    risk_per_trade_pct=Column(Float,nullable=False)
    max_exposure_pct=Column(Float,nullable=False)
    paused=Column(Integer,nullable=False,default=1)
class Order(Base):
    __tablename__='orders'
    id=Column(String,primary_key=True)
    strategy_id=Column(String, ForeignKey('strategies.id'),nullable=False)
    ticker=Column(String,nullable=False)
    side=Column(String,nullable=False)
    shares=Column(Float,nullable=False)
    price=Column(Float,nullable=False)
    status=Column(String,nullable=False)
    created_at=Column(DateTime(timezone=True),nullable=False)
class Position(Base):
    __tablename__='positions'
    id=Column(String,primary_key=True)
    strategy_id=Column(String, ForeignKey('strategies.id'),nullable=False)
    ticker=Column(String,nullable=False)
    shares=Column(Float,nullable=False)
    avg_cost=Column(Float,nullable=False)
    mark=Column(Float,nullable=False)
class Signal(Base):
    __tablename__='signals'
    id=Column(String,primary_key=True)
    strategy_id=Column(String, ForeignKey('strategies.id'),nullable=False)
    ticker=Column(String,nullable=False)
    action=Column(String,nullable=False)
    reason=Column(String,nullable=False)
    decision=Column(String,nullable=False)
    created_at=Column(DateTime(timezone=True),nullable=False)
class AuditEvent(Base):
    __tablename__='audit_events'
    id=Column(String,primary_key=True)
    action=Column(String,nullable=False)
    detail=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),nullable=False)
class PortfolioSnapshot(Base):
    __tablename__='portfolio_snapshots'
    id=Column(String,primary_key=True)
    day=Column(String,nullable=False)
    equity=Column(Float,nullable=False)
class WatchItem(Base):
    __tablename__='watch_items'
    ticker=Column(String,primary_key=True)
    company=Column(String,nullable=False)
    sector=Column(String,nullable=False)
    price=Column(Float,nullable=False)
    change_pct=Column(Float,nullable=False)
    rvol=Column(Float,nullable=False)
class BacktestRun(Base):
    __tablename__='backtest_runs'
    id=Column(String,primary_key=True)
    strategy_id=Column(String,ForeignKey('strategies.id'),nullable=False)
    period=Column(String,nullable=False)
    return_pct=Column(Float,nullable=False)
    max_drawdown_pct=Column(Float,nullable=False)
    note=Column(String,nullable=False)

def seed(db:Session):
    if db.query(Strategy).count(): return
    db.add_all([
        Strategy(id='s1',name='Momentum Alpha',category='Momentum',status='demo',version=1,allocation=4500,max_positions=3,description='Relative strength and volume signals'),
        Strategy(id='s2',name='Breakout Scout',category='Breakout',status='demo',version=1,allocation=3500,max_positions=2,description='Range breakout candidate tracking'),
        Strategy(id='s3',name='Swing Reversal',category='Mean reversion',status='draft',version=1,allocation=2000,max_positions=2,description='Pullback and reversal candidate tracking'),
        RiskPolicy(id='primary',name='Global demo safeguards',max_daily_loss_pct=2,risk_per_trade_pct=0.5,max_exposure_pct=75,paused=1),
        Position(id='p1',strategy_id='s1',ticker='NVDA',shares=8,avg_cost=125.20,mark=130.55),
        Position(id='p2',strategy_id='s1',ticker='MSFT',shares=3,avg_cost=460,mark=467.2),
        Position(id='p3',strategy_id='s2',ticker='AMD',shares=6,avg_cost=155.3,mark=153.8),
        Order(id='D-1001',strategy_id='s1',ticker='NVDA',side='BUY',shares=8,price=125.2,status='demo-filled',created_at=now()),
        Order(id='D-1002',strategy_id='s1',ticker='MSFT',side='BUY',shares=3,price=460,status='demo-filled',created_at=now()),
        Order(id='D-1003',strategy_id='s2',ticker='AMD',side='BUY',shares=6,price=155.3,status='demo-filled',created_at=now()),
        Signal(id='g1',strategy_id='s1',ticker='NVDA',action='BUY',reason='Relative strength above threshold; volume confirmation (sample)',decision='accepted',created_at=now()),
        Signal(id='g2',strategy_id='s2',ticker='TSLA',action='BUY',reason='Breakout candidate rejected: simulated exposure limit',decision='rejected',created_at=now()),
        Signal(id='g3',strategy_id='s3',ticker='AAPL',action='HOLD',reason='No reversal confirmation (sample)',decision='observed',created_at=now()),
        BacktestRun(id='b1',strategy_id='s1',period='Jan–Jun (illustrative)',return_pct=6.4,max_drawdown_pct=-4.1,note='Illustrative values only, not computed from historical market data'),
    ])
    for ticker,company,sector,price,change,rvol in [
        ('NVDA','NVIDIA','Technology',130.55,1.8,1.9),('MSFT','Microsoft','Technology',467.2,0.6,1.1),('AMD','Advanced Micro Devices','Semiconductors',153.8,-0.9,1.4),('AAPL','Apple','Technology',235.3,0.3,0.8),('TSLA','Tesla','Automotive',260.5,-1.2,2.2),('AMZN','Amazon','Consumer',205.3,1.1,1.3),('META','Meta Platforms','Technology',595.8,0.8,0.9),('GOOGL','Alphabet','Technology',189.4,-0.2,1.0)]:
        db.add(WatchItem(ticker=ticker,company=company,sector=sector,price=price,change_pct=change,rvol=rvol))
    for i,equity in enumerate([10000,10070,10045,10155,10100,10180,10210,10195,10275,10305,10290,10390,10420,10460,10482]):
        db.add(PortfolioSnapshot(id=f'snap{i}',day=f'Day {i+1}',equity=equity))
    db.add(AuditEvent(id='seed',action='demo.seed',detail='Initial synthetic demonstration dataset',created_at=now()))
    db.commit()

@asynccontextmanager
async def lifespan(app:FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db: seed(db)
    yield
app=FastAPI(title='Autonomous Trading Control Centre — Demo Only',lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=os.getenv('CORS_ORIGINS','http://localhost:3000').split(','),allow_credentials=False,allow_methods=['GET','POST','PATCH'],allow_headers=['Authorization','Content-Type'])
def db_session():
    with SessionLocal() as db: yield db
def auth(authorization:Optional[str]=Header(None)):
    if not authorization or not authorization.startswith('Bearer '): raise HTTPException(401,'Login required')
    try:
        payload=signer.loads(authorization[7:],max_age=8*3600)
        if payload.get('scope')!='private-demo': raise HTTPException(401,'Invalid session')
    except (BadSignature,SignatureExpired): raise HTTPException(401,'Session expired or invalid')
class LoginIn(BaseModel): password:str
@app.post('/auth/login')
def login(data:LoginIn):
    if not hmac.compare_digest(data.password, PRIVATE_PASSWORD): raise HTTPException(401,'Invalid credentials')
    return {'token':signer.dumps({'scope':'private-demo'}),'expires_in_seconds':28800}
@app.get('/health')
def health(): return {'status':'ok','mode':'demo','broker_connected':False,'execution_enabled':False}
def record(db,action,detail):
    db.add(AuditEvent(id=secrets.token_hex(12),action=action,detail=json.dumps(detail),created_at=now()))
    db.commit()
def strategy_dict(s): return {k:getattr(s,k) for k in ['id','name','category','status','version','allocation','max_positions','description']}
@app.get('/dashboard',dependencies=[Depends(auth)])
def dashboard(db:Session=Depends(db_session)):
    positions=db.query(Position).all(); snapshots=sorted(db.query(PortfolioSnapshot).all(),key=lambda s:int(s.id[4:]))
    cost=sum(p.avg_cost*p.shares for p in positions); marked=sum(p.mark*p.shares for p in positions)
    return {'mode':'demo','broker_connected':False,'execution_enabled':False,'account_equity':snapshots[-1].equity,'baseline_equity':snapshots[0].equity,'unrealized_pnl':round(marked-cost,2),'open_positions':len(positions),'strategy_count':db.query(Strategy).count(),'portfolio_history':[{'day':s.day,'equity':s.equity} for s in sorted(snapshots,key=lambda x:int(x.id[4:]))],'cash_estimate':round(snapshots[-1].equity-marked,2),'disclaimer':'Synthetic fixtures. No market feed or actual brokerage account.'}
@app.get('/strategies',dependencies=[Depends(auth)])
def strategies(db:Session=Depends(db_session)): return [strategy_dict(s) for s in db.query(Strategy).all()]
class StrategyCreate(BaseModel):
    name:str=Field(min_length=2,max_length=80)
    category:str=Field(min_length=2,max_length=60)
    allocation:float=Field(ge=0,le=1_000_000)
    max_positions:int=Field(ge=1,le=100)
    description:str=Field(default='',max_length=500)
@app.post('/strategies',dependencies=[Depends(auth)])
def create_strategy(v:StrategyCreate,db:Session=Depends(db_session)):
    allocated=db.query(func.sum(Strategy.allocation)).scalar() or 0
    if allocated+v.allocation>10000: raise HTTPException(400,'Demo allocations cannot exceed $10,000 capital pool')
    s=Strategy(id=secrets.token_hex(6),name=v.name,category=v.category,allocation=v.allocation,max_positions=v.max_positions,description=v.description,status='draft',version=1)
    db.add(s);record(db,'strategy.created',{'strategy_id':s.id,'name':s.name});return strategy_dict(s)
class StrategyUpdate(BaseModel):
    allocation:Optional[float]=Field(default=None,ge=0,le=1_000_000)
    max_positions:Optional[int]=Field(default=None,ge=1,le=100)
    description:Optional[str]=Field(default=None,max_length=500)
@app.patch('/strategies/{strategy_id}',dependencies=[Depends(auth)])
def update_strategy(strategy_id:str,v:StrategyUpdate,db:Session=Depends(db_session)):
    s=db.get(Strategy,strategy_id)
    if not s: raise HTTPException(404,'Strategy not found')
    changes=v.model_dump(exclude_unset=True)
    if 'allocation' in changes:
        allocated=sum(x.allocation for x in db.query(Strategy).all() if x.id!=s.id)
        if allocated+changes['allocation']>10000: raise HTTPException(400,'Demo allocations cannot exceed $10,000')
    for k,value in changes.items(): setattr(s,k,value)
    s.version+=1;record(db,'strategy.updated',{'strategy_id':s.id,'changes':changes});return strategy_dict(s)
@app.get('/positions',dependencies=[Depends(auth)])
def positions(db:Session=Depends(db_session)):
    return [{'id':p.id,'ticker':p.ticker,'strategy_id':p.strategy_id,'shares':p.shares,'avg_cost':p.avg_cost,'mark':p.mark,'market_value':round(p.shares*p.mark,2),'unrealized_pnl':round(p.shares*(p.mark-p.avg_cost),2)} for p in db.query(Position).all()]
@app.get('/orders',dependencies=[Depends(auth)])
def orders(db:Session=Depends(db_session)): return [{'id':o.id,'ticker':o.ticker,'strategy_id':o.strategy_id,'side':o.side,'shares':o.shares,'price':o.price,'status':o.status,'created_at':o.created_at.isoformat()} for o in db.query(Order).all()]
@app.get('/signals',dependencies=[Depends(auth)])
def signals(db:Session=Depends(db_session)): return [{'id':s.id,'ticker':s.ticker,'strategy_id':s.strategy_id,'action':s.action,'reason':s.reason,'decision':s.decision,'created_at':s.created_at.isoformat()} for s in db.query(Signal).all()]
@app.get('/screener',dependencies=[Depends(auth)])
def screener(db:Session=Depends(db_session)): return [{'ticker':x.ticker,'company':x.company,'sector':x.sector,'price':x.price,'change_pct':x.change_pct,'rvol':x.rvol} for x in db.query(WatchItem).all()]
@app.get('/backtests',dependencies=[Depends(auth)])
def backtests(db:Session=Depends(db_session)): return [{'id':b.id,'strategy_id':b.strategy_id,'period':b.period,'return_pct':b.return_pct,'max_drawdown_pct':b.max_drawdown_pct,'note':b.note} for b in db.query(BacktestRun).all()]
@app.get('/risk',dependencies=[Depends(auth)])
def risk(db:Session=Depends(db_session)):
    p=db.get(RiskPolicy,'primary')
    return {'max_daily_loss_pct':p.max_daily_loss_pct,'risk_per_trade_pct':p.risk_per_trade_pct,'max_exposure_pct':p.max_exposure_pct,'paused':bool(p.paused),'enforced':False}
class RiskUpdate(BaseModel):
    max_daily_loss_pct:float=Field(gt=0,le=10)
    risk_per_trade_pct:float=Field(gt=0,le=5)
    max_exposure_pct:float=Field(gt=0,le=100)
    paused:bool=True
@app.patch('/risk',dependencies=[Depends(auth)])
def update_risk(v:RiskUpdate,db:Session=Depends(db_session)):
    p=db.get(RiskPolicy,'primary')
    for key,value in v.model_dump().items(): setattr(p,key,int(value) if key=='paused' else value)
    record(db,'risk.updated',v.model_dump());return risk(db)
@app.get('/audit',dependencies=[Depends(auth)])
def audit(db:Session=Depends(db_session)):return [{'id':x.id,'action':x.action,'detail':x.detail,'created_at':x.created_at.isoformat()} for x in db.query(AuditEvent).order_by(AuditEvent.created_at.desc()).limit(30)]
