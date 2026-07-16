if not TRUE_SUBMISSION:
    import platform, statistics, time
    from axiom_core.runtime import AxiomRuntime
    from axiom_core.config import AxiomConfig
    from axiom_core.types import Observation, EnvironmentStatus
    legal=('up','down','left','right')
    rt=AxiomRuntime(AxiomConfig(per_action_ms=10, particle_count=16))
    lats=[]; illegal=0
    for i in range(5):
        obs=Observation(((0,0,0),(0,2,0),(0,0,3)), legal, EnvironmentStatus.ACTIVE, i)
        t=time.monotonic(); a=rt.choose_action(obs,10); lats.append((time.monotonic()-t)*1000); illegal += a not in legal
    print({'python':platform.python_version(),'cpu':platform.processor(),'action_budget_ms':PER_ACTION_SOFT_DEADLINE_MS,'particle_budget':PARTICLE_BUDGET,'visible_games':'not queried in diagnostics','illegal_actions':illegal,'p50_latency_ms':statistics.median(lats),'p95_latency_ms':max(lats),'submission_path':'/kaggle/working/submission.parquet'})
