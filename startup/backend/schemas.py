from dataclasses import dataclass
@dataclass
class StepRequest: session_id:str; action:str|None=None; autonomous:bool=False
