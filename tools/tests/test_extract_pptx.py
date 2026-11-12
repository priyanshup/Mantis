"""IMP-102: a dropped PowerPoint deck is converted to Markdown like any other file: one section per slide, tables as tables, charts as their numbers,
pictures by name, and the speaker notes (which can carry a different figure from the slide). Decks are built here with python-pptx; nothing is read from the inbox."""
import sys; sys.dont_write_bytecode = True  # keep __pycache__ out of OneDrive
import base64, tempfile, unittest
from pathlib import Path

import extract

try:
    from pptx import Presentation
    from pptx.chart.data import CategoryChartData
    from pptx.enum.chart import XL_CHART_TYPE
    from pptx.util import Inches
except ImportError:   # the converter then skips decks with a message; there is nothing to test
    Presentation = None

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==")


@unittest.skipIf(Presentation is None, "python-pptx is not installed")
class Deck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "deck.pptx"
        self.prs = Presentation()

    def slide(self, layout=1, title="", bullets=(), notes=""):
        s = self.prs.slides.add_slide(self.prs.slide_layouts[layout])
        if title:
            s.shapes.title.text = title
        if bullets and layout == 1:
            tf = s.placeholders[1].text_frame
            tf.text = bullets[0][0]
            tf.paragraphs[0].level = bullets[0][1]
            for text, level in bullets[1:]:
                p = tf.add_paragraph()
                p.text, p.level = text, level
        if notes:
            s.notes_slide.notes_text_frame.text = notes
        return s

    def md(self):
        self.prs.save(str(self.path))
        return extract.from_pptx(self.path)

    def test_each_slide_is_a_numbered_section_with_its_title_in_order(self):
        self.slide(title="Plan for Q1", bullets=[("Goal", 0)])
        self.slide(title="Risks", bullets=[("Delay", 0)])
        text = self.md()
        self.assertLess(text.index("## Slide 1: Plan for Q1"), text.index("## Slide 2: Risks"))

    def test_bullets_keep_their_nesting(self):
        self.slide(title="T", bullets=[("Top", 0), ("Child", 1), ("Grandchild", 2)])
        text = self.md()
        self.assertIn("- Top\n", text)
        self.assertIn("  - Child\n", text)
        self.assertTrue(text.endswith("    - Grandchild"))

    def test_speaker_notes_are_kept_and_marked_so_they_are_not_taken_for_slide_text(self):
        self.slide(title="Numbers", bullets=[("Uptake 40%", 0)], notes="Correction: uptake was 34%, the slide is out of date.")
        text = self.md()
        self.assertIn("Speaker notes:", text)
        self.assertIn("Correction: uptake was 34%", text)
        self.assertLess(text.index("Uptake 40%"), text.index("Speaker notes:"))

    def test_a_slide_with_no_notes_has_no_notes_line(self):
        self.slide(title="T", bullets=[("x", 0)])
        self.assertNotIn("Speaker notes", self.md())

    def test_a_table_becomes_a_markdown_table_with_pipes_made_safe(self):
        s = self.slide(layout=5, title="Table slide")
        t = s.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
        for (r, c), v in {(0, 0): "Market", (0, 1): "Share", (1, 0): "A|B", (1, 1): "12%"}.items():
            t.cell(r, c).text = v
        text = self.md()
        self.assertIn("| Market | Share |", text)
        self.assertIn("|---|---|", text)
        self.assertIn("| A/B | 12% |", text)

    def test_a_chart_is_written_as_its_numbers(self):
        s = self.slide(layout=5, title="Chart slide")
        data = CategoryChartData()
        data.categories = ["Q1", "Q2"]
        data.add_series("Orders", (10, 25))
        s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(1), Inches(2), Inches(5), Inches(3), data)
        text = self.md()
        self.assertIn("Chart", text)
        self.assertIn("Orders", text)
        self.assertIn("Q2", text)
        self.assertIn("25", text)

    def test_a_picture_is_listed_by_name_not_dropped_silently(self):
        s = self.slide(layout=5, title="Picture slide")
        img = Path(self.tmp.name) / "diagram.png"
        img.write_bytes(PNG)
        s.shapes.add_picture(str(img), Inches(1), Inches(2))
        self.assertIn("[image:", self.md())

    def test_text_in_a_grouped_shape_is_found(self):
        s = self.slide(layout=5, title="Group slide")
        g = s.shapes.add_group_shape()
        box = g.shapes.add_textbox(Inches(1), Inches(2), Inches(3), Inches(1))
        box.text_frame.text = "Inside a group"
        self.assertIn("Inside a group", self.md())

    def test_a_hidden_slide_is_marked_hidden(self):
        s = self.slide(title="Spare", bullets=[("x", 0)])
        s._element.set("show", "0")
        self.assertIn("(hidden slide)", self.md())

    def test_shapes_are_read_top_to_bottom_not_in_the_order_they_were_added(self):
        s = self.slide(layout=6)
        s.shapes.add_textbox(Inches(1), Inches(5), Inches(3), Inches(1)).text_frame.text = "Lower box, added first"
        s.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)).text_frame.text = "Upper box, added second"
        text = self.md()
        self.assertLess(text.index("Upper box"), text.index("Lower box"))

    def test_a_slide_with_no_title_is_still_a_section(self):
        s = self.slide(layout=6)
        s.shapes.add_textbox(Inches(1), Inches(1), Inches(3), Inches(1)).text_frame.text = "Only a text box"
        text = self.md()
        self.assertIn("## Slide 1", text)
        self.assertIn("Only a text box", text)

    def test_convert_routes_a_pptx_file_to_the_converter(self):
        self.slide(title="Routed", bullets=[("x", 0)])
        self.prs.save(str(self.path))
        self.assertIn("## Slide 1: Routed", extract.convert(self.path))


if __name__ == "__main__":
    unittest.main()
