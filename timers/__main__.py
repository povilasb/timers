from pathlib import Path
import tomllib

from pydantic import BaseModel
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, Footer, Label, Static, TabbedContent
from wakepy import keep
from playsound import playsound

class Timer(BaseModel):
    name: str
    time: int


class MultiphaseTimer(BaseModel):
    name: str
    phases: list[Timer] = []


def _load_timers(path: Path | str) -> list[MultiphaseTimer]:
    with open(path, "rb") as f:
        data = tomllib.load(f)

    timers = []

    for name, phases in data.items():
        multiphase_timer = MultiphaseTimer(name=name)
        for (phase, time) in phases.items():
            multiphase_timer.phases.append(Timer(name=phase, time=time))
        timers.append(multiphase_timer)

    return timers


TIMERS = _load_timers("timers.toml")


class TimersApp(App):
    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
    ]
    CSS_PATH = "main.tcss"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        self.dark = False

        yield ControlButtons()

        with TabbedContent(*[timer.name for timer in TIMERS]):
            for multiphase_timer in TIMERS:
                phases = [LabelledTimer(timer.name, timer.time) for timer in multiphase_timer.phases]
                yield VerticalScroll(*phases)

        yield Footer()

        self._curr_tab_id = ""

    def on_tabbed_content_tab_activated(self, msg: TabbedContent.TabActivated) -> None:
        self._curr_tab_id = msg.tab.id

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Event handler called when a button is pressed."""
        if event.button.id == "start":
            self._start_next_timer()

    def on_time_display_finished(self, msg: "TimeDisplay.Finished") -> None:
        playsound("bell.mp3")
        self._start_next_timer()

    def _start_next_timer(self) -> None:
        for timer in self.query(f"#{self._curr_tab_id} .inactive"):
            if isinstance(timer, LabelledTimer):
                timer.start()
                return

        playsound("tada.mp3")


class ControlButtons(Static):
    DEFAULT_CSS = """
    ControlButtons {
        dock: top;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Start", id="start", variant="success")
        yield Button("Stop", id="stop", variant="error")


class LabelledTimer(Static):
    def __init__(self, label: str, time_secs: int) -> None:
        super().__init__()
        self.set_class(True, "inactive")

        self._label = label
        self._time_secs = time_secs

    def compose(self) -> ComposeResult:
        w = TimeDisplay()
        w.time = self._time_secs
        yield w
        yield Label(self._label)

    def start(self) -> None:
        self.toggle_class("inactive", "active")
        self.query_one(TimeDisplay).start()

    def on_time_display_finished(self, msg: "TimeDisplay.Finished") -> None:
        self.toggle_class("active", "finished")


class TimeDisplay(Static):
    """A widget to display elapsed time."""

    time = reactive(0.0)

    class Finished(Message):
        """Message sent when the timer finishes."""

    def on_mount(self):
        self.update_timer = self.set_interval(1, self._update_time, pause=True)

    def watch_time(self, time: float) -> None:
        """Called when the time attribute changes."""
        minutes, seconds = divmod(time, 60)
        hours, minutes = divmod(minutes, 60)
        self.update(f"{hours:02,.0f}:{minutes:02.0f}:{seconds:05.2f}")

    def start(self) -> None:
        """Method to start (or resume) time updating."""
        self.update_timer.resume()

    def stop(self) -> None:
        """Method to stop the time display updating."""
        self.update_timer.stop()
        self.time = 0

    def _update_time(self) -> None:
        """Method to update the time to the current time."""
        self.time -= 1
        if self.time <= 0:
            self.update_timer.pause()
            self.post_message(self.Finished())


if __name__ == "__main__":
    with keep.running() as k:
        TimersApp().run()
