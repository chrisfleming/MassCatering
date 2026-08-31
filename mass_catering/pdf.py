from __future__ import annotations

from collections import defaultdict
from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import (
    ParagraphStyle,
    getSampleStyleSheet,
)
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from mass_catering.compiler import (
    CompilationResult,
    ScaledRecipe,
)
from mass_catering.rendering import format_quantity


PAGE_WIDTH, PAGE_HEIGHT = A4

DARK_GREEN = colors.HexColor("#176B4D")
MID_GREEN = colors.HexColor("#DDEFE7")
PALE_GREEN = colors.HexColor("#F1F8F5")
PALE_AMBER = colors.HexColor("#FFF5D6")
DARK_GREY = colors.HexColor("#333333")
MID_GREY = colors.HexColor("#666666")
LIGHT_GREY = colors.HexColor("#E4E7E5")


def safe_text(value: object | None) -> str:
    """Escape text for use inside ReportLab paragraphs."""

    if value is None:
        return ""

    text = str(value).strip()

    return escape(text).replace("\n", "<br/>")


def make_styles() -> dict[str, ParagraphStyle]:
    """Create the PDF's paragraph styles."""

    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "MassCateringTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=25,
            leading=30,
            textColor=DARK_GREEN,
            alignment=TA_CENTER,
            spaceAfter=8 * mm,
        ),
        "subtitle": ParagraphStyle(
            "MassCateringSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=16,
            textColor=MID_GREY,
            alignment=TA_CENTER,
            spaceAfter=5 * mm,
        ),
        "heading1": ParagraphStyle(
            "MassCateringHeading1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
            textColor=DARK_GREEN,
            spaceBefore=3 * mm,
            spaceAfter=4 * mm,
            keepWithNext=True,
        ),
        "heading2": ParagraphStyle(
            "MassCateringHeading2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=DARK_GREEN,
            spaceBefore=3 * mm,
            spaceAfter=3 * mm,
            keepWithNext=True,
        ),
        "heading3": ParagraphStyle(
            "MassCateringHeading3",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=DARK_GREY,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
            keepWithNext=True,
        ),
        "body": ParagraphStyle(
            "MassCateringBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=DARK_GREY,
            spaceAfter=2 * mm,
        ),
        "small": ParagraphStyle(
            "MassCateringSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=MID_GREY,
        ),
        "note": ParagraphStyle(
            "MassCateringNote",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9.5,
            leading=13,
            textColor=DARK_GREY,
        ),
        "table_header": ParagraphStyle(
            "MassCateringTableHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=colors.white,
        ),
        "table_cell": ParagraphStyle(
            "MassCateringTableCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=DARK_GREY,
        ),
    }


def add_note_box(
    story: list,
    heading: str,
    text: str | None,
    styles: dict[str, ParagraphStyle],
    background_color=PALE_AMBER,
) -> None:
    """Add a labelled note box when text is present."""

    if not text or not str(text).strip():
        return

    content = [
        Paragraph(
            f"<b>{safe_text(heading)}</b>",
            styles["note"],
        ),
        Paragraph(
            safe_text(text),
            styles["note"],
        ),
    ]

    table = Table(
        [[content]],
        colWidths=[170 * mm],
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    background_color,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    LIGHT_GREY,
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
            ]
        )
    )

    story.extend(
        [
            table,
            Spacer(1, 3 * mm),
        ]
    )


