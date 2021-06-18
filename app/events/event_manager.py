from app.data.database import DB
from app.events.event import Event
from app.engine.game_state import game
from app.engine import action, evaluate

import logging

class EventManager():
    def __init__(self):
        self.all_events = []  # Keeps all events, both in use and not yet used
        self.event_stack = []  # A stack of events that haven't been used yet

    def trigger(self, trigger, unit=None, unit2=None, item=None, position=None, region=None):
        unit1 = unit  # noqa: F841
        triggered_events = []
        for event_prefab in DB.events.get(trigger, game.level.nid):
            try:
                result = evaluate.evaluate(event_prefab.condition, unit, unit2, item, position, region)
                logging.debug("%s %s: %s", event_prefab.trigger, event_prefab.condition, result)
                if event_prefab.nid not in game.already_triggered_events and result:
                    triggered_events.append(event_prefab)
            except:
                logging.error("Condition {%s} could not be evaluated" % event_prefab.condition)

        new_event = False
        sorted_events = sorted(triggered_events, key=lambda x: x.priority)
        for event_prefab in sorted_events:
            self.add_event(event_prefab.nid, event_prefab.commands, unit, unit2, item, position, region)
            new_event = True
            if event_prefab.only_once:
                action.do(action.OnlyOnceEvent(event_prefab.nid))
        return new_event

    def add_event(self, nid, commands, unit=None, unit2=None, item=None, position=None, region=None):
        event = Event(nid, commands, unit, unit2, item, position, region)
        self.all_events.append(event)
        self.event_stack.append(event)
        game.state.change('event')

    def append(self, event):
        self.all_events.append(event)
        self.event_stack.append(event)

    def get(self):
        if self.event_stack:
            return self.event_stack.pop()
        return None

    def end(self, event):
        if event in self.all_events:
            self.all_events.remove(event)

    def save(self):
        all_events = [event.save() for event in self.all_events]
        return all_events

    @classmethod
    def restore(cls, all_events=None):
        self = cls()
        if all_events is None:
            all_events = []
        for event in all_events:
            new_event = Event.restore(event)
            self.all_events.append(new_event)
            self.event_stack.append(new_event)

        return self
