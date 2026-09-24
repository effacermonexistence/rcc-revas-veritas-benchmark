"""Cohort-wide scoring barrier, including bounded native-environment handoff."""
from dataclasses import dataclass
from .canonical import sha_json
from .interfaces import DeferredScore
from .guardrails import require


class RetainedSessionScore(DeferredScore):
    def __init__(self, session): self.session = session
    def fingerprint(self): return sha_json(self.session.pairing_state())
    def score(self): return self.session.native_score()
    def close(self): self.session.close()


@dataclass
class ScoreJob:
    handle: DeferredScore
    result: dict
    case_alias: str
    trial: int
    state_sha256: str
    detached: bool


def make_job(session, result, case_alias, trial):
    fingerprint = sha_json(session.pairing_state())
    handle = session.defer_score()
    if handle is None:
        return ScoreJob(RetainedSessionScore(session), result, case_alias, trial, fingerprint, False)
    try:
        require(isinstance(handle, DeferredScore), 'DEFERRED_SCORE_HANDLE_INVALID')
        require(handle.fingerprint() == fingerprint, 'DEFERRED_SCORE_STATE_MISMATCH')
        # defer_score must not modify the native final state before it is detached.
        require(sha_json(session.pairing_state()) == fingerprint, 'DEFERRED_SCORE_SOURCE_MUTATED')
        session.close()
    except Exception:
        if isinstance(handle, DeferredScore): handle.close()
        raise
    return ScoreJob(handle, result, case_alias, trial, fingerprint, True)
