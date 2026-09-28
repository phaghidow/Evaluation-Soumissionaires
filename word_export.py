from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor


PAGE_WIDTH = Inches(11.69)
PAGE_HEIGHT = Inches(8.27)
PAGE_MARGIN = Inches(0.4)
TABLE_HEADER_COLOR = "1B2A3D"


def configure_landscape_document(document):
    """Set all document sections to A4 landscape with compact print margins."""
    for section in document.sections:
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width = PAGE_WIDTH
        section.page_height = PAGE_HEIGHT
        section.left_margin = PAGE_MARGIN
        section.right_margin = PAGE_MARGIN
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.header_distance = Inches(0.2)
        section.footer_distance = Inches(0.2)

    normal_style = document.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(9)
    normal_style.font.color.rgb = RGBColor(31, 41, 55)
    title_style = document.styles["Heading 1"]
    title_style.font.name = "Arial"
    title_style.font.size = Pt(16)
    title_style.font.bold = True
    title_style.font.color.rgb = RGBColor(27, 42, 61)

    return PAGE_WIDTH - 2 * PAGE_MARGIN


def format_landscape_table(
    table,
    column_weights,
    usable_width,
    font_size=8,
    left_align_columns=(1,),
):
    """Apply fixed proportional widths, repeated header, and compact readable cells."""
    if len(column_weights) != len(table.columns):
        raise ValueError("Un poids de largeur doit être fourni pour chaque colonne.")
    if any(weight <= 0 for weight in column_weights):
        raise ValueError("Les poids de largeur doivent être strictement positifs.")

    table.style = "Table Grid"
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER

    properties = table._tbl.tblPr
    layout = properties.find(qn("w:tblLayout"))
    if layout is None:
        layout = OxmlElement("w:tblLayout")
        properties.append(layout)
    layout.set(qn("w:type"), "fixed")

    table_width_twips = round(usable_width / Inches(1) * 1440)
    width_element = properties.find(qn("w:tblW"))
    if width_element is None:
        width_element = OxmlElement("w:tblW")
        properties.append(width_element)
    width_element.set(qn("w:w"), str(table_width_twips))
    width_element.set(qn("w:type"), "dxa")

    total_weight = sum(column_weights)
    for column_index, weight in enumerate(column_weights):
        column_width = Inches(
            usable_width / Inches(1) * weight / total_weight
        )
        table.columns[column_index].width = column_width
        for row in table.rows:
            row.cells[column_index].width = column_width

    if table.rows:
        header_properties = table.rows[0]._tr.get_or_add_trPr()
        if header_properties.find(qn("w:tblHeader")) is None:
            repeated_header = OxmlElement("w:tblHeader")
            repeated_header.set(qn("w:val"), "true")
            header_properties.append(repeated_header)

    for row_index, row in enumerate(table.rows):
        if row_index:
            row_properties = row._tr.get_or_add_trPr()
            if row_properties.find(qn("w:cantSplit")) is None:
                row_properties.append(OxmlElement("w:cantSplit"))
        for column_index, cell in enumerate(row.cells):
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            _set_cell_margins(cell)
            for paragraph in cell.paragraphs:
                paragraph.alignment = (
                    WD_ALIGN_PARAGRAPH.LEFT
                    if column_index in left_align_columns and row_index > 0
                    else WD_ALIGN_PARAGRAPH.CENTER
                )
                paragraph.paragraph_format.space_before = Pt(0)
                paragraph.paragraph_format.space_after = Pt(0)
                paragraph.paragraph_format.line_spacing = 1.0
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.size = Pt(font_size)
                    if row_index == 0:
                        run.font.bold = True
                        run.font.color.rgb = RGBColor(255, 255, 255)

            if row_index == 0:
                _set_cell_shading(cell, TABLE_HEADER_COLOR)


def _set_cell_margins(cell, top=55, start=70, bottom=55, end=70):
    cell_properties = cell._tc.get_or_add_tcPr()
    margins = cell_properties.first_child_found_in("w:tcMar")
    if margins is None:
        margins = OxmlElement("w:tcMar")
        cell_properties.append(margins)
    for side, value in (("top", top), ("start", start), ("bottom", bottom), ("end", end)):
        element = margins.find(qn(f"w:{side}"))
        if element is None:
            element = OxmlElement(f"w:{side}")
            margins.append(element)
        element.set(qn("w:w"), str(value))
        element.set(qn("w:type"), "dxa")


def _set_cell_shading(cell, fill):
    cell_properties = cell._tc.get_or_add_tcPr()
    shading = cell_properties.find(qn("w:shd"))
    if shading is None:
        shading = OxmlElement("w:shd")
        cell_properties.append(shading)
    shading.set(qn("w:fill"), fill)