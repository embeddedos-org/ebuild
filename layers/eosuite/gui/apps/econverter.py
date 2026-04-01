# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite eConverter — Universal file converter: Word→PDF, Image→PDF, CSV↔JSON, and more.
"""
import os
import io
import json
import csv
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class EConverter(ttk.Frame):
    CONVERSIONS = [
        ("📄 Word (.docx) → PDF", "_docx_to_pdf", "docx", "pdf"),
        ("🖼 Image (PNG/JPG/BMP) → PDF", "_image_to_pdf", "image", "pdf"),
        ("📄 Text (.txt) → PDF", "_txt_to_pdf", "txt", "pdf"),
        ("📄 HTML → PDF", "_html_to_pdf", "html", "pdf"),
        ("📊 CSV → JSON", "_csv_to_json", "csv", "json"),
        ("📊 JSON → CSV", "_json_to_csv", "json", "csv"),
        ("📄 Text → JSON Lines", "_txt_to_jsonl", "txt", "jsonl"),
        ("📄 JSON → Formatted JSON", "_json_format", "json", "json"),
        ("🔤 Text → Uppercase", "_txt_upper", "txt", "txt"),
        ("🔤 Text → Lowercase", "_txt_lower", "txt", "txt"),
        ("🔐 Text → Base64", "_txt_to_base64", "txt", "b64"),
        ("🔓 Base64 → Text", "_base64_to_txt", "b64", "txt"),
        ("🔢 Text → Hex Dump", "_txt_to_hex", "txt", "hex"),
        ("📑 Lines → Sorted", "_lines_sort", "txt", "txt"),
        ("📑 Lines → Unique", "_lines_unique", "txt", "txt"),
        ("📑 Lines → Reversed", "_lines_reverse", "txt", "txt"),
        ("🖼 Image → Base64", "_image_to_base64", "image", "b64"),
        ("📄 Markdown → HTML", "_md_to_html", "md", "html"),
    ]

    FILE_FILTERS = {
        "docx": [("Word Documents", "*.docx")],
        "image": [("Images", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")],
        "csv": [("CSV files", "*.csv")],
        "json": [("JSON files", "*.json")],
        "txt": [("Text files", "*.txt")],
        "html": [("HTML files", "*.html *.htm")],
        "md": [("Markdown", "*.md")],
        "b64": [("Base64 files", "*.b64 *.txt")],
    }

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self._source_path = None
        c = self.app.theme.colors

        container = ttk.Frame(self, padding=20)
        container.pack(fill=tk.BOTH, expand=True)
        ttk.Label(container, text="🔄 eConverter", font=("Segoe UI", 18, "bold")).pack(pady=(0, 4))
        ttk.Label(container, text="Convert files between formats — Word/Image/Text → PDF and more",
                  font=("Segoe UI", 11)).pack(pady=(0, 20))

        # Conversion type (pick first so file filter adapts)
        conv_frame = ttk.Frame(container)
        conv_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(conv_frame, text="Conversion:", width=14).pack(side=tk.LEFT)
        self.conv_var = tk.StringVar(value=self.CONVERSIONS[0][0])
        conv_names = [c[0] for c in self.CONVERSIONS]
        self.conv_combo = ttk.Combobox(conv_frame, textvariable=self.conv_var,
                                       values=conv_names, state="readonly", width=45)
        self.conv_combo.pack(fill=tk.X, expand=True, side=tk.LEFT, padx=4)

        # Source file
        src_frame = ttk.Frame(container)
        src_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(src_frame, text="Source File:", width=14).pack(side=tk.LEFT)
        self.src_var = tk.StringVar(value="No file selected")
        ttk.Entry(src_frame, textvariable=self.src_var, state="readonly").pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4)
        ttk.Button(src_frame, text="Browse", command=self._browse).pack(side=tk.RIGHT)

        # Output file
        out_frame = ttk.Frame(container)
        out_frame.pack(fill=tk.X, padx=20, pady=4)
        ttk.Label(out_frame, text="Output File:", width=14).pack(side=tk.LEFT)
        self.out_var = tk.StringVar(value="Auto (same folder)")
        ttk.Entry(out_frame, textvariable=self.out_var).pack(
            fill=tk.X, expand=True, side=tk.LEFT, padx=4)
        ttk.Button(out_frame, text="Browse", command=self._browse_output).pack(side=tk.RIGHT)

        # Convert button
        btn_frame = ttk.Frame(container)
        btn_frame.pack(pady=16)
        ttk.Button(btn_frame, text="🔄 Convert Now", command=self._convert).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="📂 Open Output Folder",
                   command=self._open_output_folder).pack(side=tk.LEFT, padx=4)

        # Status / preview
        ttk.Label(container, text="Output / Preview:", font=("Segoe UI", 11, "bold")).pack(
            anchor=tk.W, padx=20)
        self.preview = tk.Text(container, height=12, font=("Consolas", 10), bg=c["terminal_bg"],
                               fg=c["terminal_fg"], relief=tk.FLAT, borderwidth=4, padx=4, pady=4)
        self.preview.pack(fill=tk.BOTH, expand=True, padx=20, pady=4)

        # Dependency info
        self.dep_label = ttk.Label(container, text="", foreground="#888888", font=("Segoe UI", 9))
        self.dep_label.pack(pady=(4, 0))
        self._check_deps()

    def _check_deps(self):
        missing = []
        try:
            import PIL
        except ImportError:
            missing.append("Pillow (pip install Pillow)")
        try:
            import docx
        except ImportError:
            missing.append("python-docx (pip install python-docx)")
        if missing:
            self.dep_label.config(
                text=f"Optional: install {', '.join(missing)} for full Word/Image→PDF support")

    def _get_conv(self):
        name = self.conv_var.get()
        for c in self.CONVERSIONS:
            if c[0] == name:
                return c
        return None

    def _browse(self):
        conv = self._get_conv()
        src_type = conv[2] if conv else "txt"
        ft = self.FILE_FILTERS.get(src_type, [("All files", "*.*")])
        ft.append(("All files", "*.*"))
        path = filedialog.askopenfilename(filetypes=ft)
        if path:
            self._source_path = path
            self.src_var.set(path)

    def _browse_output(self):
        conv = self._get_conv()
        ext = conv[3] if conv else "txt"
        path = filedialog.asksaveasfilename(defaultextension=f".{ext}",
                                            filetypes=[(f"{ext.upper()} files", f"*.{ext}"),
                                                       ("All files", "*.*")])
        if path:
            self.out_var.set(path)

    def _get_output_path(self, ext):
        out = self.out_var.get().strip()
        if out and out != "Auto (same folder)" and not out.startswith("No "):
            return out
        if self._source_path:
            base = os.path.splitext(self._source_path)[0]
            return f"{base}.{ext}"
        return None

    def _log(self, text):
        self.preview.insert(tk.END, text + "\n")
        self.preview.see(tk.END)

    def _convert(self):
        if not self._source_path:
            messagebox.showwarning("Warning", "Select a source file first.")
            return
        conv = self._get_conv()
        if not conv:
            return
        method = getattr(self, conv[1], None)
        if not method:
            messagebox.showerror("Error", "Conversion not implemented.")
            return
        self.preview.delete("1.0", tk.END)
        try:
            method()
            self.app.set_status(f"Converted: {conv[0]}")
        except Exception as e:
            self._log(f"Error: {e}")
            messagebox.showerror("Conversion Error", str(e))

    def _open_output_folder(self):
        out = self.out_var.get().strip()
        folder = os.path.dirname(out) if out and out != "Auto (same folder)" else (
            os.path.dirname(self._source_path) if self._source_path else os.getcwd())
        if sys.platform == "win32":
            os.startfile(folder)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", folder])
        else:
            subprocess.Popen(["xdg-open", folder])

    # ── PDF Conversions ───────────────────────────────────────────────

    def _docx_to_pdf(self):
        out = self._get_output_path("pdf")
        try:
            from docx import Document
        except ImportError:
            self._log("python-docx not installed. Trying system conversion...")
            self._system_convert_to_pdf()
            return

        doc = Document(self._source_path)
        text_lines = []
        for para in doc.paragraphs:
            text_lines.append(para.text)
        full_text = "\n".join(text_lines)

        self._text_to_pdf_file(full_text, out, title=os.path.basename(self._source_path))
        self._log(f"✅ Converted Word → PDF: {out}")
        self.out_var.set(out)

    def _image_to_pdf(self):
        out = self._get_output_path("pdf")
        try:
            from PIL import Image
            img = Image.open(self._source_path)
            if img.mode == "RGBA":
                img = img.convert("RGB")
            img.save(out, "PDF", resolution=150.0)
            self._log(f"✅ Image → PDF: {out}")
            self._log(f"   Size: {img.size[0]}×{img.size[1]}")
            self.out_var.set(out)
        except ImportError:
            # Built-in fallback: embed raw image in a minimal PDF wrapper
            self._log("Using built-in image→PDF converter...")
            try:
                with open(self._source_path, "rb") as f:
                    img_data = f.read()
                ext = os.path.splitext(self._source_path)[1].lower()
                if ext in (".jpg", ".jpeg"):
                    self._embed_jpeg_pdf(img_data, out)
                else:
                    self._log("Built-in converter supports JPEG only.")
                    self._log("For PNG/BMP/GIF, the app bundles Pillow automatically.")
                    self._log("If you see this, the build may be incomplete.")
            except Exception as e:
                self._log(f"Error: {e}")

    def _txt_to_pdf(self):
        out = self._get_output_path("pdf")
        with open(self._source_path, "r", encoding="utf-8") as f:
            content = f.read()
        self._text_to_pdf_file(content, out, title=os.path.basename(self._source_path))
        self._log(f"✅ Text → PDF: {out}")
        self.out_var.set(out)

    def _html_to_pdf(self):
        out = self._get_output_path("pdf")
        with open(self._source_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Strip HTML to text, then make PDF
        import html.parser

        class HTMLStripper(html.parser.HTMLParser):
            def __init__(self):
                super().__init__()
                self.text = []

            def handle_data(self, data):
                self.text.append(data)

        s = HTMLStripper()
        s.feed(content)
        plain = "".join(s.text)
        self._text_to_pdf_file(plain, out, title=os.path.basename(self._source_path))
        self._log(f"✅ HTML → PDF: {out}")
        self.out_var.set(out)

    def _text_to_pdf_file(self, text, output_path, title="eConverter"):
        """Generate a simple PDF from text using raw PDF commands (no dependencies)."""
        lines = text.split("\n")
        page_lines = 58
        pages = [lines[i:i + page_lines] for i in range(0, max(len(lines), 1), page_lines)]

        objects = []
        obj_id = 0

        def add_obj(content):
            nonlocal obj_id
            obj_id += 1
            objects.append((obj_id, content))
            return obj_id

        catalog_id = add_obj(None)
        pages_id = add_obj(None)

        page_ids = []
        stream_ids = []
        for page_lines_chunk in pages:
            stream_text = "BT\n/F1 10 Tf\n36 756 Td\n12 TL\n"
            for line in page_lines_chunk:
                safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                stream_text += f"({safe}) Tj T*\n"
            stream_text += "ET"
            stream_id = add_obj(f"<< /Length {len(stream_text)} >>\nstream\n{stream_text}\nendstream")
            stream_ids.append(stream_id)
            page_id = add_obj(None)
            page_ids.append(page_id)

        font_id = add_obj("<< /Type /Font /Subtype /Type1 /BaseFont /Courier >>")

        # Fill in deferred objects
        objects[catalog_id - 1] = (catalog_id,
                                   f"<< /Type /Catalog /Pages {pages_id} 0 R >>")
        kids = " ".join(f"{pid} 0 R" for pid in page_ids)
        objects[pages_id - 1] = (pages_id,
                                 f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>")
        for i, pid in enumerate(page_ids):
            objects[pid - 1] = (pid,
                                f"<< /Type /Page /Parent {pages_id} 0 R "
                                f"/MediaBox [0 0 612 792] "
                                f"/Contents {stream_ids[i]} 0 R "
                                f"/Resources << /Font << /F1 {font_id} 0 R >> >> >>")

        # Write PDF
        with open(output_path, "wb") as f:
            f.write(b"%PDF-1.4\n")
            offsets = {}
            for oid, content in objects:
                offsets[oid] = f.tell()
                f.write(f"{oid} 0 obj\n{content}\nendobj\n".encode())
            xref_pos = f.tell()
            f.write(b"xref\n")
            f.write(f"0 {len(objects) + 1}\n".encode())
            f.write(b"0000000000 65535 f \n")
            for oid in range(1, len(objects) + 1):
                f.write(f"{offsets[oid]:010d} 00000 n \n".encode())
            f.write(b"trailer\n")
            f.write(f"<< /Size {len(objects) + 1} /Root {catalog_id} 0 R >>\n".encode())
            f.write(b"startxref\n")
            f.write(f"{xref_pos}\n".encode())
            f.write(b"%%EOF\n")

    def _system_convert_to_pdf(self):
        """Fallback: try LibreOffice or wkhtmltopdf for conversion."""
        out = self._get_output_path("pdf")
        for cmd in ["soffice", "libreoffice"]:
            try:
                result = subprocess.run(
                    [cmd, "--headless", "--convert-to", "pdf",
                     "--outdir", os.path.dirname(out), self._source_path],
                    capture_output=True, text=True, timeout=30)
                if result.returncode == 0:
                    self._log(f"✅ Converted via LibreOffice: {out}")
                    self.out_var.set(out)
                    return
            except FileNotFoundError:
                continue
        self._log("No system converter found. Install python-docx or LibreOffice.")

    # ── Text Conversions ──────────────────────────────────────────────

    def _read_text(self):
        with open(self._source_path, "r", encoding="utf-8") as f:
            return f.read()

    def _csv_to_json(self):
        content = self._read_text()
        result = json.dumps(list(csv.DictReader(content.strip().split("\n"))), indent=2)
        self._log(result)

    def _json_to_csv(self):
        content = self._read_text()
        data = json.loads(content)
        if not isinstance(data, list) or not data:
            self._log("Error: JSON must be an array of objects")
            return
        out = io.StringIO()
        w = csv.DictWriter(out, fieldnames=data[0].keys())
        w.writeheader()
        w.writerows(data)
        self._log(out.getvalue())

    def _txt_to_jsonl(self):
        content = self._read_text()
        result = "\n".join(json.dumps({"line": i + 1, "text": l})
                           for i, l in enumerate(content.strip().split("\n")))
        self._log(result)

    def _json_format(self):
        content = self._read_text()
        self._log(json.dumps(json.loads(content), indent=2, sort_keys=True))

    def _txt_upper(self):
        self._log(self._read_text().upper())

    def _txt_lower(self):
        self._log(self._read_text().lower())

    def _txt_to_base64(self):
        import base64
        self._log(base64.b64encode(self._read_text().encode()).decode())

    def _base64_to_txt(self):
        import base64
        self._log(base64.b64decode(self._read_text().strip()).decode())

    def _txt_to_hex(self):
        data = self._read_text().encode()
        lines = []
        for i in range(0, len(data), 16):
            chunk = data[i:i + 16]
            h = " ".join(f"{b:02x}" for b in chunk)
            a = "".join(chr(b) if 0x20 <= b <= 0x7e else "." for b in chunk)
            lines.append(f"{i:08x}  {h:<48}  {a}")
        self._log("\n".join(lines))

    def _lines_sort(self):
        self._log("\n".join(sorted(self._read_text().strip().split("\n"))))

    def _lines_unique(self):
        seen, r = set(), []
        for l in self._read_text().strip().split("\n"):
            if l not in seen:
                seen.add(l)
                r.append(l)
        self._log("\n".join(r))

    def _lines_reverse(self):
        self._log("\n".join(reversed(self._read_text().strip().split("\n"))))

    def _image_to_base64(self):
        import base64
        with open(self._source_path, "rb") as f:
            data = f.read()
        ext = os.path.splitext(self._source_path)[1].lstrip(".").lower()
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "bmp": "image/bmp", "webp": "image/webp"}.get(ext, "image/png")
        b64 = base64.b64encode(data).decode()
        self._log(f"data:{mime};base64,{b64[:200]}...")
        self._log(f"\nFull base64 length: {len(b64)} chars")

    def _md_to_html(self):
        content = self._read_text()
        lines = content.split("\n")
        html_lines = []
        for line in lines:
            if line.startswith("### "):
                html_lines.append(f"<h3>{line[4:]}</h3>")
            elif line.startswith("## "):
                html_lines.append(f"<h2>{line[3:]}</h2>")
            elif line.startswith("# "):
                html_lines.append(f"<h1>{line[2:]}</h1>")
            elif line.startswith("- "):
                html_lines.append(f"<li>{line[2:]}</li>")
            elif line.startswith("**") and line.endswith("**"):
                html_lines.append(f"<p><strong>{line[2:-2]}</strong></p>")
            elif line.strip() == "":
                html_lines.append("<br>")
            else:
                html_lines.append(f"<p>{line}</p>")
        result = "<html><body>\n" + "\n".join(html_lines) + "\n</body></html>"
        self._log(result)
