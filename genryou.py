import csv
import datetime
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import webbrowser

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FILE_NAME = os.path.join(BASE_DIR, "inventory_tabs.csv")

# デザインカラー（モダンテーマ）
BG_COLOR = "#F4F6F9"
PRIMARY_COLOR = "#2C3E50"
ACCENT_BLUE = "#2980B9"
ACCENT_GREEN = "#27AE60"
ACCENT_ORANGE = "#E67E22"
ACCENT_PURPLE = "#8E44AD"
ACCENT_RED = "#C0392B"
TEXT_COLOR = "#333333"


class UltimateInventoryAppV3:

    def __init__(self, root):
        self.root = root
        self.root.title("ULTIMATE版 在庫管理システム (ソート・右クリック・拡張項目対応)")
        self.root.geometry("1000x720")
        self.root.configure(bg=BG_COLOR)

        self.trees = {}

        self.init_csv()
        self.setup_styles()
        self.create_context_menu()
        self.create_widgets()
        self.load_data()

    def init_csv(self):
        """初期CSVの作成（存在しない場合）※新フォーマット"""
        if not os.path.exists(FILE_NAME):
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
            with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(
                    ["タブ名", "品名", "在庫数", "単位", "更新日時", "保管場所", "備考"]
                )
                writer.writerow(
                    ["事務用品", "A4コピー用紙", 12, "箱", now, "キャビネットA", "来月発注予定"]
                )
                writer.writerow(
                    ["事務用品", "黒ボールペン 0.5mm", 2, "本", now, "引き出し1", ""]
                )
                writer.writerow(
                    ["PC・機材", "HDMIケーブル", 3, "本", now, "機材庫", "2mタイプ"]
                )
                writer.writerow(["その他", "", "", "", "", "", ""])

    def setup_styles(self):
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self.style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=TEXT_COLOR,
            rowheight=32,
            font=("MeiryoUI", 10),
            fieldbackground="#FFFFFF",
        )
        self.style.configure(
            "Treeview.Heading",
            background=PRIMARY_COLOR,
            foreground="white",
            font=("MeiryoUI", 10, "bold"),
            padding=6,
        )
        self.style.map("Treeview", background=[("selected", "#3498DB")])
        self.style.configure("TNotebook", background=BG_COLOR)
        self.style.configure(
            "TNotebook.Tab",
            font=("MeiryoUI", 10, "bold"),
            padding=[15, 6],
            background="#D5D8DC",
            foreground=TEXT_COLOR,
        )
        self.style.map(
            "TNotebook.Tab",
            background=[("selected", PRIMARY_COLOR)],
            foreground=[("selected", "white")],
        )

    def create_context_menu(self):
        """右クリックメニューの構築"""
        self.context_menu = tk.Menu(self.root, tearoff=0, font=("MeiryoUI", 9))
        self.context_menu.add_command(
            label="＋ 行の挿入 (新規追加)", command=self.add_item_dialog
        )
        self.context_menu.add_command(
            label="🗑️ 選択行の削除", command=self.delete_item
        )
        self.context_menu.add_separator()
        self.context_menu.add_command(
            label="📊 エクセル向け出力", command=self.export_excel
        )
        self.context_menu.add_command(
            label="📄 PDF向け出力", command=self.export_pdf
        )

    def create_widgets(self):
        # --- 1. ヘッダーエリア ---
        header_frame = tk.Frame(self.root, bg=PRIMARY_COLOR, height=60)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)

        title_label = tk.Label(
            header_frame,
            text="📑 在庫管理システム (高度拡張版)",
            font=("MeiryoUI", 14, "bold"),
            bg=PRIMARY_COLOR,
            fg="white",
        )
        title_label.pack(side="left", padx=20, pady=12)

        header_btn_frame = tk.Frame(header_frame, bg=PRIMARY_COLOR)
        header_btn_frame.pack(side="right", padx=15)

        tk.Button(
            header_btn_frame,
            text="＋ タブ追加",
            font=("MeiryoUI", 9, "bold"),
            bg="#27AE60",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.add_tab,
        ).pack(side="left", padx=3)

        tk.Button(
            header_btn_frame,
            text="🗑️ タブ削除",
            font=("MeiryoUI", 9),
            bg="#E74C3C",
            fg="white",
            bd=0,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self.delete_tab,
        ).pack(side="left", padx=3)

        # --- 2. メインエリア ---
        main_frame = tk.Frame(self.root, bg=BG_COLOR, padx=15, pady=15)
        main_frame.pack(fill="both", expand=True)

        card_frame = tk.Frame(
            main_frame, bg="white", relief="solid", bd=1, padx=15, pady=10
        )
        card_frame.pack(fill="x", pady=(0, 10))

        # 全タブ横断検索
        search_frame = tk.Frame(card_frame, bg="white")
        search_frame.pack(fill="x", pady=(0, 8))
        tk.Label(
            search_frame,
            text="🔍 全タブ横断検索:",
            font=("MeiryoUI", 9, "bold"),
            bg="white",
        ).pack(side="left", padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *args: self.filter_data())
        search_entry = tk.Entry(
            search_frame,
            textvariable=self.search_var,
            font=("MeiryoUI", 10),
            bg="#F0F3F4",
            bd=1,
            relief="flat",
        )
        search_entry.pack(side="left", fill="x", expand=True, ipady=4)

        ttk.Separator(card_frame, orient="horizontal").pack(fill="x", pady=6)

        # 登録フォーム（2段構成に拡張）
        input_frame = tk.Frame(card_frame, bg="white")
        input_frame.pack(fill="x")

        # 1段目
        tk.Label(
            input_frame, text="品名:", font=("MeiryoUI", 9, "bold"), bg="white"
        ).grid(row=0, column=0, sticky="w")
        self.entry_name = tk.Entry(
            input_frame,
            width=20,
            font=("MeiryoUI", 9),
            bg="#F0F3F4",
            bd=1,
            relief="flat",
        )
        self.entry_name.grid(row=0, column=1, padx=(5, 10), ipady=3)

        tk.Label(
            input_frame, text="数量:", font=("MeiryoUI", 9, "bold"), bg="white"
        ).grid(row=0, column=2, sticky="w")
        self.entry_qty = tk.Entry(
            input_frame,
            width=6,
            font=("MeiryoUI", 9),
            bg="#F0F3F4",
            bd=1,
            relief="flat",
        )
        self.entry_qty.grid(row=0, column=3, padx=(5, 10), ipady=3)

        tk.Label(
            input_frame, text="単位:", font=("MeiryoUI", 9, "bold"), bg="white"
        ).grid(row=0, column=4, sticky="w")
        self.combo_unit = ttk.Combobox(
            input_frame,
            values=[
                "個",
                "本",
                "枚",
                "箱",
                "セット",
                "台",
                "kg",
                "L",
                "冊",
                "パック",
            ],
            width=6,
            font=("MeiryoUI", 9),
        )
        self.combo_unit.set("個")
        self.combo_unit.grid(row=0, column=5, padx=(5, 15), ipady=3)

        # 2段目
        tk.Label(
            input_frame,
            text="保管場所:",
            font=("MeiryoUI", 9, "bold"),
            bg="white",
        ).grid(row=1, column=0, sticky="w", pady=(8, 0))
        self.entry_loc = tk.Entry(
            input_frame,
            width=20,
            font=("MeiryoUI", 9),
            bg="#F0F3F4",
            bd=1,
            relief="flat",
        )
        self.entry_loc.grid(row=1, column=1, padx=(5, 10), pady=(8, 0), ipady=3)

        tk.Label(
            input_frame, text="備考:", font=("MeiryoUI", 9, "bold"), bg="white"
        ).grid(row=1, column=2, sticky="w", pady=(8, 0))
        self.entry_rem = tk.Entry(
            input_frame,
            width=30,
            font=("MeiryoUI", 9),
            bg="#F0F3F4",
            bd=1,
            relief="flat",
        )
        self.entry_rem.grid(
            row=1,
            column=3,
            columnspan=3,
            sticky="we",
            padx=(5, 15),
            pady=(8, 0),
            ipady=3,
        )

        # 登録ボタン
        btn_add = tk.Button(
            input_frame,
            text="＋ 登録",
            font=("MeiryoUI", 9, "bold"),
            bg=ACCENT_BLUE,
            fg="white",
            bd=0,
            padx=20,
            pady=10,
            cursor="hand2",
            command=self.add_item,
        )
        btn_add.grid(row=0, column=6, rowspan=2, padx=10, sticky="nsew")

        # --- 3. タブエリア（Notebook） ---
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        self.notebook.bind("<Double-1>", self.on_notebook_double_click)

        # --- 4. 下部ボタンバー ---
        action_frame = tk.Frame(main_frame, bg=BG_COLOR)
        action_frame.pack(fill="x", pady=(12, 0))

        tk.Button(
            action_frame,
            text="➖ 1つ使う",
            font=("MeiryoUI", 9, "bold"),
            bg=ACCENT_ORANGE,
            fg="white",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.use_item,
        ).pack(side="left", padx=(0, 5))

        tk.Button(
            action_frame,
            text="➕ 1つ補充",
            font=("MeiryoUI", 9, "bold"),
            bg=ACCENT_GREEN,
            fg="white",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.add_one_item,
        ).pack(side="left", padx=5)

        tk.Label(
            action_frame,
            text="※ヘッダー(列名)クリックで並び替え / 右クリックで各種メニュー表示",
            font=("MeiryoUI", 8),
            bg=BG_COLOR,
            fg="#7F8C8D",
        ).pack(side="left", padx=15)

        tk.Button(
            action_frame,
            text="🔄 最新表示",
            font=("MeiryoUI", 9),
            bg="#95A5A6",
            fg="white",
            bd=0,
            padx=10,
            pady=6,
            cursor="hand2",
            command=self.load_data,
        ).pack(side="right")

    def rebuild_notebook_tabs(self, items):
        """タブとTreeviewの再構築"""
        for tab in self.notebook.tabs():
            self.notebook.forget(tab)
        self.trees.clear()

        # カラム定義
        columns = ("品名", "在庫数", "単位", "更新日時", "保管場所", "備考", "状態")

        for tab_name in items.keys():
            frame = tk.Frame(self.notebook, bg=BG_COLOR)
            self.notebook.add(frame, text=f" {tab_name} ")

            tree = ttk.Treeview(frame, columns=columns, show="headings")

            # 各列の設定とソート機能のバインド
            for col in columns:
                tree.heading(
                    col,
                    text=col,
                    command=lambda _t=tree, _c=col: self.treeview_sort_column(
                        _t, _c, False
                    ),
                )

            tree.column("品名", width=160, anchor="w")
            tree.column("在庫数", width=60, anchor="center")
            tree.column("単位", width=50, anchor="center")
            tree.column("更新日時", width=120, anchor="center")
            tree.column("保管場所", width=110, anchor="w")
            tree.column("備考", width=160, anchor="w")
            tree.column("状態", width=90, anchor="center")

            scrollbar = ttk.Scrollbar(
                frame, orient="vertical", command=tree.yview
            )
            tree.configure(yscroll=scrollbar.set)

            # イベントバインド（ダブルクリック編集 ＆ 右クリック）
            tree.bind("<Double-1>", self.on_row_double_click)
            tree.bind("<Button-3>", self.show_context_menu)  # Windows/Linux用
            tree.bind("<Button-2>", self.show_context_menu)  # macOS用対策

            tree.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            tree.tag_configure(
                "empty", background="#FADBD8", foreground="#78281F"
            )
            tree.tag_configure(
                "low", background="#FCF3CF", foreground="#7D6608"
            )
            tree.tag_configure("normal", background="#FFFFFF")

            self.trees[tab_name] = tree

    def treeview_sort_column(self, tree, col, reverse):
        """列ヘッダーのクリックによるソート"""
        l = [(tree.set(k, col), k) for k in tree.get_children("")]

        # 数値ソートが可能な列（在庫数など）の考慮
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)

        # 順番を入れ替え
        for index, (val, k) in enumerate(l):
            tree.move(k, "", index)

        # 次回クリック時は逆順にする設定
        tree.heading(
            col,
            command=lambda _t=tree, _c=col: self.treeview_sort_column(
                _t, _c, not reverse
            ),
        )

    def show_context_menu(self, event):
        """右クリックメニューの表示"""
        tab_name, tree = self.get_current_tab_info()
        iid = tree.identify_row(event.y)
        if iid:
            tree.selection_set(iid)  # カーソル下の行を選択状態にする
        self.context_menu.post(event.x_root, event.y_root)

    def get_current_tab_info(self):
        idx = self.notebook.index("current")
        tab_name = self.notebook.tab(idx, "text").strip()
        tree = self.trees[tab_name]
        return tab_name, tree

    def get_all_items(self):
        items = {}
        if os.path.exists(FILE_NAME):
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                next(reader, None)
                for row in reader:
                    if len(row) >= 1 and row[0].strip():
                        tab = row[0].strip()
                        if tab not in items:
                            items[tab] = {}

                        if len(row) >= 3 and row[1].strip():
                            name = row[1].strip()
                            qty = int(row[2]) if row[2].isdigit() else 0
                            unit = row[3].strip() if len(row) >= 4 else "個"
                            # 新規追加項目（旧CSV互換対応）
                            updated_at = row[4].strip() if len(row) >= 5 else ""
                            loc = row[5].strip() if len(row) >= 6 else ""
                            rem = row[6].strip() if len(row) >= 7 else ""

                            items[tab][name] = {
                                "qty": qty,
                                "unit": unit,
                                "updated_at": updated_at,
                                "location": loc,
                                "remarks": rem,
                            }

        if not items:
            items = {"事務用品": {}, "PC・機材": {}, "その他": {}}
        return items

    def save_all_items(self, items):
        with open(FILE_NAME, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "タブ名",
                    "品名",
                    "在庫数",
                    "単位",
                    "更新日時",
                    "保管場所",
                    "備考",
                ]
            )
            for tab, tab_items in items.items():
                if not tab_items:
                    writer.writerow([tab, "", "", "", "", "", ""])
                else:
                    for name, data in tab_items.items():
                        writer.writerow(
                            [
                                tab,
                                name,
                                data["qty"],
                                data["unit"],
                                data.get("updated_at", ""),
                                data.get("location", ""),
                                data.get("remarks", ""),
                            ]
                        )

    def load_data(self, filter_text=""):
        items = self.get_all_items()

        if set(items.keys()) != set(self.trees.keys()):
            self.rebuild_notebook_tabs(items)

        for tab_name, tree in self.trees.items():
            for row in tree.get_children():
                tree.delete(row)

            tab_items = items.get(tab_name, {})
            for name, data in tab_items.items():
                if filter_text and filter_text not in name.lower():
                    continue

                qty, unit = data["qty"], data["unit"]
                updated = data.get("updated_at", "")
                loc = data.get("location", "")
                rem = data.get("remarks", "")

                if qty == 0:
                    status, tag = "❌ 在庫切れ", "empty"
                elif qty <= 2:
                    status, tag = "⚠️ 要補充", "low"
                else:
                    status, tag = "✅ 良好", "normal"

                tree.insert(
                    "",
                    "end",
                    values=(name, qty, unit, updated, loc, rem, status),
                    tags=(tag,),
                )

    def filter_data(self):
        self.load_data(filter_text=self.search_var.get().strip().lower())

    # --- タブ操作 ---
    def add_tab(self):
        new_tab = simpledialog.askstring("タブ追加", "新しいカテゴリを入力:")
        if not new_tab or not new_tab.strip():
            return
        new_tab = new_tab.strip()
        items = self.get_all_items()
        if new_tab in items:
            messagebox.showwarning("エラー", "既に存在します")
            return
        items[new_tab] = {}
        self.save_all_items(items)
        self.load_data(self.search_var.get())
        self.notebook.select(list(items.keys()).index(new_tab))

    def delete_tab(self):
        items = self.get_all_items()
        if len(items) <= 1:
            messagebox.showwarning("エラー", "最低1つのタブが必要です")
            return
        tab_name, _ = self.get_current_tab_info()
        if messagebox.askyesno("確認", f"「{tab_name}」タブを削除しますか？"):
            del items[tab_name]
            self.save_all_items(items)
            self.load_data(self.search_var.get())

    def on_notebook_double_click(self, event):
        try:
            index = self.notebook.index(f"@{event.x},{event.y}")
        except Exception:
            return
        items = self.get_all_items()
        old_tab = list(items.keys())[index]
        new_tab = simpledialog.askstring(
            "名前変更", "新しいタブ名:", initialvalue=old_tab
        )
        if not new_tab or new_tab.strip() == old_tab:
            return
        new_tab = new_tab.strip()
        if new_tab in items:
            return
        new_items = {
            new_tab if k == old_tab else k: v for k, v in items.items()
        }
        self.save_all_items(new_items)
        self.load_data(self.search_var.get())
        self.notebook.select(index)

    # --- 行編集（ダブルクリック） ---
    def on_row_double_click(self, event):
        tab_name, tree = self.get_current_tab_info()
        selected = tree.selection()
        if not selected:
            return

        column = tree.identify_column(event.x)
        values = tree.item(selected[0], "values")
        old_name, old_qty, old_unit = (
            str(values[0]),
            int(values[1]),
            str(values[2]),
        )
        old_loc, old_rem = str(values[4]), str(values[5])
        items = self.get_all_items()
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

        if column == "#1":  # 品名
            new_name = simpledialog.askstring(
                "編集", "新しい品名:", initialvalue=old_name
            )
            if new_name and new_name.strip() != old_name:
                data = items[tab_name].pop(old_name)
                data["updated_at"] = now
                items[tab_name][new_name.strip()] = data
                self.save_all_items(items)
                self.load_data(self.search_var.get())
        elif column == "#2":  # 在庫数
            new_qty = simpledialog.askinteger(
                "編集",
                "正しい在庫数:",
                initialvalue=old_qty,
                minvalue=0,
            )
            if new_qty is not None and new_qty != old_qty:
                items[tab_name][old_name]["qty"] = new_qty
                items[tab_name][old_name]["updated_at"] = now
                self.save_all_items(items)
                self.load_data(self.search_var.get())
        elif column == "#3":  # 単位
            new_unit = simpledialog.askstring(
                "編集", "新しい単位:", initialvalue=old_unit
            )
            if new_unit and new_unit.strip() != old_unit:
                items[tab_name][old_name]["unit"] = new_unit.strip()
                items[tab_name][old_name]["updated_at"] = now
                self.save_all_items(items)
                self.load_data(self.search_var.get())
        elif column == "#5":  # 保管場所
            new_loc = simpledialog.askstring(
                "編集", "保管場所:", initialvalue=old_loc
            )
            if new_loc is not None and new_loc.strip() != old_loc:
                items[tab_name][old_name]["location"] = new_loc.strip()
                items[tab_name][old_name]["updated_at"] = now
                self.save_all_items(items)
                self.load_data(self.search_var.get())
        elif column == "#6":  # 備考
            new_rem = simpledialog.askstring(
                "編集", "備考:", initialvalue=old_rem
            )
            if new_rem is not None and new_rem.strip() != old_rem:
                items[tab_name][old_name]["remarks"] = new_rem.strip()
                items[tab_name][old_name]["updated_at"] = now
                self.save_all_items(items)
                self.load_data(self.search_var.get())

    # --- 基本・拡張アクション ---
    def add_item(self):
        tab_name, _ = self.get_current_tab_info()
        name = self.entry_name.get().strip()
        qty = self.entry_qty.get().strip()
        unit = self.combo_unit.get().strip() or "個"
        loc = self.entry_loc.get().strip()
        rem = self.entry_rem.get().strip()

        if not name or not qty.isdigit():
            messagebox.showwarning(
                "エラー", "品名と正しい数字を入力してください。"
            )
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        items = self.get_all_items()
        items[tab_name][name] = {
            "qty": int(qty),
            "unit": unit,
            "updated_at": now,
            "location": loc,
            "remarks": rem,
        }
        self.save_all_items(items)

        self.entry_name.delete(0, tk.END)
        self.entry_qty.delete(0, tk.END)
        self.combo_unit.set("個")
        self.entry_loc.delete(0, tk.END)
        self.entry_rem.delete(0, tk.END)
        self.load_data(self.search_var.get())

    def use_item(self):
        self._update_qty(-1)

    def add_one_item(self):
        self._update_qty(1)

    def _update_qty(self, delta):
        tab_name, tree = self.get_current_tab_info()
        selected = tree.selection()
        if not selected:
            return

        name = str(tree.item(selected[0])["values"][0])
        qty = int(tree.item(selected[0])["values"][1])

        if qty + delta < 0:
            messagebox.showwarning("在庫切れ", "これ以上減らせません。")
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        items = self.get_all_items()
        items[tab_name][name]["qty"] = qty + delta
        items[tab_name][name]["updated_at"] = now
        self.save_all_items(items)
        self.load_data(self.search_var.get())

    def delete_item(self):
        tab_name, tree = self.get_current_tab_info()
        selected = tree.selection()
        if not selected:
            return
        name = str(tree.item(selected[0])["values"][0])
        if messagebox.askyesno("確認", f"「{name}」を削除しますか？"):
            items = self.get_all_items()
            if name in items[tab_name]:
                del items[tab_name][name]
                self.save_all_items(items)
                self.load_data(self.search_var.get())

    def add_item_dialog(self):
        """右クリックから簡易に新規登録ダイアログを出す"""
        tab_name, _ = self.get_current_tab_info()
        new_name = simpledialog.askstring(
            "挿入", f"「{tab_name}」に追加する品名を入力:"
        )
        if not new_name or not new_name.strip():
            return
        new_name = new_name.strip()

        items = self.get_all_items()
        if new_name in items[tab_name]:
            messagebox.showwarning("エラー", "既に存在します")
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        items[tab_name][new_name] = {
            "qty": 0,
            "unit": "個",
            "updated_at": now,
            "location": "",
            "remarks": "",
        }
        self.save_all_items(items)
        self.load_data(self.search_var.get())
        messagebox.showinfo(
            "追加完了",
            f"「{new_name}」を挿入しました。\n一覧から行をダブルクリックして個数等を編集してください。",
        )

    def export_excel(self):
        """Excelで開ける形式(Shift-JISのCSV)で出力"""
        tab_name, tree = self.get_current_tab_info()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("Excel向けCSV", "*.csv")],
            initialfile=f"在庫データ_{tab_name}.csv",
        )
        if not file_path:
            return
        try:
            with open(
                file_path,
                "w",
                newline="",
                encoding="shift-jis",
                errors="replace",
            ) as f:
                writer = csv.writer(f)
                writer.writerow(
                    [
                        "品名",
                        "在庫数",
                        "単位",
                        "更新日時",
                        "保管場所",
                        "備考",
                        "状態",
                    ]
                )
                for row in tree.get_children():
                    writer.writerow(tree.item(row)["values"])
            messagebox.showinfo(
                "完了", f"エクセル向けに出力しました。\n保存先: {file_path}"
            )
        except Exception as e:
            messagebox.showerror("エラー", f"出力に失敗しました:\n{e}")

    def export_pdf(self):
        """安全な環境でPDF化するためのHTML出力"""
        tab_name, tree = self.get_current_tab_info()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".html",
            filetypes=[("PDF印刷用HTML", "*.html")],
            initialfile=f"在庫一覧_{tab_name}.html",
        )
        if not file_path:
            return
        try:
            html = f"""
            <html><head><meta charset='utf-8'><title>{tab_name} 在庫一覧</title>
            <style>
                body {{ font-family: sans-serif; padding: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #333; padding: 8px; text-align: left; }}
                th {{ background-color: #2C3E50; color: white; }}
            </style>
            </head><body>
            <h2>{tab_name} 在庫一覧</h2>
            <table>
                <tr><th>品名</th><th>在庫数</th><th>単位</th><th>更新日時</th><th>保管場所</th><th>備考</th><th>状態</th></tr>
            """
            for row in tree.get_children():
                v = tree.item(row)["values"]
                html += f"<tr><td>{v[0]}</td><td>{v[1]}</td><td>{v[2]}</td><td>{v[3]}</td><td>{v[4]}</td><td>{v[5]}</td><td>{v[6]}</td></tr>"

            html += "</table></body></html>"

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(html)

            webbrowser.open(file_path)
            messagebox.showinfo(
                "出力完了",
                "ブラウザで一覧を開きました。\n右クリックや設定メニューの「印刷」から『PDFとして保存』を選択してPDF化してください。",
            )
        except Exception as e:
            messagebox.showerror("エラー", f"出力に失敗しました:\n{e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = UltimateInventoryAppV3(root)
    root.mainloop()
