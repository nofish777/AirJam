class MelodicZoneController:
    def __init__(self, x, y, w, h, notes, cooldown_ms=100):
        self.x = x
        self.y = y
        self.w = w
        self.h = h
        self.notes = notes
        self.cooldown_ms = cooldown_ms
        self.last_index = None
        self.cooldown_until = 0

    def update(self, point, now_ms):
        if point is None:
            self.last_index = None
            return None
        px, py = point
        if not (self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h):
            self.last_index = None
            return None

        zone_w = max(1, self.w / len(self.notes))
        index = int((px - self.x) / zone_w)
        if index >= len(self.notes):
            index = len(self.notes) - 1
        if index == self.last_index and now_ms < self.cooldown_until:
            return None

        self.last_index = index
        self.cooldown_until = now_ms + self.cooldown_ms
        return self.notes[index]
