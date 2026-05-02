"""External Python Libraries"""
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import socket
import tkinter as tk
from tkinter import messagebox, ttk
import sqlite3
import matplotlib
import pandas as pd
matplotlib.use('TkAgg')

HOST = '127.0.0.1'
PORT = 8000

# ── Colour & font constants ───────────────────────────────────────────────────
BG        = "#f0f4f8"
CARD_BG   = "#ffffff"
PRIMARY   = "#2980b9"
PRIMARY_D = "#2471a3"
SUCCESS   = "#27ae60"
DANGER    = "#e74c3c"
TEXT      = "#2c3e50"
MUTED     = "#7f8c8d"
BORDER    = "#dde1e7"

FONT_H1     = ("Helvetica", 18, "bold")
FONT_H2     = ("Helvetica", 13, "bold")
FONT_LABEL  = ("Helvetica", 11)
FONT_SMALL  = ("Helvetica", 9)
FONT_ENTRY  = ("Helvetica", 11)
FONT_BTN    = ("Helvetica", 10, "bold")


def _btn(widget, color=PRIMARY, fg="white"):
    """Apply a flat, coloured style to a tk.Button."""
    widget.config(
        bg=color, fg=fg, font=FONT_BTN, relief="flat",
        cursor="hand2", padx=14, pady=7,
        activebackground=PRIMARY_D, activeforeground="white",
        bd=0,
    )


def _msgbox(kind, title, msg, **kwargs):
    """Show a tkinter messagebox centered on the screen.

    A withdrawn window loses position context on Windows, so we use a
    fully-transparent (alpha=0) but *visible* 1×1 Toplevel placed at the
    screen centre.  The messagebox then positions itself over that anchor.
    """
    root = tk._default_root
    if root is None:
        return getattr(messagebox, kind)(title, msg, **kwargs)
    sw = root.winfo_screenwidth()
    sh = root.winfo_screenheight()
    tmp = tk.Toplevel(root)
    tmp.geometry(f"1x1+{sw // 2}+{sh // 2}")
    tmp.wm_attributes("-alpha", 0.0)   # invisible but positioned on-screen
    tmp.update_idletasks()
    result = getattr(messagebox, kind)(title, msg, parent=tmp, **kwargs)
    tmp.destroy()
    return result


# ── Helpers ───────────────────────────────────────────────────────────────────

class CenteredTkWindow:
    def center_window(self):
        self.update_idletasks()
        w, h = self.winfo_width(), self.winfo_height()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')


class PlaceholderEntry(tk.Entry):
    """Entry widget that shows grey hint text and correctly handles password masking."""

    def __init__(self, master, placeholder, show_char="", **kwargs):
        kwargs.setdefault("font", FONT_ENTRY)
        kwargs.setdefault("relief", "flat")
        kwargs.setdefault("bd", 0)
        kwargs.setdefault("highlightthickness", 1)
        kwargs.setdefault("highlightbackground", BORDER)
        kwargs.setdefault("highlightcolor", PRIMARY)
        kwargs.setdefault("bg", CARD_BG)
        super().__init__(master, **kwargs)
        self.placeholder = placeholder
        self.show_char = show_char
        self._ph_active = True
        self.config(fg=MUTED)
        self.insert(0, placeholder)
        self.bind("<FocusIn>",  self._clear)
        self.bind("<FocusOut>", self._restore)

    def _clear(self, _event):
        if self._ph_active:
            self.delete(0, tk.END)
            self.config(fg=TEXT, show=self.show_char)
            self._ph_active = False

    def _restore(self, _event):
        if not super().get():
            self.config(show="", fg=MUTED)
            self.insert(0, self.placeholder)
            self._ph_active = True

    def get(self):
        """Return "" when the placeholder is shown, otherwise the real value."""
        return "" if self._ph_active else super().get()


# ── Login window ──────────────────────────────────────────────────────────────

