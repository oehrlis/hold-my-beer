from ..util import ApiError

STATES = ("waiting", "voting_open", "voting_closed", "result_visible",
          "challenge_running", "scorecard_visible", "closing")

TRANSITIONS = {
    "waiting": {"voting_open"},
    "voting_open": {"voting_closed"},
    "voting_closed": {"result_visible"},
    "result_visible": {"challenge_running"},
    "challenge_running": {"scorecard_visible"},
    "scorecard_visible": {"waiting", "closing"},
    "closing": set(),
}


def check_transition(current, new):
    if new not in TRANSITIONS.get(current, set()):
        raise ApiError("invalid_transition",
                       "Ungültiger Zustandswechsel: %s → %s." % (current, new), 409)