def draw_page_number(canvas, document) -> None:
    """Draw a footer and page number on each PDF page."""

    canvas.saveState()

    canvas.setStrokeColor(LIGHT_GREY)
    canvas.setLineWidth(0.5)
    canvas.line(
        document.leftMargin,
        14 * mm,
        PAGE_WIDTH - document.rightMargin,
        14 * mm,
    )

    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(MID_GREY)

    canvas.drawString(
        document.leftMargin,
        9 * mm,
        "Mass Catering",
    )

    canvas.drawRightString(
        PAGE_WIDTH - document.rightMargin,
        9 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


def add_cover_page(
    story: list,
    menu: dict,
    result: CompilationResult,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Add the menu cover page."""

    story.append(Spacer(1, 28 * mm))

    story.append(
        Paragraph(
            safe_text(menu.get("name", "Mass Catering Menu")),
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "Weekend catering menu and chef recipe pack",
            styles["subtitle"],
        )
    )

    if menu.get("description"):
        story.append(
            Paragraph(
                safe_text(menu["description"]),
                styles["body"],
            )
        )

    attendance = menu.get("attendance", {})

    summary_rows = [
        [
            Paragraph("<b>Scheduled dishes</b>", styles["table_cell"]),
            Paragraph(
                str(
                    len(
                        [
                            recipe
                            for recipe in result.scaled_recipes
                            if recipe.meal != "provisions"
                        ]
                    )
                ),
                styles["table_cell"],
            ),
        ],
        [
            Paragraph("<b>Shopping-list items</b>", styles["table_cell"]),
            Paragraph(
                str(len(result.shopping_list)),
                styles["table_cell"],
            ),
        ],
    ]

    if attendance:
        if attendance.get("adults") is not None:
            summary_rows.append(
                [
                    Paragraph("<b>Adults</b>", styles["table_cell"]),
                    Paragraph(
                        str(attendance["adults"]),
                        styles["table_cell"],
                    ),
                ]
            )

        if attendance.get("children") is not None:
            summary_rows.append(
                [
                    Paragraph("<b>Children</b>", styles["table_cell"]),
                    Paragraph(
                        str(attendance["children"]),
                        styles["table_cell"],
                    ),
                ]
            )

    summary = Table(
        summary_rows,
        colWidths=[70 * mm, 35 * mm],
        hAlign="CENTER",
    )

    summary.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    PALE_GREEN,
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    LIGHT_GREY,
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.25,
                    LIGHT_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    4 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
            ]
        )
    )

    story.extend(
        [
            Spacer(1, 6 * mm),
            summary,
            Spacer(1, 7 * mm),
        ]
    )

    add_note_box(
        story,
        "Menu notes",
        menu.get("notes"),
        styles,
        background_color=PALE_GREEN,
    )

    story.append(PageBreak())


def add_schedule(
    story: list,
    menu: dict,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Add a summary timetable for the weekend."""

    story.append(
        Paragraph(
            "Weekend schedule",
            styles["heading1"],
        )
    )

    rows = [
        [
            Paragraph("Day", styles["table_header"]),
            Paragraph("Meal", styles["table_header"]),
            Paragraph("Event", styles["table_header"]),
            Paragraph("People", styles["table_header"]),
            Paragraph("Dishes", styles["table_header"]),
        ]
    ]

    for event in menu.get("events", []):
        dish_names = [
            safe_text(dish["recipe"].replace("_", " "))
            for dish in event.get("dishes", [])
        ]

        rows.append(
            [
                Paragraph(
                    safe_text(event.get("day", "")),
                    styles["table_cell"],
                ),
                Paragraph(
                    safe_text(event.get("meal", "")),
                    styles["table_cell"],
                ),
                Paragraph(
                    safe_text(event.get("name", "")),
                    styles["table_cell"],
                ),
                Paragraph(
                    str(event.get("people", "")),
                    styles["table_cell"],
                ),
                Paragraph(
                    "<br/>".join(dish_names),
                    styles["table_cell"],
                ),
            ]
        )

    table = Table(
        rows,
        colWidths=[
            24 * mm,
            25 * mm,
            39 * mm,
            17 * mm,
            65 * mm,
        ],
        repeatRows=1,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    DARK_GREEN,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, PALE_GREEN],
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    LIGHT_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
            ]
        )
    )

    story.extend(
        [
            table,
            PageBreak(),
        ]
    )


