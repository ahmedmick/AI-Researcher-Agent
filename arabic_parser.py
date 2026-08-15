import os
import re
import arabic_reshaper
from bidi.algorithm import get_display
from rich.console import Console
from rich.align import Align

class ArabicParser():
    def __init__(self):
        pass

    def contains_arabic(self, text: str) -> bool:
        return any("\u0600" <= ch <= "\u06ff" for ch in text)

    def classify_line(self, line: str) -> dict:
        line_info = {"type": "", "content": "", "level": 0, "number": ""}

        if line == "":
            line_info["type"] = "blank"
        elif line.startswith("### "):
            line_info["type"] = "header"
            line_info["content"] = line[4:]
            line_info["level"] = 3
        elif line.startswith("## "):
            line_info["type"] = "header"
            line_info["content"] = line[3:]
            line_info["level"] = 2
        elif line.startswith(("---", "***")):
            line_info["type"] = "hr"
        elif line.startswith(("• ", "* ", "- ")):
            line_info["type"] = "bullet"
            line_info["content"] = line[2:]
        elif match := re.match(r"^(\d+)\. ", line):
            line_info["type"] = "numbered"
            line_info["number"] = match.group(1)
            line_info["content"] = line[match.end():]
        else:
            line_info["content"] = line

        return line_info

    def apply_bold_markup(self, text: str) -> str:
        normal_text = re.sub(r"@@B(\d+)@@(.*?)@@E\1@@", "[bold]\\2[/bold]", text)
        swapped_text = re.sub(r"@@E(\d+)@@(.*?)@@B\1@@", "[bold]\\2[/bold]", normal_text)
        return swapped_text

    def format_bidi_text(self, text):
        reshaped = arabic_reshaper.reshape(text)
        return get_display(reshaped)

    def insert_bold_markers(self, text: str) -> str:
        counter = [0]
        def replacer(match):
            idx = counter[0]
            counter[0] += 1
            return f"@@B{idx}@@{match.group(1)}@@E{idx}@@"
        return re.sub(r'\*\*(.*?)\*\*', replacer, text)

    def render_inline_bold(self, text: str):
        text_lines = text.split("\n")
        rendered_text = ""
        for line in text_lines:
            bold_line = self.insert_bold_markers(line)
            if not self.is_mintty():
                bidi_line = self.format_bidi_text(bold_line)
            else:
                bidi_line = bold_line
            rendered_line = self.apply_bold_markup(bidi_line)
            rendered_text += rendered_line + "\n"
        return rendered_text

    def render_line(self, line: dict, console: Console):
        match line["type"]:
            case "blank":
                console.print("")
            case "header":
                content = self.render_inline_bold(line["content"])
                style = "bold cyan" if line["level"] == 2 else "bold blue"
                console.print(
                    f"[{style}]{content}[/{style}]"
                    if self.is_mintty()
                    else Align.right(f"[{style}]{content}[/{style}]")
                )
            case "hr":
                console.print(
                    "[dim]" + "─" * 80 + "[/dim]"
                    if self.is_mintty()
                    else Align.right("[dim]" + "─" * 80 + "[/dim]")
                )
            case "bullet":
                content = self.render_inline_bold(line["content"])
                console.print(
                    f"  • {content}"
                    if self.is_mintty()
                    else Align.right(f"  • {content}")
                )
            case "numbered":
                content = self.render_inline_bold(line["content"])
                console.print(
                    f"  {line['number']}. {content}"
                    if self.is_mintty()
                    else Align.right(f"  {line['number']}. {content}")
                )
            case _:
                content = self.render_inline_bold(line["content"])
                console.print(
                    content
                    if self.is_mintty()
                    else Align.right(content)
                )

    def render_arabic_markdown(self, text: str, console: Console):
        lines = text.split("\n")
        for line in lines:
            temp_line = self.classify_line(line)
            self.render_line(temp_line, console)

    def is_mintty(self):
        return os.environ.get("MSYSTEM") is not None

x = ArabicParser()
test = x.insert_bold_markers("ذاك **Minecraft** [4].")
print(repr(test))

reshaped = arabic_reshaper.reshape(test)
bidi_result = get_display(reshaped)
print(repr(bidi_result))
