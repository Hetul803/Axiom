from __future__ import annotations
from dataclasses import dataclass, field
import html, json
@dataclass
class DiagnosticRecorder:
    enabled: bool = False
    events: list[dict] = field(default_factory=list)
    def record(self, **event):
        if self.enabled: self.events.append(event)
    def jsonl(self): return '\n'.join(json.dumps(e,sort_keys=True,default=str) for e in self.events)
def render_html(events:list[dict], path):
    rows=[]
    for i,e in enumerate(events): rows.append(f"<section><h2>Step {i}</h2><pre>{html.escape(json.dumps(e,indent=2,default=str))}</pre></section>")
    open(path,'w').write('<html><body><h1>Axiom V2 Replay</h1>'+''.join(rows)+'</body></html>')
