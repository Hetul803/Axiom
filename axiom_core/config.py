from dataclasses import dataclass
@dataclass(frozen=True)
class AxiomConfig:
    seed:int=0; particle_count:int=64; max_hypotheses:int=96; max_mutations:int=32; max_history:int=256; planning_depth:int=18; coordinate_candidate_limit:int=64; per_action_ms:int=35; global_seconds:int=11*60
    w_information:float=1.0; w_progress:float=.8; w_novelty:float=.75; w_reversibility:float=.35; w_risk:float=1.2; w_repeat:float=.8; w_cost:float=.02; neural_proposer_enabled:bool=False