def add_scaled_recipe(
    story: list,
    recipe: ScaledRecipe,
    rounding_places: int,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Add one chef-friendly scaled recipe."""

    story.append(
        Paragraph(
            safe_text(recipe.name),
            styles["heading1"],
        )
    )

    event_text = f"{recipe.day} - {recipe.meal}"

    if recipe.event_name:
        event_text += f" - {recipe.event_name}"

    details = Table(
        [
            [
                Paragraph("<b>Event</b>", styles["table_cell"]),
                Paragraph(
                    safe_text(event_text),
                    styles["table_cell"],
                ),
            ],
            [
                Paragraph("<b>Prepare for</b>", styles["table_cell"]),
                Paragraph(
                    (
                        f"{recipe.people} people"
                        if recipe.people
                        else "General provision"
                    ),
                    styles["table_cell"],
                ),
            ],
        ],
        colWidths=[34 * mm, 136 * mm],
    )

    details.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    MID_GREEN,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    LIGHT_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2.5 * mm,
                ),
            ]
        )
    )

    story.extend(
        [
            details,
            Spacer(1, 4 * mm),
        ]
    )

    add_note_box(
        story,
        "Notes for this meal",
        recipe.event_notes,
        styles,
        background_color=PALE_GREEN,
    )

    add_note_box(
        story,
        "Preparation notes for the chef",
        recipe.preparation_notes,
        styles,
        background_color=PALE_AMBER,
    )

    story.append(
        Paragraph(
            "Ingredients",
            styles["heading2"],
        )
    )

    ingredient_rows = [
        [
            Paragraph("Ingredient", styles["table_header"]),
            Paragraph("Required amount", styles["table_header"]),
        ]
    ]

    for ingredient_name, quantity in sorted(
        recipe.ingredients.items()
    ):
        ingredient_rows.append(
            [
                Paragraph(
                    safe_text(
                        ingredient_name.replace("_", " ")
                    ),
                    styles["table_cell"],
                ),
                Paragraph(
                    safe_text(
                        format_quantity(
                            quantity,
                            rounding_places,
                        )
                    ),
                    styles["table_cell"],
                ),
            ]
        )

    ingredient_table = Table(
        ingredient_rows,
        colWidths=[105 * mm, 65 * mm],
        repeatRows=1,
    )

    ingredient_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    DARK_GREEN,
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, PALE_GREEN],
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.35,
                    LIGHT_GREY,
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    3 * mm,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    2.2 * mm,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    2.2 * mm,
                ),
            ]
        )
    )

    story.extend(
        [
            ingredient_table,
            Spacer(1, 4 * mm),
        ]
    )

    if recipe.method:
        story.extend(
            [
                Paragraph("Method", styles["heading2"]),
                Paragraph(
                    safe_text(recipe.method),
                    styles["body"],
                ),
            ]
        )

    add_note_box(
        story,
        "Recipe notes",
        recipe.recipe_notes,
        styles,
        background_color=PALE_GREEN,
    )

    story.append(PageBreak())


def add_shopping_list(
    story: list,
    result: CompilationResult,
    food_catalogue: dict,
    rounding_places: int,
    styles: dict[str, ParagraphStyle],
) -> None:
    """Add a shopping list grouped by shop."""

    story.append(
        Paragraph(
            "Shopping list",
            styles["heading1"],
        )
    )

    shops: dict[str, list[tuple[str, object]]] = defaultdict(list)

    for ingredient_name, quantity in result.shopping_list.items():
        details = food_catalogue.get(ingredient_name, {})

        if not isinstance(details, dict):
            details = {}

        shop = details.get("shop", "Supermarket")

        shops[str(shop)].append(
            (ingredient_name, quantity)
        )

    for shop in sorted(shops):
        story.append(
            Paragraph(
                safe_text(shop),
                styles["heading2"],
            )
        )

        rows = [
            [
                Paragraph("Done", styles["table_header"]),
                Paragraph("Ingredient", styles["table_header"]),
                Paragraph("Quantity", styles["table_header"]),
            ]
        ]

        for ingredient_name, quantity in sorted(
            shops[shop],
            key=lambda item: item[0].casefold(),
        ):
            rows.append(
                [
                    Paragraph("☐", styles["table_cell"]),
                    Paragraph(
                        safe_text(
                            ingredient_name.replace("_", " ")
                        ),
                        styles["table_cell"],
                    ),
                    Paragraph(
                        safe_text(
                            format_quantity(
                                quantity,
                                rounding_places,
                            )
                        ),
                        styles["table_cell"],
                    ),
                ]
            )

        table = Table(
            rows,
            colWidths=[
                16 * mm,
                104 * mm,
                50 * mm,
            ],
            repeatRows=1,
        )

        table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        DARK_GREEN,
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, PALE_GREEN],
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.35,
                        LIGHT_GREY,
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "MIDDLE",
                    ),
                    (
                        "ALIGN",
                        (0, 1),
                        (0, -1),
                        "CENTER",
                    ),
                    (
                        "LEFTPADDING",
                        (0, 0),
                        (-1, -1),
                        3 * mm,
                    ),
                    (
                        "RIGHTPADDING",
                        (0, 0),
                        (-1, -1),
                        3 * mm,
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        2.2 * mm,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        2.2 * mm,
                    ),
                ]
            )
        )

        story.extend(
            [
                table,
                Spacer(1, 5 * mm),
            ]
        )


def generate_menu_pdf(
    menu: dict,
    result: CompilationResult,
    food_catalogue: dict,
    rounding_places: int = 2,
) -> bytes:
    """Generate and return a complete menu PDF as bytes."""

    buffer = BytesIO()
    styles = make_styles()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=20 * mm,
        leftMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=str(menu.get("name", "Mass Catering Menu")),
        author="Mass Catering",
        subject="Catering menu, recipes and shopping list",
    )

    story: list = []

    add_cover_page(
        story=story,
        menu=menu,
        result=result,
        styles=styles,
    )

    add_schedule(
        story=story,
        menu=menu,
        styles=styles,
    )

    general_provisions = [
        recipe
        for recipe in result.scaled_recipes
        if recipe.meal == "provisions"
    ]

    scheduled_recipes = [
        recipe
        for recipe in result.scaled_recipes
        if recipe.meal != "provisions"
    ]

    if general_provisions:
        story.append(
            Paragraph(
                "General provisions",
                styles["heading1"],
            )
        )

        story.append(
            Paragraph(
                (
                    "These quantities support the wider catering "
                    "arrangements rather than one scheduled meal."
                ),
                styles["body"],
            )
        )

        story.append(PageBreak())

        for recipe in general_provisions:
            add_scaled_recipe(
                story=story,
                recipe=recipe,
                rounding_places=rounding_places,
                styles=styles,
            )

    for recipe in scheduled_recipes:
        add_scaled_recipe(
            story=story,
            recipe=recipe,
            rounding_places=rounding_places,
            styles=styles,
        )

    add_shopping_list(
        story=story,
        result=result,
        food_catalogue=food_catalogue,
        rounding_places=rounding_places,
        styles=styles,
    )

    document.build(
        story,
        onFirstPage=draw_page_number,
        onLaterPages=draw_page_number,
    )

    return buffer.getvalue()