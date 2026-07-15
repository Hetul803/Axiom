from axiom_core.startup_safety import classify_action
class ApprovalController:
    def __init__(self): self.approved=set(); self.denied=[]
    def approve(self, session_id, action): self.approved.add((session_id,str(action)))
    def allowed(self, session_id, action):
        safety=classify_action(action)
        if safety.requires_approval and (session_id,str(action)) not in self.approved:
            self.denied.append({'session_id':session_id,'action':str(action),'reason':'approval_required'}); return False
        return True
APPROVALS=ApprovalController()
