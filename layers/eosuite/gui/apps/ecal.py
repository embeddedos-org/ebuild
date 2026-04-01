# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import tkinter as tk
from tkinter import ttk
import math


class ECal(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.pack(fill="both", expand=True)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=5, pady=5)

        self.basic_tab = ttk.Frame(self.notebook)
        self.scientific_tab = ttk.Frame(self.notebook)
        self.tax_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.basic_tab, text="  Basic  ")
        self.notebook.add(self.scientific_tab, text="  Scientific  ")
        self.notebook.add(self.tax_tab, text="  Tax Calculator  ")

        self._build_basic_calculator()
        self._build_scientific_calculator()
        self._build_tax_calculator()

    def on_close(self):
        pass

    # ─── SAFE EVAL ───────────────────────────────────────────────────────

    def _safe_eval(self, expr):
        allowed_names = {
            "sin": math.sin, "cos": math.cos, "tan": math.tan,
            "asin": math.asin, "acos": math.acos, "atan": math.atan,
            "log": math.log10, "ln": math.log, "sqrt": math.sqrt,
            "abs": abs, "pi": math.pi, "e": math.e,
            "factorial": math.factorial, "pow": pow,
            "radians": math.radians, "degrees": math.degrees,
        }
        allowed_chars = set("0123456789+-*/.()% ")
        cleaned = expr
        for name in allowed_names:
            cleaned = cleaned.replace(name, "")
        for ch in cleaned:
            if ch not in allowed_chars:
                raise ValueError(f"Invalid character: {ch}")
        return eval(expr, {"__builtins__": {}}, allowed_names)

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB 1: BASIC CALCULATOR
    # ═══════════════════════════════════════════════════════════════════════

    def _build_basic_calculator(self):
        tab = self.basic_tab

        self.basic_expression = tk.StringVar(value="")
        self.basic_result = tk.StringVar(value="0")

        display_frame = ttk.Frame(tab)
        display_frame.pack(fill="x", padx=10, pady=(10, 5))

        expr_label = ttk.Label(display_frame, textvariable=self.basic_expression,
                               anchor="e", font=("Segoe UI", 12))
        expr_label.pack(fill="x")

        result_label = ttk.Label(display_frame, textvariable=self.basic_result,
                                 anchor="e", font=("Segoe UI", 24, "bold"))
        result_label.pack(fill="x")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        buttons = [
            ["%", "CE", "C", "⌫"],
            ["1/x", "x²", "√", "/"],
            ["7", "8", "9", "*"],
            ["4", "5", "6", "-"],
            ["1", "2", "3", "+"],
            ["+/-", "0", ".", "="],
        ]

        for r, row in enumerate(buttons):
            btn_frame.rowconfigure(r, weight=1)
            for c, text in enumerate(row):
                btn_frame.columnconfigure(c, weight=1)
                cmd = lambda t=text: self._basic_press(t)
                style = "Accent.TButton" if text == "=" else "TButton"
                btn = ttk.Button(btn_frame, text=text, command=cmd, style=style)
                btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

        tab.bind_all("<Key>", self._basic_key_handler)

    def _basic_press(self, key):
        expr = self.basic_expression.get()
        result = self.basic_result.get()

        if key == "C":
            self.basic_expression.set("")
            self.basic_result.set("0")
        elif key == "CE":
            self.basic_result.set("0")
            self.basic_expression.set("")
        elif key == "⌫":
            if expr:
                self.basic_expression.set(expr[:-1])
        elif key == "=":
            try:
                sanitized = expr.replace("×", "*").replace("÷", "/")
                val = self._safe_eval(sanitized)
                if isinstance(val, float) and val == int(val):
                    val = int(val)
                self.basic_result.set(str(val))
                self.basic_expression.set("")
            except Exception:
                self.basic_result.set("Error")
                self.basic_expression.set("")
        elif key == "+/-":
            if expr and expr[0] == "-":
                self.basic_expression.set(expr[1:])
            elif expr:
                self.basic_expression.set("-" + expr)
        elif key == "%":
            try:
                val = self._safe_eval(expr) / 100
                self.basic_expression.set(str(val))
            except Exception:
                pass
        elif key == "x²":
            try:
                val = self._safe_eval(expr) ** 2
                self.basic_result.set(str(val))
                self.basic_expression.set("")
            except Exception:
                pass
        elif key == "√":
            try:
                val = math.sqrt(self._safe_eval(expr))
                self.basic_result.set(str(val))
                self.basic_expression.set("")
            except Exception:
                pass
        elif key == "1/x":
            try:
                val = 1 / self._safe_eval(expr)
                self.basic_result.set(str(val))
                self.basic_expression.set("")
            except Exception:
                pass
        else:
            self.basic_expression.set(expr + key)

    def _basic_key_handler(self, event):
        if self.notebook.index(self.notebook.select()) != 0:
            return
        key = event.char
        if key in "0123456789+-*/.":
            self._basic_press(key)
        elif event.keysym == "Return":
            self._basic_press("=")
        elif event.keysym == "BackSpace":
            self._basic_press("⌫")
        elif event.keysym == "Escape":
            self._basic_press("C")

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB 2: SCIENTIFIC CALCULATOR
    # ═══════════════════════════════════════════════════════════════════════

    def _build_scientific_calculator(self):
        tab = self.scientific_tab

        self.sci_expression = tk.StringVar(value="")
        self.sci_result = tk.StringVar(value="0")
        self.sci_angle_mode = tk.StringVar(value="Radians")
        self.sci_memory = 0.0

        display_frame = ttk.Frame(tab)
        display_frame.pack(fill="x", padx=10, pady=(10, 5))

        top_bar = ttk.Frame(display_frame)
        top_bar.pack(fill="x")

        ttk.Radiobutton(top_bar, text="Rad", variable=self.sci_angle_mode,
                        value="Radians").pack(side="left")
        ttk.Radiobutton(top_bar, text="Deg", variable=self.sci_angle_mode,
                        value="Degrees").pack(side="left", padx=(5, 0))

        self.sci_mem_label = ttk.Label(top_bar, text="", font=("Segoe UI", 9))
        self.sci_mem_label.pack(side="right")

        expr_label = ttk.Label(display_frame, textvariable=self.sci_expression,
                               anchor="e", font=("Segoe UI", 11))
        expr_label.pack(fill="x")

        result_label = ttk.Label(display_frame, textvariable=self.sci_result,
                                 anchor="e", font=("Segoe UI", 22, "bold"))
        result_label.pack(fill="x")

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        buttons = [
            ["MC", "MR", "M+", "M-", "⌫", "C"],
            ["sin", "cos", "tan", "log", "ln", "CE"],
            ["x²", "x³", "xʸ", "√", "π", "e"],
            ["(", ")", "!", "abs", "1/x", "mod"],
            ["7", "8", "9", "/", "%", ""],
            ["4", "5", "6", "*", "", ""],
            ["1", "2", "3", "-", "", ""],
            ["+/-", "0", ".", "+", "", "="],
        ]

        for r, row in enumerate(buttons):
            btn_frame.rowconfigure(r, weight=1)
            for c, text in enumerate(row):
                btn_frame.columnconfigure(c, weight=1)
                if not text:
                    continue
                cmd = lambda t=text: self._sci_press(t)
                style = "Accent.TButton" if text == "=" else "TButton"
                btn = ttk.Button(btn_frame, text=text, command=cmd, style=style)
                if text == "=" :
                    btn.grid(row=r, column=c, rowspan=1, sticky="nsew", padx=2, pady=2)
                else:
                    btn.grid(row=r, column=c, sticky="nsew", padx=2, pady=2)

    def _sci_press(self, key):
        expr = self.sci_expression.get()
        deg = self.sci_angle_mode.get() == "Degrees"

        if key == "C":
            self.sci_expression.set("")
            self.sci_result.set("0")
            return
        if key == "CE":
            self.sci_expression.set("")
            return
        if key == "⌫":
            self.sci_expression.set(expr[:-1])
            return

        if key == "MC":
            self.sci_memory = 0.0
            self.sci_mem_label.config(text="")
            return
        if key == "MR":
            self.sci_expression.set(expr + str(self.sci_memory))
            return
        if key == "M+":
            try:
                self.sci_memory += float(self.sci_result.get())
                self.sci_mem_label.config(text="M")
            except Exception:
                pass
            return
        if key == "M-":
            try:
                self.sci_memory -= float(self.sci_result.get())
                self.sci_mem_label.config(text="M")
            except Exception:
                pass
            return

        if key == "=":
            try:
                sanitized = expr
                sanitized = sanitized.replace("mod", "%")
                val = self._safe_eval(sanitized)
                if isinstance(val, float) and val == int(val) and abs(val) < 1e15:
                    val = int(val)
                self.sci_result.set(str(val))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
                self.sci_expression.set("")
            return

        if key == "+/-":
            if expr and expr[0] == "-":
                self.sci_expression.set(expr[1:])
            elif expr:
                self.sci_expression.set("-" + expr)
            return

        if key == "%":
            try:
                val = self._safe_eval(expr) / 100
                self.sci_expression.set(str(val))
            except Exception:
                pass
            return

        trig_funcs = {"sin": math.sin, "cos": math.cos, "tan": math.tan}
        if key in trig_funcs:
            try:
                val = self._safe_eval(expr) if expr else 0
                if deg:
                    val = math.radians(val)
                result = trig_funcs[key](val)
                if abs(result) < 1e-15:
                    result = 0.0
                self.sci_result.set(str(result))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
                self.sci_expression.set("")
            return

        if key == "log":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(math.log10(val)))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
                self.sci_expression.set("")
            return

        if key == "ln":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(math.log(val)))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
                self.sci_expression.set("")
            return

        if key == "x²":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(val ** 2))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "x³":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(val ** 3))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "xʸ":
            self.sci_expression.set(expr + "**")
            return

        if key == "√":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(math.sqrt(val)))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "π":
            self.sci_expression.set(expr + str(math.pi))
            return

        if key == "e":
            if expr and (expr[-1].isdigit() or expr[-1] == "."):
                self.sci_expression.set(expr + "*" + str(math.e))
            else:
                self.sci_expression.set(expr + str(math.e))
            return

        if key == "!":
            try:
                val = int(self._safe_eval(expr))
                self.sci_result.set(str(math.factorial(val)))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "abs":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(abs(val)))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "1/x":
            try:
                val = self._safe_eval(expr)
                self.sci_result.set(str(1 / val))
                self.sci_expression.set("")
            except Exception:
                self.sci_result.set("Error")
            return

        if key == "mod":
            self.sci_expression.set(expr + "%")
            return

        self.sci_expression.set(expr + key)

    # ═══════════════════════════════════════════════════════════════════════
    #  TAB 3: TAX CALCULATOR
    # ═══════════════════════════════════════════════════════════════════════

    TAX_BRACKETS = {
        "US": {
            "currency": "$",
            "Single": {
                "standard_deduction": 14600,
                "brackets": [
                    (11600, 0.10),
                    (47150, 0.12),
                    (100525, 0.22),
                    (191950, 0.24),
                    (243725, 0.32),
                    (609350, 0.35),
                    (float("inf"), 0.37),
                ],
            },
            "Married Filing Jointly": {
                "standard_deduction": 29200,
                "brackets": [
                    (23200, 0.10),
                    (94300, 0.12),
                    (201050, 0.22),
                    (383900, 0.24),
                    (487450, 0.32),
                    (731200, 0.35),
                    (float("inf"), 0.37),
                ],
            },
            "Head of Household": {
                "standard_deduction": 21900,
                "brackets": [
                    (16550, 0.10),
                    (63100, 0.12),
                    (100500, 0.22),
                    (191950, 0.24),
                    (243700, 0.32),
                    (609350, 0.35),
                    (float("inf"), 0.37),
                ],
            },
        },
        "UK": {
            "currency": "£",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (12570, 0.00),
                    (50270, 0.20),
                    (125140, 0.40),
                    (float("inf"), 0.45),
                ],
            },
        },
        "Germany": {
            "currency": "€",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (11604, 0.00),
                    (17005, 0.14),
                    (66760, 0.24),
                    (277825, 0.42),
                    (float("inf"), 0.45),
                ],
            },
        },
        "India": {
            "currency": "₹",
            "Single": {
                "standard_deduction": 50000,
                "brackets": [
                    (300000, 0.00),
                    (700000, 0.05),
                    (1000000, 0.10),
                    (1200000, 0.15),
                    (1500000, 0.20),
                    (float("inf"), 0.30),
                ],
            },
        },
        "Canada": {
            "currency": "C$",
            "Single": {
                "standard_deduction": 15705,
                "brackets": [
                    (55867, 0.15),
                    (111733, 0.205),
                    (154906, 0.26),
                    (220000, 0.29),
                    (float("inf"), 0.33),
                ],
            },
        },
        "Australia": {
            "currency": "A$",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (18200, 0.00),
                    (45000, 0.19),
                    (120000, 0.325),
                    (180000, 0.37),
                    (float("inf"), 0.45),
                ],
            },
        },
        "Japan": {
            "currency": "¥",
            "Single": {
                "standard_deduction": 480000,
                "brackets": [
                    (1950000, 0.05),
                    (3300000, 0.10),
                    (6950000, 0.20),
                    (9000000, 0.23),
                    (18000000, 0.33),
                    (40000000, 0.40),
                    (float("inf"), 0.45),
                ],
            },
        },
        "France": {
            "currency": "€",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (11294, 0.00),
                    (28797, 0.11),
                    (82341, 0.30),
                    (177106, 0.41),
                    (float("inf"), 0.45),
                ],
            },
        },
        "Brazil": {
            "currency": "R$",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (24511.92, 0.00),
                    (33919.80, 0.075),
                    (45012.60, 0.15),
                    (55976.16, 0.225),
                    (float("inf"), 0.275),
                ],
            },
        },
        "Singapore": {
            "currency": "S$",
            "Single": {
                "standard_deduction": 0,
                "brackets": [
                    (20000, 0.00),
                    (30000, 0.02),
                    (40000, 0.035),
                    (80000, 0.07),
                    (120000, 0.115),
                    (160000, 0.15),
                    (200000, 0.18),
                    (240000, 0.19),
                    (280000, 0.195),
                    (320000, 0.20),
                    (500000, 0.22),
                    (1000000, 0.23),
                    (float("inf"), 0.24),
                ],
            },
        },
    }

    def _build_tax_calculator(self):
        tab = self.tax_tab

        input_frame = ttk.LabelFrame(tab, text="Income Details", padding=10)
        input_frame.pack(fill="x", padx=10, pady=(10, 5))

        ttk.Label(input_frame, text="Annual Gross Income:").grid(
            row=0, column=0, sticky="w", pady=3)
        self.tax_income_var = tk.StringVar(value="")
        income_entry = ttk.Entry(input_frame, textvariable=self.tax_income_var,
                                 width=25, font=("Segoe UI", 11))
        income_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=3)

        ttk.Label(input_frame, text="Country:").grid(
            row=1, column=0, sticky="w", pady=3)
        self.tax_country_var = tk.StringVar(value="US")
        countries = list(self.TAX_BRACKETS.keys())
        country_combo = ttk.Combobox(input_frame, textvariable=self.tax_country_var,
                                     values=countries, state="readonly", width=22)
        country_combo.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=3)
        country_combo.bind("<<ComboboxSelected>>", self._on_country_change)

        ttk.Label(input_frame, text="Filing Status:").grid(
            row=2, column=0, sticky="w", pady=3)
        self.tax_status_var = tk.StringVar(value="Single")
        self.status_combo = ttk.Combobox(
            input_frame, textvariable=self.tax_status_var,
            values=["Single", "Married Filing Jointly", "Head of Household"],
            state="readonly", width=22)
        self.status_combo.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=3)

        self.tax_deduction_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(input_frame, text="Apply Standard Deduction",
                        variable=self.tax_deduction_var).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=3)

        input_frame.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill="x", padx=10, pady=5)
        ttk.Button(btn_frame, text="Calculate Tax", style="Accent.TButton",
                   command=self._calculate_tax).pack(side="left")
        ttk.Button(btn_frame, text="Clear",
                   command=self._clear_tax).pack(side="left", padx=(10, 0))

        result_frame = ttk.LabelFrame(tab, text="Tax Breakdown", padding=10)
        result_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self.tax_result_text = tk.Text(result_frame, wrap="word",
                                       font=("Consolas", 10),
                                       state="disabled", relief="flat",
                                       bg="#f5f5f5")
        scrollbar = ttk.Scrollbar(result_frame, orient="vertical",
                                  command=self.tax_result_text.yview)
        self.tax_result_text.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tax_result_text.pack(fill="both", expand=True)

    def _on_country_change(self, event=None):
        country = self.tax_country_var.get()
        data = self.TAX_BRACKETS.get(country, {})
        statuses = [k for k in data.keys() if k != "currency"]
        if statuses:
            self.status_combo.config(values=statuses)
            if self.tax_status_var.get() not in statuses:
                self.tax_status_var.set(statuses[0])
        else:
            self.status_combo.config(values=["Single"])
            self.tax_status_var.set("Single")

    def _clear_tax(self):
        self.tax_income_var.set("")
        self.tax_result_text.config(state="normal")
        self.tax_result_text.delete("1.0", "end")
        self.tax_result_text.config(state="disabled")

    def _calculate_tax(self):
        self.tax_result_text.config(state="normal")
        self.tax_result_text.delete("1.0", "end")

        try:
            raw = self.tax_income_var.get().replace(",", "").replace(" ", "")
            gross_income = float(raw)
        except ValueError:
            self.tax_result_text.insert("end", "⚠ Please enter a valid income amount.")
            self.tax_result_text.config(state="disabled")
            return

        country = self.tax_country_var.get()
        status = self.tax_status_var.get()
        apply_deduction = self.tax_deduction_var.get()

        country_data = self.TAX_BRACKETS.get(country, {})
        currency = country_data.get("currency", "$")
        status_data = country_data.get(status)
        if not status_data:
            status_data = country_data.get("Single")
        if not status_data:
            self.tax_result_text.insert("end", "⚠ No tax data for this selection.")
            self.tax_result_text.config(state="disabled")
            return

        brackets = status_data["brackets"]
        std_deduction = status_data["standard_deduction"] if apply_deduction else 0
        taxable_income = max(0, gross_income - std_deduction)

        total_tax = 0.0
        bracket_details = []
        prev_limit = 0

        for limit, rate in brackets:
            if taxable_income <= prev_limit:
                break
            taxed_amount = min(taxable_income, limit) - prev_limit
            tax_for_bracket = taxed_amount * rate
            total_tax += tax_for_bracket
            bracket_details.append({
                "lower": prev_limit,
                "upper": min(limit, taxable_income),
                "rate": rate,
                "taxed_amount": taxed_amount,
                "tax": tax_for_bracket,
            })
            prev_limit = limit

        effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else 0
        net_income = gross_income - total_tax

        def fmt(val):
            return f"{currency}{val:,.2f}"

        lines = []
        lines.append(f"{'═' * 50}")
        lines.append(f"  TAX CALCULATION — {country} ({status})")
        lines.append(f"{'═' * 50}")
        lines.append("")
        lines.append(f"  Gross Income:          {fmt(gross_income)}")
        if apply_deduction and std_deduction > 0:
            lines.append(f"  Standard Deduction:   -{fmt(std_deduction)}")
        lines.append(f"  Taxable Income:        {fmt(taxable_income)}")
        lines.append("")
        lines.append(f"{'─' * 50}")
        lines.append("  TAX BREAKDOWN BY BRACKET")
        lines.append(f"{'─' * 50}")

        for bd in bracket_details:
            upper_str = fmt(bd["upper"]) if bd["upper"] < float("inf") else "∞"
            lines.append(
                f"  {fmt(bd['lower']):>16s} – {upper_str:<16s}  "
                f"@ {bd['rate']*100:5.1f}%  = {fmt(bd['tax'])}"
            )

        lines.append(f"{'─' * 50}")
        lines.append(f"  Total Tax:             {fmt(total_tax)}")
        lines.append(f"  Effective Tax Rate:    {effective_rate:.2f}%")
        lines.append(f"  Net Income (after tax):{fmt(net_income)}")
        lines.append(f"{'═' * 50}")

        self.tax_result_text.insert("end", "\n".join(lines))
        self.tax_result_text.config(state="disabled")
