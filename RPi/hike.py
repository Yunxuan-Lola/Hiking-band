MET_HIKING = 6
KCAL_PER_STEP = 0.04

# detailed information
class HikeSession:
    def __init__(self):
        self.id = 0
        self.km = 0
        self.steps = 0
        self.kcal = -1
        self.activity_mode = "unknown"
        self.activity_distribution = {}

    #calculate burned calories
    def calc_kcal(self):
        self.kcal = int(MET_HIKING * KCAL_PER_STEP * self.steps)

    def __repr__(self):
        return f"HikeSession{{{self.id}, {self.km}(km), {self.steps}(steps), {self.kcal:.2f}(kcal), activity={self.activity_mode}}}"

def to_list(s: HikeSession) -> list:
    import json
    return [s.id, s.km, s.steps, s.kcal, s.activity_mode, json.dumps(s.activity_distribution)]

def from_list(l: list) -> HikeSession:
    import json
    s = HikeSession()
    s.id = l[0]
    s.km = l[1]
    s.steps = l[2]
    s.kcal = l[3]
    # Database schema: id, km, steps, kcal, user, activity, distribution.
    if len(l) >= 7:
        s.activity_mode = l[5] or 'unknown'
        s.activity_distribution = json.loads(l[6]) if l[6] else {}
    elif len(l) == 6:
        s.activity_mode = l[4] or 'unknown'
        s.activity_distribution = json.loads(l[5]) if l[5] else {}
    else:
        s.activity_mode = "unknown"
        s.activity_distribution = {}
    return s