class MainWindow(tk.Tk, CenteredTkWindow):
    def __init__(self):
        super().__init__()
        self.title("Finance Platform — Login")
        self.geometry("420x500")
        self.resizable(False, False)
        self.config(bg=BG)
        self.center_window()
        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def _build_ui(self):
        # ── Header banner
        hdr = tk.Frame(self, bg=PRIMARY, pady=28)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Finance Platform", font=FONT_H1,
                 bg=PRIMARY, fg="white").pack()
        tk.Label(hdr, text="Stocks & Cryptocurrency Trading", font=FONT_SMALL,
                 bg=PRIMARY, fg="#d6eaf8").pack(pady=(4, 0))

        # ── Card
        card = tk.Frame(self, bg=CARD_BG, padx=40, pady=30)
        card.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(card, text="Username", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT, anchor="w").pack(fill="x")
        self.username_entry = PlaceholderEntry(card, "Enter your username")
        self.username_entry.pack(fill="x", ipady=8, pady=(4, 14))

        tk.Label(card, text="Password", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT, anchor="w").pack(fill="x")
        self.password_entry = PlaceholderEntry(card, "Enter your password", show_char="*")
        self.password_entry.pack(fill="x", ipady=8, pady=(4, 22))

        login_btn = tk.Button(card, text="Login", command=self.login)
        _btn(login_btn)
        login_btn.pack(fill="x", pady=(0, 10))

        tk.Frame(card, bg=BORDER, height=1).pack(fill="x", pady=8)

        reg_btn = tk.Button(card, text="Create Account", command=self.register)
        _btn(reg_btn, color="#ecf0f1", fg=TEXT)
        reg_btn.pack(fill="x")

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()
        if not username or not password:
            _msgbox("showwarning", "Missing Fields", "Please enter both username and password.")
            return
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(f'login|{username}|{password}'.encode())
                response = s.recv(1024).decode()
        except ConnectionRefusedError:
            _msgbox("showerror", "Connection Error",
                    "Could not connect to server.\nMake sure server.py is running.")
            return
        if response.startswith("Login successful"):
            client_id = response.split(": ")[-1].strip()
            self.withdraw()
            AccountWindow(self, username, client_id)
        else:
            _msgbox("showerror", "Login Failed", response)

    def register(self):
        RegisterWindow(self)

    def on_closing(self):
        self.quit()


# ── Registration window ───────────────────────────────────────────────────────

