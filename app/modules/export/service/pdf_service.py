import markdown
from weasyprint import HTML
from jinja2 import Template


class PDFService:

    def __init__(self):
        self.base_template = """
        <html>
        <head>
            <meta charset="utf-8">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    padding: 40px;
                    color: #1f2937;
                }
                h1, h2, h3 {
                    color: #111827;
                }
                code {
                    background: #f3f4f6;
                    padding: 4px 6px;
                    border-radius: 4px;
                }
                pre {
                    background: #f3f4f6;
                    padding: 10px;
                    border-radius: 6px;
                    overflow-x: auto;
                }
                table {
                    border-collapse: collapse;
                    width: 100%;
                }
                table, th, td {
                    border: 1px solid #ddd;
                }
                th, td {
                    padding: 8px;
                    text-align: left;
                }
            </style>
        </head>
        <body>
            {{ content }}
        </body>
        </html>
        """

    def generate_pdf(self, content: str, format_type: str) -> bytes:

        if format_type not in ["md", "html"]:
            raise ValueError("Formato inválido. Use 'md' ou 'html'")

        # 🔁 Se for markdown, converte para HTML
        if format_type == "md":
            content = markdown.markdown(
                content,
                extensions=["tables", "fenced_code"]
            )

        # 🔥 Aplica template base
        template = Template(self.base_template)
        final_html = template.render(content=content)

        # 🧾 Gera PDF
        pdf_bytes = HTML(string=final_html).write_pdf()

        return pdf_bytes