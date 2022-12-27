from textual.widgets import ListView, ListItem, Static
from textual.reactive import reactive
from textual.message import Message, MessageTarget
import dis
from types import CodeType

import executing.executing
import sys


class InstructionItem(ListItem):
    def __init__(self, inst, node):
        self.inst = inst
        n = "[green]:link:[/]" if node is not None else "  "
        text = f"{inst.offset:>3}:{n}{inst.opname}"
        if inst.arg is not None:
            text += f" [blue]{repr(inst.argval)}"

        self.node = node

        super().__init__(Static(text))


def codes(code):
    yield code
    for inst in dis.get_instructions(code):
        if isinstance(inst.argval, CodeType):
            yield from codes(inst.argval)


class Frame:
    pass


class BytecodeView(Static):
    DEFAULT_CSS = """
    ListView {
        height: 1fr;
        width: 1fr;
        border: solid $primary-background-lighten-2;
        background: $panel;
    }

    ListView:focus {
        border: double $primary-lighten-2;
    }
    """

    source = reactive(None)
    blocks = reactive([])

    def get_node(self, code, inst, line):

        frame = Frame()
        frame.f_lasti = inst.offset
        frame.f_code = code
        frame.f_globals = {}
        frame.f_lineno = line
        source = executing.Source.for_frame(frame)
        ex = source.executing(frame)
        return ex.node

    async def watch_source(self, _, source):
        if source is None:
            return
        print("set source", source)
        bytecodes = compile(source.tree, source.filename, "exec")
        print("set source", source)

        entries = []
        for code in codes(bytecodes):
            entries.append(ListItem(Static(f"[green]{code.co_name}:")))

            line_starts = dict(dis.findlinestarts(code))

            lineno = None
            for inst in dis.get_instructions(code):
                lineno = line_starts.get(inst.offset, lineno)

                if inst.is_jump_target:
                    entries.append(ListItem(Static("")))
                node = self.get_node(code, inst, lineno)
                entries.append(InstructionItem(inst, node))

        print("set entries", entries)

        self.query_one(ListView).remove()
        await self.mount(ListView(*entries))

    def compose(self):
        yield ListView()

    class NodeChanged(Message):
        """Node changed"""

        def __init__(self, sender: MessageTarget, node) -> None:
            self.node = node
            super().__init__(sender)

    async def on_list_view_highlighted(self, event):

        node = getattr(event.item, "node", None)
        if node is not None:

            await self.emit(self.NodeChanged(self, node))
