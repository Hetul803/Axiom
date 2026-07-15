try:
    from fastapi import FastAPI
except Exception:
    class FastAPI:
        def __init__(self,*a,**k): self.routes=[]
        def get(self,path): return lambda f:f
        def post(self,path): return lambda f:f
from startup.backend.session_manager import MANAGER
app=FastAPI(title='Axiom Runtime')
@app.get('/health')
def health(): return {'ok':True,'name':'Axiom Runtime'}
@app.post('/sessions/{kind}')
def create_session(kind:str='grid'):
    sid=MANAGER.create(kind); return {'session_id':sid,'kind':kind}
@app.post('/sessions/{sid}/step')
def step(sid:str, action:str|None=None, autonomous:bool=False): return MANAGER.step(sid, action, autonomous)
@app.get('/sessions/{sid}/replay')
def replay(sid:str): return {'timeline':MANAGER.sessions[sid]['timeline']}