class RegisterWindow(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Create Account")
        self.geometry("420x460")
        self.resizable(False, False)
        self.config(bg=BG)
        self.center_window()
        self._build_ui()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=SUCCESS, pady=24)
        hdr.pack(fill="x")
        tk.Label(hdr, text="Create Account", font=FONT_H1,
                 bg=SUCCESS, fg="white").pack()

        card = tk.Frame(self, bg=CARD_BG, padx=40, pady=28)
        card.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(card, text="Username (min 4 characters)", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT, anchor="w").pack(fill="x")
        self.username_entry = PlaceholderEntry(card, "Choose a username")
        self.username_entry.pack(fill="x", ipady=8, pady=(4, 14))

        tk.Label(card, text="Password (min 6 characters)", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT, anchor="w").pack(fill="x")
        self.password_entry = PlaceholderEntry(card, "Choose a password", show_char="*")
        self.password_entry.pack(fill="x", ipady=8, pady=(4, 22))

        reg_btn = tk.Button(card, text="Register", command=self.register_user)
        _btn(reg_btn, color=SUCCESS)
        reg_btn.pack(fill="x")

    def register_user(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            _msgbox("showerror", "Missing Fields", "Please fill in both fields.")
            return
        if len(username) < 4:
            _msgbox("showerror", "Username Too Short",
                    "Username must be at least 4 characters.")
            return
        if len(password) < 6:
            _msgbox("showerror", "Password Too Short",
                    "Password must be at least 6 characters.")
            return

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(f'register|{username}|{password}'.encode())
                response = s.recv(1024).decode()
        except ConnectionRefusedError:
            _msgbox("showerror", "Connection Error", "Could not connect to server.")
            return

        _msgbox("showinfo", "Registration Result", response)
        self.destroy()
        self.master.deiconify()


# ── Account window ────────────────────────────────────────────────────────────

class AccountWindow(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent, username, client_id):
        super().__init__(parent)
        self.client_id = client_id
        self.username = username
        self.portfolio = {"balance": 0.0}
        self.title(f"{username}'s Account")
        self.geometry("520x480")
        self.resizable(False, False)
        self.config(bg=BG)
        self.protocol("WM_DELETE_WINDOW", self.logout)
        self.center_window()
        self._build_ui()
        self.request_update_balance()

    def _build_ui(self):
        # ── Header
        hdr = tk.Frame(self, bg=PRIMARY, pady=20)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"Welcome, {self.username}!", font=FONT_H1,
                 bg=PRIMARY, fg="white").pack()
        tk.Label(hdr, text=f"Client ID: {self.client_id}", font=FONT_SMALL,
                 bg=PRIMARY, fg="#d6eaf8").pack(pady=(4, 0))

        # ── Balance card
        bal_card = tk.Frame(self, bg=CARD_BG, pady=18, padx=30, relief="flat",
                            highlightthickness=1, highlightbackground=BORDER)
        bal_card.pack(fill="x", padx=30, pady=(20, 10))

        tk.Label(bal_card, text="Current Balance", font=FONT_SMALL,
                 bg=CARD_BG, fg=MUTED).pack()
        self.balance_label = tk.Label(bal_card, text="£0.00", font=("Helvetica", 24, "bold"),
                                      bg=CARD_BG, fg=SUCCESS)
        self.balance_label.pack()

        # ── Amount input + buttons
        action_frame = tk.Frame(self, bg=BG)
        action_frame.pack(padx=30, pady=10, fill="x")

        self.amount_entry = PlaceholderEntry(action_frame, "Enter amount (£)")
        self.amount_entry.pack(fill="x", ipady=8, pady=(0, 10))

        btn_row = tk.Frame(action_frame, bg=BG)
        btn_row.pack(fill="x")

        dep_btn = tk.Button(btn_row, text="Deposit", command=self.deposit_money)
        _btn(dep_btn, color=SUCCESS)
        dep_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        wdw_btn = tk.Button(btn_row, text="Withdraw", command=self.withdraw_money)
        _btn(wdw_btn, color=DANGER)
        wdw_btn.pack(side="left", expand=True, fill="x")

        # ── Portfolio button
        port_btn = tk.Button(self, text="Open Portfolio & Markets",
                             command=self.open_portfolio)
        _btn(port_btn)
        port_btn.pack(padx=30, pady=(12, 6), fill="x")

        # ── Logout button
        logout_btn = tk.Button(self, text="Logout", command=self.logout)
        _btn(logout_btn, color="#95a5a6")
        logout_btn.pack(padx=30, pady=(0, 12), fill="x")

    # ── Balance ───────────────────────────────────────────────────────────────

    def request_update_balance(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(f'get_balance|{self.username}'.encode())
                response = s.recv(1024).decode()
            self.portfolio["balance"] = float(response)
            self._refresh_balance_label()
        except (ValueError, ConnectionRefusedError) as e:
            print("Error fetching balance:", e)

    def _refresh_balance_label(self):
        self.balance_label.config(
            text=f"£{self.portfolio['balance']:.2f}")

    # ── Transactions ──────────────────────────────────────────────────────────

    def deposit_money(self):
        amount_str = self.amount_entry.get()
        if not amount_str:
            _msgbox("showwarning", "Input Required", "Please enter an amount.")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError as e:
            _msgbox("showerror", "Invalid Amount", str(e) if "positive" in str(e)
                    else "Please enter a valid number.")
            return

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("UPDATE users SET balance = balance + ? WHERE username = ?",
                  (amount, self.username))
        c.execute("INSERT INTO transactions (username, transaction_type, amount) "
                  "VALUES (?, 'deposit', ?)", (self.username, amount))
        conn.commit()
        conn.close()
        _msgbox("showinfo", "Deposit Successful",
                f"£{amount:.2f} has been added to your account.")
        self.request_update_balance()

    def withdraw_money(self):
        amount_str = self.amount_entry.get()
        if not amount_str:
            _msgbox("showwarning", "Input Required", "Please enter an amount.")
            return
        try:
            amount = float(amount_str)
            if amount <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError as e:
            _msgbox("showerror", "Invalid Amount", str(e) if "positive" in str(e)
                    else "Please enter a valid number.")
            return

        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT balance FROM users WHERE username = ?", (self.username,))
        balance = c.fetchone()[0]
        if balance < amount:
            _msgbox("showerror", "Insufficient Funds",
                    f"You only have £{balance:.2f} available.")
            conn.close()
            return
        c.execute("UPDATE users SET balance = balance - ? WHERE username = ?",
                  (amount, self.username))
        c.execute("INSERT INTO transactions (username, transaction_type, amount) "
                  "VALUES (?, 'withdraw', ?)", (self.username, amount))
        conn.commit()
        conn.close()
        _msgbox("showinfo", "Withdrawal Successful",
                f"£{amount:.2f} has been withdrawn from your account.")
        self.request_update_balance()

    def logout(self):
        # Close any Toplevel children (PortfolioWindow etc.) then return to login
        for w in list(self.master.winfo_children()):
            if isinstance(w, tk.Toplevel):
                w.destroy()
        self.master.deiconify()

    def open_portfolio(self):
        PortfolioWindow(self, self.username, self.client_id,
                        self.portfolio["balance"])


# ── Portfolio window ──────────────────────────────────────────────────────────

class PortfolioWindow(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent, username, client_id, balance):
        super().__init__(parent)
        self.username = username
        self.client_id = client_id
        self.portfolio = {"balance": balance}
        self.investment_option = tk.StringVar(value="Stocks")
        self.title(f"{username}'s Portfolio")
        self.geometry("1300x640")
        self.config(bg=BG)
        self.center_window()
        self.market_files = {
            "Stocks": "stocks.csv",
            "Cryptocurrency": "cryptocurrencies.csv",
        }
        self.create_widgets()
        self.request_update_balance()
        self.update_graph()

    def create_widgets(self):
        # ── Top bar
        top = tk.Frame(self, bg=PRIMARY, pady=14, padx=20)
        top.pack(fill="x")
        tk.Label(top, text=f"{self.username}'s Portfolio", font=FONT_H2,
                 bg=PRIMARY, fg="white").pack(side="left")
        tk.Label(top, text=f"Client ID: {self.client_id}", font=FONT_SMALL,
                 bg=PRIMARY, fg="#d6eaf8").pack(side="right")

        # ── Balance strip
        bal_strip = tk.Frame(self, bg=CARD_BG, pady=10, padx=20,
                             highlightthickness=1, highlightbackground=BORDER)
        bal_strip.pack(fill="x", padx=20, pady=(12, 0))
        tk.Label(bal_strip, text="Available Balance:", font=FONT_LABEL,
                 bg=CARD_BG, fg=MUTED).pack(side="left")
        self.balance_label = tk.Label(bal_strip, text="£0.00",
                                      font=("Helvetica", 14, "bold"),
                                      bg=CARD_BG, fg=SUCCESS)
        self.balance_label.pack(side="left", padx=(8, 0))

        # ── Main split: treeview left, chart right
        main = tk.Frame(self, bg=BG)
        main.pack(fill="both", expand=True, padx=20, pady=12)

        left = tk.Frame(main, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # Market selector
        sel_row = tk.Frame(left, bg=BG)
        sel_row.pack(fill="x", pady=(0, 6))
        tk.Label(sel_row, text="Market:", font=FONT_LABEL,
                 bg=BG, fg=TEXT).pack(side="left")
        menu = ttk.Combobox(sel_row, textvariable=self.investment_option,
                            values=list(self.market_files.keys()),
                            state="readonly", width=18, font=FONT_LABEL)
        menu.pack(side="left", padx=8)
        menu.bind("<<ComboboxSelected>>", self.update_graph)

        # Treeview
        style = ttk.Style()
        style.configure("Portfolio.Treeview.Heading", font=FONT_BTN)
        style.configure("Portfolio.Treeview", font=FONT_LABEL, rowheight=26)

        self.tree = ttk.Treeview(left, columns=("Market", "Quantity", "Price"),
                                 show="headings", style="Portfolio.Treeview")
        for col, w in [("Market", 200), ("Quantity", 90), ("Price", 110)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=w)
        self.tree.pack(fill="both", expand=True)

        # Buttons below tree
        btn_row = tk.Frame(left, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))

        invest_btn = tk.Button(btn_row, text="Invest in Selected",
                               command=self.open_investment_window_with_selection)
        _btn(invest_btn, color=SUCCESS)
        invest_btn.pack(side="left", padx=(0, 8))

        my_inv_btn = tk.Button(btn_row, text="My Investments",
                               command=self.open_my_investment_window)
        _btn(my_inv_btn, color=PRIMARY)
        my_inv_btn.pack(side="left")

        # Chart (right side)
        right = tk.Frame(main, bg=CARD_BG, relief="flat",
                         highlightthickness=1, highlightbackground=BORDER)
        right.pack(side="right", fill="both", expand=True)

        self.fig, self.ax = plt.subplots(figsize=(6, 4))
        self.fig.patch.set_facecolor(CARD_BG)
        self.canvas = FigureCanvasTkAgg(self.fig, master=right)
        self.canvas.get_tk_widget().pack(fill="both", expand=True)

    def request_update_balance(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((HOST, PORT))
                s.sendall(f'get_balance|{self.username}'.encode())
                response = s.recv(1024).decode()
            self.portfolio["balance"] = float(response)
            self.balance_label.config(text=f"£{self.portfolio['balance']:.2f}")
        except (ValueError, ConnectionRefusedError) as e:
            print("Error fetching balance:", e)

    def update_graph(self, *_args):
        selected = self.investment_option.get()
        if selected == "Stocks":
            self._plot_stocks()
        elif selected == "Cryptocurrency":
            self._plot_crypto()

    def _plot_stocks(self):
        try:
            df = pd.read_csv("stocks.csv")
            if df.empty:
                return
            self.ax.clear()
            self.ax.bar(df["Name"], df["Last Price"], color=PRIMARY)
            self.ax.set_title("Top Stocks — Last Price", fontsize=11, pad=10)
            self.ax.set_xlabel("Stock")
            self.ax.set_ylabel("Price (£)")
            self.ax.tick_params(axis="x", rotation=45)
            self.fig.tight_layout()
            self.canvas.draw()
            self._populate_tree(df, "Stocks")
        except Exception as e:
            print(f"Error plotting stocks: {e}")

    def _plot_crypto(self):
        try:
            df = pd.read_csv("cryptocurrencies.csv")
            if df.empty:
                return
            df["Price"] = df["Price"].replace(r"[\$,]", "", regex=True).astype(float)
            self.ax.clear()
            self.ax.bar(df["Name"], df["Price"], color="#f39c12")
            self.ax.set_title("Top Cryptocurrencies — Price (USD)", fontsize=11, pad=10)
            self.ax.set_xlabel("Crypto")
            self.ax.set_ylabel("Price ($)")
            self.ax.tick_params(axis="x", rotation=45)
            self.fig.tight_layout()
            self.canvas.draw()
            self._populate_tree(df, "Cryptocurrency")
        except Exception as e:
            print(f"Error plotting crypto: {e}")

    def _populate_tree(self, df, market_type):
        for row in self.tree.get_children():
            self.tree.delete(row)
        price_col = "Last Price" if market_type == "Stocks" else "Price"
        symbol = "£" if market_type == "Stocks" else "$"
        for _, row in df.iterrows():
            self.tree.insert("", "end", values=(
                row["Name"], "1", f"{symbol}{float(row[price_col]):.2f}"
            ))

    def open_investment_window_with_selection(self):
        selected = self.tree.selection()
        if not selected:
            _msgbox("showwarning", "No Selection",
                    "Please select a stock or cryptocurrency from the list.")
            return
        values = self.tree.item(selected[0], "values")
        market_name = values[0]
        item_price = float(values[2].lstrip("£$"))
        Investment(self, self.username, market_name, item_price)

    def open_my_investment_window(self):
        MyInvestmentWindow(self, self.username)


# ── Investment (buy/sell) window ──────────────────────────────────────────────

class Investment(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent, username, selected_market, item_price):
        super().__init__(parent)
        self.username = username
        self.selected_market = selected_market
        self.item_price = item_price
        self.trade_option = tk.StringVar(value="Buy")
        self.quantity_var = tk.IntVar(value=1)
        self.investment_amount_var = tk.StringVar()
        self.title(f"Trade — {selected_market}")
        self.geometry("380x400")
        self.resizable(False, False)
        self.config(bg=BG)
        self.center_window()
        self._build_ui()
        self._refresh_amount()
        self.quantity_var.trace_add("write", lambda *_: self._refresh_amount())

    def _build_ui(self):
        hdr = tk.Frame(self, bg=PRIMARY, pady=18)
        hdr.pack(fill="x")
        tk.Label(hdr, text=f"{self.selected_market}", font=FONT_H2,
                 bg=PRIMARY, fg="white").pack()
        tk.Label(hdr, text=f"Price per unit: £{self.item_price:.2f}", font=FONT_SMALL,
                 bg=PRIMARY, fg="#d6eaf8").pack(pady=(4, 0))

        card = tk.Frame(self, bg=CARD_BG, padx=30, pady=20)
        card.pack(fill="both", expand=True, padx=20, pady=14)

        # Trade type
        tk.Label(card, text="Trade Type:", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w")
        rb_row = tk.Frame(card, bg=CARD_BG)
        rb_row.pack(anchor="w", pady=(4, 14))
        for label, val in [("Buy", "Buy"), ("Sell", "Sell")]:
            tk.Radiobutton(rb_row, text=label, variable=self.trade_option, value=val,
                           bg=CARD_BG, font=FONT_LABEL, fg=TEXT,
                           activebackground=CARD_BG).pack(side="left", padx=(0, 16))

        # Quantity
        tk.Label(card, text="Quantity:", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w")
        tk.Spinbox(card, from_=1, to=10000, width=8, textvariable=self.quantity_var,
                   font=FONT_ENTRY, relief="flat", bd=0,
                   highlightthickness=1, highlightbackground=BORDER,
                   command=self._refresh_amount).pack(anchor="w", ipady=5, pady=(4, 14))

        # Total
        tk.Label(card, text="Total Amount:", font=FONT_LABEL,
                 bg=CARD_BG, fg=TEXT).pack(anchor="w")
        tk.Entry(card, textvariable=self.investment_amount_var,
                 state="readonly", font=FONT_ENTRY, relief="flat", bd=0,
                 highlightthickness=1, highlightbackground=BORDER,
                 readonlybackground=CARD_BG, fg=SUCCESS).pack(
                     fill="x", ipady=5, pady=(4, 18))

        btn_row = tk.Frame(card, bg=CARD_BG)
        btn_row.pack(fill="x")
        confirm_btn = tk.Button(btn_row, text="Confirm", command=self.confirm_investment)
        _btn(confirm_btn, color=SUCCESS)
        confirm_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))
        cancel_btn = tk.Button(btn_row, text="Cancel", command=self.destroy)
        _btn(cancel_btn, color="#95a5a6")
        cancel_btn.pack(side="left", expand=True, fill="x")

    def _refresh_amount(self):
        try:
            total = self.item_price * self.quantity_var.get()
            self.investment_amount_var.set(f"£{total:.2f}")
        except tk.TclError:
            pass

    def confirm_investment(self):
        transaction_type = self.trade_option.get()
        quantity = self.quantity_var.get()
        total_amount = self.item_price * quantity

        conn = sqlite3.connect('users.db')
        c = conn.cursor()

        if transaction_type == "Buy":
            c.execute("SELECT balance FROM users WHERE username=?", (self.username,))
            balance = c.fetchone()[0]
            if balance < total_amount:
                _msgbox("showerror", "Insufficient Funds",
                        f"You need £{total_amount:.2f} but only have £{balance:.2f}.")
                conn.close()
                return
            c.execute("UPDATE users SET balance = balance - ? WHERE username=?",
                      (total_amount, self.username))
            c.execute("INSERT INTO transactions (username, transaction_type, amount, market) "
                      "VALUES (?, 'buy', ?, ?)", (self.username, total_amount, self.selected_market))
            c.execute("SELECT quantity FROM portfolios WHERE username=? AND market=?",
                      (self.username, self.selected_market))
            row = c.fetchone()
            if row:
                c.execute("UPDATE portfolios SET quantity=? WHERE username=? AND market=?",
                          (row[0] + quantity, self.username, self.selected_market))
            else:
                c.execute("INSERT INTO portfolios (username, market, quantity, amount) "
                          "VALUES (?, ?, ?, ?)",
                          (self.username, self.selected_market, quantity, total_amount))

        elif transaction_type == "Sell":
            c.execute("SELECT quantity FROM portfolios WHERE username=? AND market=?",
                      (self.username, self.selected_market))
            row = c.fetchone()
            if not row or row[0] < quantity:
                owned = row[0] if row else 0
                _msgbox("showerror", "Cannot Sell",
                        f"You own {owned} unit(s) of {self.selected_market}, "
                        f"but tried to sell {quantity}.")
                conn.close()
                return
            c.execute("UPDATE users SET balance = balance + ? WHERE username=?",
                      (total_amount, self.username))
            c.execute("INSERT INTO transactions (username, transaction_type, amount, market) "
                      "VALUES (?, 'sell', ?, ?)", (self.username, total_amount, self.selected_market))
            new_qty = row[0] - quantity
            if new_qty > 0:
                c.execute("UPDATE portfolios SET quantity=? WHERE username=? AND market=?",
                          (new_qty, self.username, self.selected_market))
            else:
                c.execute("DELETE FROM portfolios WHERE username=? AND market=?",
                          (self.username, self.selected_market))
        else:
            conn.close()
            return

        conn.commit()
        conn.close()
        _msgbox("showinfo", "Transaction Complete",
                f"{transaction_type} of {quantity} × {self.selected_market} "
                f"(£{total_amount:.2f}) processed successfully.")
        self.master.request_update_balance()
        self.destroy()


# ── My Investments window ─────────────────────────────────────────────────────

class MyInvestmentWindow(tk.Toplevel, CenteredTkWindow):
    def __init__(self, parent, username):
        super().__init__(parent)
        self.username = username
        self.title(f"{username}'s Investments")
        self.geometry("560x380")
        self.config(bg=BG)
        self.center_window()
        self._build_ui()
        self._load_investments()

    def _build_ui(self):
        hdr = tk.Frame(self, bg=PRIMARY, pady=16)
        hdr.pack(fill="x")
        tk.Label(hdr, text="My Investments", font=FONT_H2,
                 bg=PRIMARY, fg="white").pack()

        frame = tk.Frame(self, bg=BG, padx=16, pady=12)
        frame.pack(fill="both", expand=True)

        style = ttk.Style()
        style.configure("Inv.Treeview.Heading", font=FONT_BTN)
        style.configure("Inv.Treeview", font=FONT_LABEL, rowheight=26)

        self.tree = ttk.Treeview(frame, columns=("Market", "Quantity", "Paid"),
                                 show="headings", style="Inv.Treeview")
        for col, w in [("Market", 220), ("Quantity", 100), ("Paid", 120)]:
            self.tree.heading(col, text=col)
            self.tree.column(col, anchor="center", width=w)
        self.tree.pack(fill="both", expand=True)

    def _load_investments(self):
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT market, quantity, amount FROM portfolios WHERE username=?",
                  (self.username,))
        rows = c.fetchall()
        conn.close()
        for market, qty, amount in rows:
            self.tree.insert("", "end", values=(market, qty, f"£{float(amount):.2f}"))
        if not rows:
            self.tree.insert("", "end", values=("No investments yet", "", ""))


if __name__ == "__main__":
    app = MainWindow()
    app.mainloop()
