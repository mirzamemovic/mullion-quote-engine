"""The client quote PDF and the workshop PDF (PLAN.md section 8, milestone M7).

``labels`` holds the words and number formats, ``drawing`` the SVG window drawings and bar
strips, ``content`` turns a quote revision into what each page shows, and ``render`` fills the
Jinja2 templates and lays them out with WeasyPrint, which may fetch nothing but bundled fonts.
"""
