class SecurityException(Exception):
    def __init__(self, message, risk_score=None, tier=None, patterns=None, reasoning=None):
        super().__init__(message)
        self.risk_score = risk_score
        self.tier = tier
        self.patterns = patterns or []
        self.reasoning = reasoning


class InterventionRequired(Exception):
    def __init__(self, message, risk_score=None, tier=None, reasoning=None, confirm_callback=None, audit_record=None):
        super().__init__(message)
        self.risk_score = risk_score
        self.tier = tier
        self.reasoning = reasoning
        self.confirm_callback = confirm_callback
        self.audit_record = audit_record
