from __future__ import annotations
import importlib.util, json, statistics, sys, time
from pathlib import Path
ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('axiom_v3_eval',ROOT/'source/axiom_scientist.py'); module=importlib.util.module_from_spec(spec); sys.modules[spec.name]=module; spec.loader.exec_module(module)
exec((ROOT/'source/frozen_v2.py').read_text(),module.__dict__)

def run(seed:int):
    legal=[{'name':name} for name in ('a','b','c','d')]
    controller=module.AxiomScientistController()
    position=[2,2]; target=(0,4); mapping=dict(zip(('a','b','c','d'),((0,1),(1,0),(0,-1),(-1,0))[seed%4:]+((0,1),(1,0),(0,-1),(-1,0))[:seed%4]))
    repeats=0; seen=set(); latencies=[]
    for step in range(40):
        grid=[[0]*5 for _ in range(5)]; grid[target[0]][target[1]]=2; grid[position[0]][position[1]]=1
        observation=controller.observe(tuple(map(tuple,grid)),legal,'win' if tuple(position)==target else 'active')
        if tuple(position)==target: break
        start=time.perf_counter(); action=controller.choose(observation,time.monotonic()+.02); latencies.append((time.perf_counter()-start)*1000)
        key=(tuple(position),action['name']); repeats += key in seen; seen.add(key)
        dy,dx=mapping[action['name']]; position[0]=max(0,min(4,position[0]+dy)); position[1]=max(0,min(4,position[1]+dx))
    return {'solved':tuple(position)==target,'actions':step,'repeated_rate':repeats/max(1,step),'mean_action_ms':statistics.mean(latencies),'p95_action_ms':sorted(latencies)[int(.95*(len(latencies)-1))],'llm_calls':0,'generated_tokens':0}

results=[run(seed) for seed in range(12)]
summary={'evaluation':'synthetic hidden-permutation exploration; no official ARC environments or local 27B model available','games':len(results),'solved':sum(x['solved'] for x in results),'solve_rate':sum(x['solved'] for x in results)/len(results),'mean_actions':statistics.mean(x['actions'] for x in results),'mean_repeated_rate':statistics.mean(x['repeated_rate'] for x in results),'mean_action_ms':statistics.mean(x['mean_action_ms'] for x in results),'p95_action_ms':max(x['p95_action_ms'] for x in results),'average_llm_calls':0,'average_generated_tokens':0,'details':results}
(ROOT/'synthetic_results.json').write_text(json.dumps(summary,indent=2)+'\n'); print(json.dumps(summary,indent=2))
