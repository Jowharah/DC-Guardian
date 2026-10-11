"""Grounded PPE and face specialist; no severity or identity-to-PPE linkage."""
from response.agents.grounded_reasoning import grounded_reason
from response.agents.specialists.base import SpecialistAgent,SpecialistRequest

class PhysicalSecuritySpecialist(SpecialistAgent):
    specialist_id="physical_security"
    supported_domains=frozenset({"PHYSICAL_SECURITY","SAFETY"})
    def __init__(self,provider):
        self.provider=provider
    def assess(self,request:SpecialistRequest)->dict:
        self.validate_request(request)
        task=("Assess only supplied frozen PPE person-level policy outcomes, face recognition "
              "and independent zone authorization. Same-camera/time pairing is operator-declared "
              "and does not establish the recognized person is any particular PPE detection. "
              "A missing associated safety vest is a detector/policy outcome, not proof a vest "
              "was physically absent. Do not infer misconduct, identity-to-PPE association, "
              "camera authenticity, causation, severity, escalation, or autonomous action. "
              "Preserve uncertainty and cite only retrieved approved sources. "+request.task)
        return grounded_reason(provider=self.provider,incident_evidence=request.incident_evidence,
                               retrieved_evidence=request.retrieved_evidence,task=task)
