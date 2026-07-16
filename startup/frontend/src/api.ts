export async function createSession(kind:string){return fetch(`/sessions/${kind}`,{method:'POST'}).then(r=>r.json())}
export async function step(session_id:string, action?:string){return fetch(`/sessions/${session_id}/step?action=${action||''}`,{method:'POST'}).then(r=>r.json())}
