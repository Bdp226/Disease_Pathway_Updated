from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime
import os

out_dir = r"C:\Users\z005b8nt\Downloads\Digitization-of-Disease-Pathways-main-20260721T095451Z-1-001\Digitization-of-Disease-Pathways-main\output"
os.makedirs(out_dir, exist_ok=True)
pdf_path = os.path.join(out_dir, "detailed-project-output.pdf")

styles = getSampleStyleSheet()
style_h1 = styles["Title"]
style_h2 = styles["Heading2"]
style_p = styles["BodyText"]

story = []
story.append(Paragraph("Digitization of Disease Pathways", style_h1))
story.append(Paragraph("Detailed Project Output", style_h2))
story.append(Spacer(1, 0.2 * inch))

story.append(Paragraph("1. Overview", style_h2))
story.append(Paragraph("This detailed report captures the final verified status of the disease pathway platform after the layout, contrast, mapping, and similarity fixes across the app.", style_p))
story.append(Spacer(1, 0.1 * inch))

story.append(Paragraph("2. Major completed items", style_h2))
items = [
    "Removed global root/body layout constraints that were creating empty gutters on every disease page.",
    "Refined the Back to Diseases control with lighter contrast and a centered SVG arrow icon.",
    "Lightened stakeholder card surfaces so text remains readable against the dark background.",
    "Corrected disease similarity scoring to filter out generic clinical overlap and avoid false unrelated matches.",
    "Validated stakeholder icon mapping and deduplication for real disease-stage data, preventing repeated icons on a page.",
    "Verified the frontend build still compiles successfully after the final changes.",
]
for item in items:
    story.append(Paragraph("- " + item, style_p))

story.append(PageBreak())
story.append(Paragraph("3. Validation evidence", style_h2))
story.append(Paragraph("Frontend verification command: npm run build -- --logLevel error", style_p))
story.append(Paragraph("Result: successful build exit status 0", style_p))
story.append(Spacer(1, 0.15 * inch))
story.append(Paragraph("4. Notes and conclusions", style_h2))
story.append(Paragraph("The current project state is stable. The disease pages no longer show unintended empty side spacing, the back button is visually cleaner and better contrasted, and the disease matching logic is more trustworthy for real use.", style_p))

story.append(PageBreak())
story.append(Paragraph("5. Final status", style_h2))
story.append(Paragraph("The platform is in a verified working state for the current build, with the required UI and data-quality fixes applied and checked.", style_p))
story.append(Spacer(1, 0.2 * inch))
story.append(Paragraph("Generated on: " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"), style_p))

doc = SimpleDocTemplate(pdf_path, pagesize=A4, leftMargin=0.75 * inch, rightMargin=0.75 * inch, topMargin=0.75 * inch, bottomMargin=0.75 * inch)
doc.build(story)
print(pdf_path)
