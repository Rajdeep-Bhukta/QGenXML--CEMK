# !/usr/bin/env python3

"""
Moodle Question Editor — single-file app
- No initial blank tab; New File prompts for filename/path.
- Insert images stores absolute path per-tab.
- Preview: shows inline thumbnails; removes image tag text.
- PDF export: embeds original images; does NOT print the [IMG:...] tag text anywhere.
Requires: pillow, reportlab
"""

import os
import uuid
import re
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import xml.etree.ElementTree as ET
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from PIL import Image, ImageTk

# ---------------------------
# Model
# ---------------------------
class Question:
    def __init__(self, qid=None, qtype="MCQ", text="", marks=1.0, options=None, correct_index=None):
        self.qid = qid or str(uuid.uuid4())
        self.qtype = qtype  # "MCQ", "SAQ", "Long"
        self.text = text
        self.marks = float(marks)
        self.options = options or []
        self.correct_index = correct_index

def app_type_to_moodle(t):
    if t == "MCQ": return "multichoice"
    if t == "SAQ": return "shortanswer"
    return "essay"

def moodle_type_to_app(t):
    if t == "multichoice": return "MCQ"
    if t == "shortanswer": return "SAQ"
    return "Long"

# ---------------------------
# App
# ---------------------------
class MoodleEditorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Moodle Question Editor")
        self.root.geometry("1250x720")
        self.root.minsize(1000, 600)

        # state
        self.tabs = {}  # key -> {"frame","path","name","questions","images"}
        self.preview_image_refs = {}
        self.selected_question_index = None
        self.root_dir = os.getcwd()
        self.status_var = tk.StringVar(value="Ready")
        ##

        # Header info
        self.header_info = {
            "college": "",
            "department": "",
            "subject": "",
            "subject_code": "",
            "exam_name": ""
        }

        # Group info list
        self.group_sections = []

        ##

        # Header
        header = tk.Frame(root, bg="#1F3A93", height=60)
        header.pack(side=tk.TOP, fill=tk.X)
        tk.Label(header, text="Moodle Question Editor", bg="#1F3A93", fg="white",
                 font=("Segoe UI", 16, "bold")).pack(side=tk.LEFT, padx=12, pady=10)

        # Toolbar
        toolbar = tk.Frame(root, bg="#2C3E50", height=36)
        toolbar.pack(side=tk.TOP, fill=tk.X)
        ttk.Button(toolbar, text="Select Folder", command=self.select_folder).pack(side=tk.LEFT, padx=6, pady=4)
        ttk.Button(toolbar, text="Open File...", command=self.open_any_file).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="New File (Save As...)", command=self.new_file_tab).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Export XML", command=self.export_active_xml).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Export PDF", command=self.export_active_pdf).pack(side=tk.LEFT, padx=6)
        ttk.Button(toolbar, text="Verify", command=self.verify_active_xml).pack(side=tk.LEFT, padx=6)

        main = tk.Frame(root)
        main.pack(fill=tk.BOTH, expand=True)

        # Left panel (directory + question list)
        left_panel = tk.Frame(main, width=320, bg="#151B24")
        left_panel.pack(side=tk.LEFT, fill=tk.Y, padx=6, pady=6)
        left_panel.pack_propagate(False)

        tk.Label(left_panel, text="Directory Structure", bg="#151B24", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="nw", padx=8, pady=(6,2))
        dir_ctrl = tk.Frame(left_panel, bg="#151B24")
        dir_ctrl.pack(fill=tk.X, padx=8)
        self.dir_path_var = tk.StringVar(value=self.root_dir)
        ttk.Entry(dir_ctrl, textvariable=self.dir_path_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(dir_ctrl, text="Load", command=self.load_directory_from_path).pack(side=tk.LEFT, padx=4)

        self.dir_tree = ttk.Treeview(left_panel, show="tree")
        self.dir_tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        self.dir_tree.bind("<<TreeviewSelect>>", self.on_dir_select)
        self.load_directory(self.root_dir)

        tk.Label(left_panel, text="Questions (Active File)", bg="#151B24", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="nw", padx=8, pady=(6,2))
        self.question_listbox = tk.Listbox(left_panel, height=10)
        self.question_listbox.pack(fill=tk.X, padx=8, pady=(0,8))
        self.question_listbox.bind("<<ListboxSelect>>", self.on_question_select)
        qbtns = tk.Frame(left_panel, bg="#151B24")
        qbtns.pack(fill=tk.X, padx=8, pady=(0,8))
        ttk.Button(qbtns, text="New", command=self.new_question).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(qbtns, text="Edit", command=self.edit_question).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(qbtns, text="Delete", command=self.delete_question).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Center (notebook compact + editor)
        center = tk.Frame(main)
        center.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=6, pady=6)

        self.notebook = ttk.Notebook(center)
        self.notebook.pack(fill=tk.X)
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

        editor_frame = tk.Frame(center, padx=6, pady=6)
        editor_frame.pack(fill=tk.X, anchor="n")

        ttk.Label(editor_frame, text="Question Type:").grid(row=0, column=0, sticky="w")
        self.qtype_var = tk.StringVar(value="MCQ")
        ttk.Combobox(editor_frame, textvariable=self.qtype_var, values=["MCQ", "SAQ", "Long"], width=10).grid(row=0, column=1, sticky="w", padx=4)

        ttk.Label(editor_frame, text="Marks:").grid(row=0, column=2, sticky="w", padx=(12,0))
        self.marks_var = tk.StringVar(value="1")
        ttk.Entry(editor_frame, textvariable=self.marks_var, width=6).grid(row=0, column=3, sticky="w", padx=4)

        ttk.Label(editor_frame, text="Insert at (#):").grid(row=0, column=4, sticky="w", padx=(12,0))
        self.insert_at_var = tk.IntVar(value=0)
        try:
            self.insert_spin = ttk.Spinbox(editor_frame, from_=0, to=9999, textvariable=self.insert_at_var, width=6)
        except Exception:
            self.insert_spin = tk.Spinbox(editor_frame, from_=0, to=9999, textvariable=self.insert_at_var, width=6)
        self.insert_spin.grid(row=0, column=5, sticky="w", padx=4)

        ttk.Label(editor_frame, text="Question Text:").grid(row=1, column=0, columnspan=6, sticky="w", pady=(6,0))
        self.text_area = tk.Text(editor_frame, height=4)
        self.text_area.grid(row=2, column=0, columnspan=6, sticky="we", pady=(0,6))

        # MCQ options
        self.option_entries = []
        opts_frame = tk.Frame(editor_frame)
        opts_frame.grid(row=3, column=0, columnspan=6, sticky="we", pady=(0,6))
        for i, label in enumerate(["A","B","C","D"]):
            f = tk.Frame(opts_frame)
            f.pack(fill=tk.X, pady=2)
            tk.Label(f, text=f"{label}:", width=3).pack(side=tk.LEFT)
            e = ttk.Entry(f)
            e.pack(side=tk.LEFT, fill=tk.X, expand=True)
            self.option_entries.append(e)

        ttk.Label(editor_frame, text="Correct Option Index (0-3):").grid(row=4, column=0, sticky="w", pady=(4,0))
        self.correct_var = tk.StringVar(value="0")
        ttk.Entry(editor_frame, textvariable=self.correct_var, width=6).grid(row=4, column=1, sticky="w", padx=(2,0))
        ##

        # =========================
        # HEADER TOGGLE BUTTON
        # =========================
        self.header_visible = False

        ttk.Button(
            editor_frame,
            text="Header Details ▼",
            command=self.toggle_header_section
        ).grid(row=5, column=0, columnspan=6, sticky="we", pady=5)

        # Hidden header frame
        self.header_drop = ttk.LabelFrame(editor_frame, text="Exam Header Details")

        tk.Label(self.header_drop, text="College Name").grid(row=0, column=0, sticky="w")
        self.college_var = tk.StringVar()
        ttk.Entry(self.header_drop, textvariable=self.college_var, width=40).grid(row=0, column=1, padx=5, pady=2)

        tk.Label(self.header_drop, text="Department").grid(row=1, column=0, sticky="w")
        self.department_var = tk.StringVar()
        ttk.Entry(self.header_drop, textvariable=self.department_var, width=40).grid(row=1, column=1, padx=5, pady=2)

        tk.Label(self.header_drop, text="Subject").grid(row=2, column=0, sticky="w")
        self.subject_var = tk.StringVar()
        ttk.Entry(self.header_drop, textvariable=self.subject_var, width=40).grid(row=2, column=1, padx=5, pady=2)

        tk.Label(self.header_drop, text="Subject Code").grid(row=3, column=0, sticky="w")
        self.subject_code_var = tk.StringVar()
        ttk.Entry(self.header_drop, textvariable=self.subject_code_var, width=40).grid(row=3, column=1, padx=5, pady=2)

        tk.Label(self.header_drop, text="Exam Name").grid(row=4, column=0, sticky="w")
        self.exam_name_var = tk.StringVar()
        ttk.Entry(self.header_drop, textvariable=self.exam_name_var, width=40).grid(row=4, column=1, padx=5, pady=2)

        ttk.Button(
            self.header_drop,
            text="Add Header",
            command=self.add_header_info
        ).grid(row=5, column=0, columnspan=2, pady=5)

        ##       
        # =========================
        # GROUP TOGGLE BUTTON
        # =========================
        self.group_visible = False

        ttk.Button(
            editor_frame,
            text="Question Group ▼",
            command=self.toggle_group_section
        ).grid(row=6, column=0, columnspan=6, sticky="we", pady=5)

        # Hidden group frame
        self.group_drop = ttk.LabelFrame(editor_frame, text="Question Group")

        tk.Label(self.group_drop, text="Group Name").grid(row=0, column=0, sticky="w")
        self.group_name_var = tk.StringVar()
        ttk.Entry(self.group_drop, textvariable=self.group_name_var, width=40).grid(row=0, column=1, padx=5, pady=2)

        tk.Label(self.group_drop, text="Instruction").grid(row=1, column=0, sticky="w")
        self.group_instruction_var = tk.StringVar()
        ttk.Entry(self.group_drop, textvariable=self.group_instruction_var, width=40).grid(row=1, column=1, padx=5, pady=2)

        tk.Label(self.group_drop, text="Marks").grid(row=2, column=0, sticky="w")
        self.group_marks_var = tk.StringVar()
        ttk.Entry(self.group_drop, textvariable=self.group_marks_var, width=20).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        tk.Label(self.group_drop, text="Start From Question").grid(row=3, column=0, sticky="w")

        self.group_start_var = tk.StringVar()

        ttk.Entry(
            self.group_drop,
            textvariable=self.group_start_var,
            width=20
        ).grid(row=3, column=1, padx=5, pady=2, sticky="w")

        ttk.Button(
            self.group_drop,
            text="Add Group",
            command=self.add_group_section
        ).grid(row=4, column=0, columnspan=2, pady=5)
        ##
        ##
        edit_btns = tk.Frame(editor_frame)
        edit_btns.grid(row=9, column=0, columnspan=6, pady=6)
        ttk.Button(edit_btns, text="Insert Image (into current question)", command=self.insert_image).pack(side=tk.LEFT, padx=6)
        ttk.Button(edit_btns, text="Save/Add", command=self.save_question).pack(side=tk.LEFT, padx=6)
        ttk.Button(edit_btns, text="Clear", command=self.clear_editor).pack(side=tk.LEFT, padx=6)

        # Right preview
        right_panel = tk.Frame(main, width=420, bg="#0F1720")
        right_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=6, pady=6)
        right_panel.pack_propagate(False)
        tk.Label(right_panel, text="Preview (Active File)", bg="#0F1720", fg="white", font=("Segoe UI", 11, "bold")).pack(anchor="nw", padx=8, pady=(6,2))
        self.preview_text = tk.Text(right_panel, state=tk.DISABLED, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)

        # Status
        status = tk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor="w")
        status.pack(side=tk.BOTTOM, fill=tk.X)

        self.set_status("Ready — create New File or Open File.")

    # ---------- Directory ----------
    def load_directory(self, path):
        self.dir_tree.delete(*self.dir_tree.get_children())
        try:
            root_name = os.path.basename(path) or path
            root_node = self.dir_tree.insert("", "end", text=root_name, open=True, values=(path,))
            try:
                entries = sorted(os.listdir(path))
            except Exception:
                entries = []
            for entry in entries:
                full = os.path.join(path, entry)
                if os.path.isdir(full):
                    node = self.dir_tree.insert(root_node, "end", text=entry, open=False, values=(full,))
                    try:
                        for sub in sorted(os.listdir(full)):
                            sfull = os.path.join(full, sub)
                            self.dir_tree.insert(node, "end", text=sub, values=(sfull,))
                    except Exception:
                        pass
                else:
                    self.dir_tree.insert(root_node, "end", text=entry, values=(full,))
            self.set_status(f"Directory loaded: {path}")
        except Exception as e:
            self.set_status(f"Failed loading dir: {e}")

    def load_directory_from_path(self):
        p = self.dir_path_var.get().strip()
        if os.path.isdir(p):
            self.root_dir = p
            self.load_directory(p)
        else:
            messagebox.showwarning("Directory", "Invalid directory path.")

    def on_dir_select(self, ev):
        sel = self.dir_tree.selection()
        if not sel:
            return
        path = self.dir_tree.item(sel[0], "values")[0]
        if os.path.isdir(path):
            try:
                files = sorted(os.listdir(path))
            except Exception:
                files = []
            if not files:
                messagebox.showinfo("Directory", "No files inside selected directory.")
                return
            if messagebox.askyesno("Open files", f"Open all files from:\n{path} ?"):
                for fn in files:
                    full = os.path.join(path, fn)
                    if os.path.isfile(full):
                        self.open_file_into_tab(full)
            else:
                p = filedialog.askopenfilename(initialdir=path, title="Open file", filetypes=[("All files","*.*")])
                if p:
                    self.open_file_into_tab(p)
        else:
            if messagebox.askyesno("Open file", f"Open file:\n{path} ?"):
                self.open_file_into_tab(path)

    def select_folder(self):
        folder = filedialog.askdirectory(title="Select folder", initialdir=self.root_dir)
        if not folder:
            return
        self.dir_path_var.set(folder)
        self.root_dir = folder
        self.load_directory(folder)

    def open_any_file(self):
        p = filedialog.askopenfilename(title="Open file", initialdir=self.root_dir, filetypes=[("All files","*.*")])
        if p:
            self.open_file_into_tab(p)

    # ---------- Tabs ----------
    def new_file_tab(self, path=None, name=None):
        if not path:
            dest = filedialog.asksaveasfilename(title="Create New File (choose name & location)",
                                                defaultextension=".xml",
                                                initialdir=self.root_dir,
                                                filetypes=[("XML Files","*.xml"),("All files","*.*")])
            if not dest:
                self.set_status("New file cancelled.")
                return None
            path = dest

        frame = tk.Frame(self.notebook)
        display_name = name or (os.path.basename(path) if path else f"Untitled-{len(self.tabs)+1}")
        self.notebook.add(frame, text=display_name)
        tab_key = str(uuid.uuid4())
        self.tabs[tab_key] = {"frame": frame, "path": path, "name": display_name, "questions": [], "images": {},"groups":[]}
        frame._tab_key = tab_key
        self.preview_image_refs[tab_key] = []
        if path and os.path.isfile(path) and path.lower().endswith(".xml"):
            self.load_xml_into_tab(path, tab_key)
        self.notebook.select(frame)
        return tab_key

    def open_file_into_tab(self, path):
        ap = os.path.abspath(path)
        for k,v in self.tabs.items():
            if v.get("path") and os.path.abspath(v["path"]) == ap:
                self.notebook.select(v["frame"])
                return k
        return self.new_file_tab(path=path, name=os.path.basename(path))

    def load_xml_into_tab(self, path, tab_key):
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            questions = []
            for qnode in root.findall("question"):
                t = moodle_type_to_app(qnode.get("type", "multichoice"))
                text = ""
                qt = qnode.find("questiontext")
                if qt is not None:
                    tn = qt.find("text")
                    if tn is not None and tn.text:
                        text = tn.text
                marks = float(qnode.findtext("defaultgrade", "1") or 1)
                options = []
                correct = None
                for i,a in enumerate(qnode.findall("answer")):
                    txt = a.findtext("text","") or ""
                    options.append(txt)
                    if a.get("fraction") and float(a.get("fraction","0")) == 100:
                        correct = i
                q = Question(qid=str(uuid.uuid4()), qtype=t, text=text, marks=marks, options=options, correct_index=correct)
                questions.append(q)
            self.tabs[tab_key]["questions"] = questions
            self.tabs[tab_key]["path"] = path
            self.tabs[tab_key]["name"] = os.path.basename(path)
            try:
                frame = self.tabs[tab_key]["frame"]
                idx = self.notebook.index(frame)
                self.notebook.tab(idx, text=os.path.basename(path))
            except Exception:
                pass
            if self.get_active_tab_key() == tab_key:
                self.refresh_question_list()
                self.update_preview()
            self.set_status(f"Loaded {len(questions)} questions from {os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("Open XML", f"Failed to open XML: {e}")

    def on_tab_changed(self, ev):
        sel = self.notebook.select()
        if not sel:
            return
        widget = self.root.nametowidget(sel)
        tab_key = getattr(widget, "_tab_key", None)
        self.refresh_question_list()
        self.clear_editor()
        self.update_preview()
        info = self.tabs.get(tab_key, {})
        self.set_status(f"Switched to: {info.get('name')} ({info.get('path') or 'unsaved'})")

    def get_active_tab_key(self):
        sel = self.notebook.select()
        if not sel:
            return None
        widget = self.root.nametowidget(sel)
        return getattr(widget, "_tab_key", None)

    # ---------- Questions ----------
    def refresh_question_list(self):
        key = self.get_active_tab_key()
        qlist = self.tabs.get(key, {}).get("questions", [])
        self.question_listbox.delete(0, tk.END)
        for i,q in enumerate(qlist, start=1):
            snippet = " ".join(q.text.strip().splitlines())[:50]
            self.question_listbox.insert(tk.END, f"{i}. [{q.qtype}] ({q.marks}m) {snippet}{'...' if len(snippet)>=50 else ''}")

    def new_question(self):
        self.clear_editor()
        self.selected_question_index = None
        self.set_status("New question - edit fields then Save/Add")

    def save_question(self):
        key = self.get_active_tab_key()
        if not key:
            messagebox.showwarning("No tab", "Open or create a tab first.")
            return
        try:
            qtype = self.qtype_var.get()
            marks = float(self.marks_var.get())
        except Exception:
            messagebox.showwarning("Marks", "Enter valid numeric marks.")
            return
        text = self.text_area.get("1.0", tk.END).strip()
        options = [e.get() for e in self.option_entries]
        correct = None
        if qtype == "MCQ":
            try:
                ci = int(self.correct_var.get())
                if 0 <= ci < len(options):
                    correct = ci
            except Exception:
                correct = None

        idx = getattr(self, "selected_question_index", None)
        insert_at = int(self.insert_at_var.get() or 0)
        if idx is None:
            q = Question(qid=str(uuid.uuid4()), qtype=qtype, text=text, marks=marks, options=options, correct_index=correct)
            if insert_at and 1 <= insert_at <= len(self.tabs[key]["questions"]):
                self.tabs[key]["questions"].insert(insert_at-1, q)
                self.set_status(f"Question inserted at position {insert_at}")
            else:
                self.tabs[key]["questions"].append(q)
                self.set_status("Question added")
        else:
            k = self.get_active_tab_key()
            q = self.tabs[k]["questions"][idx]
            q.qtype = qtype
            q.marks = marks
            q.text = text
            q.options = options
            q.correct_index = correct
            self.set_status("Question updated")
        self.refresh_question_list()
        self.update_preview()
        self.clear_editor()
        self.selected_question_index = None
        self.insert_at_var.set(0)

    def edit_question(self):
        sel = self.question_listbox.curselection()
        if not sel:
            messagebox.showwarning("Edit", "Select a question to edit.")
            return
        idx = sel[0]
        key = self.get_active_tab_key()
        q = self.tabs[key]["questions"][idx]
        self.selected_question_index = idx
        self.qtype_var.set(q.qtype)
        self.marks_var.set(str(q.marks))
        self.text_area.delete("1.0", tk.END)
        self.text_area.insert(tk.END, q.text)
        for i,e in enumerate(self.option_entries):
            e.delete(0, tk.END)
            if i < len(q.options):
                e.insert(0, q.options[i])
        self.correct_var.set(str(q.correct_index) if q.correct_index is not None else "0")
        self.set_status("Loaded question into editor")

    def delete_question(self):
        sel = self.question_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.get_active_tab_key()
        if messagebox.askyesno("Delete", "Delete selected question?"):
            del self.tabs[key]["questions"][idx]
            self.refresh_question_list()
            self.update_preview()
            self.set_status("Question deleted")

    def on_question_select(self, ev):
        sel = self.question_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.get_active_tab_key()
        q = self.tabs[key]["questions"][idx]
        self.set_status(f"Selected: {q.text.strip()[:60]}...")

    def clear_editor(self):
        self.qtype_var.set("MCQ")
        self.marks_var.set("1")
        self.text_area.delete("1.0", tk.END)
        for e in self.option_entries:
            e.delete(0, tk.END)
        self.correct_var.set("0")
        self.selected_question_index = None
        self.insert_at_var.set(0)

    # ---------- Image insert ----------
    def insert_image(self):
        file = filedialog.askopenfilename(title="Select image", initialdir=self.root_dir,
                                          filetypes=[("Images","*.png;*.jpg;*.jpeg;*.bmp;*.gif")])
        if not file:
            return
        filename = os.path.basename(file)
        tag = f"[IMG:{filename}]"
        key = self.get_active_tab_key()
        if key:
            # store absolute path
            self.tabs[key]["images"][filename] = os.path.abspath(file)

        if self.selected_question_index is not None and key is not None:
            q = self.tabs[key]["questions"][self.selected_question_index]
            q.text = (q.text.rstrip() + "\n" + tag + "\n")
            self.set_status(f"Inserted image tag into question #{self.selected_question_index+1}: {tag}")
            self.refresh_question_list()
            self.update_preview()
        else:
            try:
                self.text_area.insert(tk.INSERT, "\n" + tag + "\n")
                self.set_status(f"Inserted image tag into editor: {tag}")
            except Exception:
                self.set_status("Could not insert tag into editor.")

    # ---------- Preview (no tag text shown) ----------
    def update_preview(self):
        key = self.get_active_tab_key()
        if key not in self.preview_image_refs:
            self.preview_image_refs[key] = []
        else:
            self.preview_image_refs[key].clear()

        self.preview_text.config(state=tk.NORMAL)
        self.preview_text.delete("1.0", tk.END)

        if not key:
            self.preview_text.insert(tk.END, "No active file/tab. Create (New File) or Open file to begin.")
            self.preview_text.config(state=tk.DISABLED)
            return

        qlist = self.tabs[key]["questions"]
        mcq_count = sum(1 for q in qlist if q.qtype == "MCQ")
        saq_count = sum(1 for q in qlist if q.qtype == "SAQ")
        long_count = sum(1 for q in qlist if q.qtype == "Long")
        self.preview_text.insert(tk.END, f"Counts — MCQ: {mcq_count} | SAQ: {saq_count} | Long: {long_count}\n\n", ("meta",))
        ##

        # Header display
        if any(self.header_info.values()):
            self.preview_text.insert(tk.END, f"College: {self.header_info['college']}\n")
            self.preview_text.insert(tk.END, f"Department: {self.header_info['department']}\n")
            self.preview_text.insert(tk.END, f"Subject: {self.header_info['subject']}\n")
            self.preview_text.insert(tk.END, f"Subject Code: {self.header_info['subject_code']}\n")
            self.preview_text.insert(tk.END, f"Exam Name: {self.header_info['exam_name']}\n\n")



        ##
        self.preview_text.tag_configure("meta", font=("Segoe UI", 9, "italic"), foreground="#AFCDE7")
        ##
        
        for i, q in enumerate(qlist, start=1):
            ##
            #groups = sorted(self.group_sections, key=lambda x: x["start_question"])
            ##
            key = self.get_active_tab_key()
            groups = sorted(self.tabs.get(key, {}).get("groups", []),
                            key=lambda x: x["start_question"])
            ##
            current_group = None

            for idx, g in enumerate(groups):
                start = g["start_question"]
                next_start = groups[idx + 1]["start_question"] if idx + 1 < len(groups) else float("inf")

                if start <= i < next_start:
                    current_group = g
                    break

            if current_group and i == current_group["start_question"]:
                self.preview_text.insert(tk.END, f"=== {current_group['group_name']} ===\n")
                self.preview_text.insert(tk.END, f"Instruction: {current_group['instruction']}\n")
                self.preview_text.insert(tk.END, f"Marks: {current_group['marks']}\n\n")
                ##
            ##
            # strip image tags from textual display
            text_without_tags = re.sub(r"\[IMG:[^\]]+\]", "", q.text).strip()
            self.preview_text.insert(tk.END, f"{i}. {text_without_tags}\n")
            self.preview_text.insert(tk.END, f"[{q.marks} Marks]\n")
            
            if q.qtype == "MCQ":
                for j, opt in enumerate(q.options):
                    letter = chr(ord('a') + j)
                    self.preview_text.insert(tk.END, f"   {letter}) {opt}\n")
            # display inline images (if present); if not found -> skip silently (no tag text)
            imgs = self._extract_image_tags(q.text)
            for im in imgs:
                img_path = self._resolve_image_path(im, key)
                if img_path and os.path.isfile(img_path):
                    try:
                        pil = Image.open(img_path)
                        max_w = 320
                        w0, h0 = pil.size
                        scale = min(1.0, max_w / w0)
                        new_w = int(w0 * scale)
                        new_h = int(h0 * scale)
                        pil = pil.resize((new_w, new_h), Image.LANCZOS)
                        tkimg = ImageTk.PhotoImage(pil)
                        self.preview_text.image_create(tk.END, image=tkimg)
                        self.preview_text.insert(tk.END, "\n")
                        self.preview_image_refs[key].append(tkimg)
                    except Exception:
                        # skip silently
                        pass
                else:
                    # skip silently if not found — user asked to remove the tag from PDF; do same here
                    pass
            self.preview_text.insert(tk.END, "\n")
        self.preview_text.config(state=tk.DISABLED)

    def _extract_image_tags(self, text):
        return re.findall(r"\[IMG:([^\]]+)\]", text)

    def _resolve_image_path(self, tag_filename, tab_key):
        tab_info = self.tabs.get(tab_key, {})
        mapping = tab_info.get("images", {}) or {}
        # 1. mapping
        if tag_filename in mapping:
            return mapping[tag_filename]
        # 2. same folder as tab
        tab_path = tab_info.get("path")
        if tab_path:
            candidate = os.path.join(os.path.dirname(tab_path), tag_filename)
            if os.path.isfile(candidate):
                return candidate
        # 3. absolute?
        if os.path.isabs(tag_filename) and os.path.isfile(tag_filename):
            return tag_filename
        # 4. root_dir
        candidate = os.path.join(self.root_dir, tag_filename)
        if os.path.isfile(candidate):
            return candidate
        return None

    # ---------- XML export/open/verify ----------
    def export_active_xml(self):
        key = self.get_active_tab_key()
        if not key:
            messagebox.showwarning("Export XML", "No active tab.")
            return
        default = (self.tabs[key].get("path") and os.path.basename(self.tabs[key]["path"])) or f"{self.tabs[key]['name']}.xml"
        dest = filedialog.asksaveasfilename(title="Export XML", defaultextension=".xml", initialfile=default, filetypes=[("XML Files","*.xml")])
        if not dest:
            return
        try:
            root = ET.Element("quiz")
            ##
            # Header metadata
            meta = ET.SubElement(root, "examinfo")

            for k, v in self.header_info.items():
                node = ET.SubElement(meta, k)
                node.text = v

            # Group sections
            groups_node = ET.SubElement(root, "groups")

            for g in self.tabs[key]["groups"]:
                gnode = ET.SubElement(groups_node, "group")

                ET.SubElement(gnode, "group_name").text = g["group_name"]
                ET.SubElement(gnode, "instruction").text = g["instruction"]
                ET.SubElement(gnode, "marks").text = g["marks"]
            ##
            for q in self.tabs[key]["questions"]:
                qnode = ET.SubElement(root, "question", {"type": app_type_to_moodle(q.qtype)})
                name = ET.SubElement(qnode, "name")
                name_text = ET.SubElement(name, "text")
                name_text.text = (q.text.strip()[:60] or "Question").strip()
                qtext = ET.SubElement(qnode, "questiontext", {"format":"html"})
                qtext_text = ET.SubElement(qtext, "text")
                qtext_text.text = q.text
                d = ET.SubElement(qnode, "defaultgrade")
                d.text = str(q.marks)
                if q.qtype == "MCQ":
                    for i,opt in enumerate(q.options):
                        frac = "100" if (q.correct_index is not None and q.correct_index == i) else "0"
                        an = ET.SubElement(qnode, "answer", {"fraction": frac})
                        an_text = ET.SubElement(an, "text")
                        an_text.text = opt
                elif q.qtype == "SAQ":
                    if q.options:
                        for opt in q.options:
                            an = ET.SubElement(qnode, "answer", {"fraction":"100"})
                            an_text = ET.SubElement(an, "text")
                            an_text.text = opt
                    else:
                        an = ET.SubElement(qnode, "answer", {"fraction":"100"})
                        an_text = ET.SubElement(an, "text")
                        an_text.text = ""
                else:
                    pass
            tree = ET.ElementTree(root)
            tree.write(dest, encoding="utf-8", xml_declaration=True)
            self.tabs[key]["path"] = dest
            self.tabs[key]["name"] = os.path.basename(dest)
            try:
                frame = self.tabs[key]["frame"]
                idx = self.notebook.index(frame)
                self.notebook.tab(idx, text=self.tabs[key]["name"])
            except Exception:
                pass
            self.set_status(f"Exported XML -> {dest}")
            messagebox.showinfo("Export XML", f"Exported {len(self.tabs[key]['questions'])} questions to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Export XML", f"Failed: {e}")

    def open_xml(self):
        p = filedialog.askopenfilename(title="Open XML", filetypes=[("XML Files","*.xml")], initialdir=self.root_dir)
        if not p:
            return
        self.open_file_into_tab(p)

    def verify_active_xml(self):
        key = self.get_active_tab_key()
        if not key:
            messagebox.showwarning("Verify", "No active tab.")
            return
        problems = []
        for i,q in enumerate(self.tabs[key]["questions"], start=1):
            if not q.text.strip():
                problems.append(f"Q{i}: empty text")
            try:
                float(q.marks)
            except Exception:
                problems.append(f"Q{i}: invalid marks")
            if q.qtype == "MCQ" and not any(opt.strip() for opt in q.options):
                problems.append(f"Q{i}: MCQ but no options")
        if problems:
            messagebox.showwarning("Verify", "Problems found:\n" + "\n".join(problems))
        else:
            messagebox.showinfo("Verify", "No problems found.")

    # ---------- PDF generation ----------
    def export_active_pdf(self):
        key = self.get_active_tab_key()
        if not key:
            messagebox.showwarning("Export PDF", "No active tab.")
            return
        default_base = (self.tabs[key].get("path") and os.path.splitext(os.path.basename(self.tabs[key]["path"]))[0]) or self.tabs[key]["name"]
        dest = filedialog.asksaveasfilename(title="Export PDF", defaultextension=".pdf", initialfile=f"{default_base}.pdf", filetypes=[("PDF Files","*.pdf")])
        if not dest:
            return
        try:
            base_path = os.path.dirname(self.tabs[key].get("path") or self.root_dir)
            self._generate_pdf(dest, self.tabs[key]["questions"], base_path=base_path, tab_images=self.tabs[key].get("images", {}))
            self.set_status(f"Exported PDF -> {dest}")
            messagebox.showinfo("Export PDF", f"Exported PDF to:\n{dest}")
        except Exception as e:
            messagebox.showerror("Export PDF", f"Failed: {e}")

    def _generate_pdf(self, outpath, questions, base_path=None, tab_images=None):
        if base_path is None:
            base_path = os.getcwd()
        if tab_images is None:
            tab_images = {}
        c = canvas.Canvas(outpath, pagesize=A4)
        w,h = A4
        margin = 50
        y = h - margin
        c.setFont("Helvetica-Bold", 16)
        #c.drawString(margin, y, "Moodle Question Paper")
        #y -= 28
        c.setFont("Helvetica", 10)
        mcq_count = sum(1 for q in questions if q.qtype=="MCQ")
        saq_count = sum(1 for q in questions if q.qtype=="SAQ")
        long_count = sum(1 for q in questions if q.qtype=="Long")
        #c.drawString(margin, y, f"Counts — MCQ: {mcq_count} | SAQ: {saq_count} | Long: {long_count}")
        #y -= 20
        ##
        # Header info
        if any(self.header_info.values()):

            c.setFont("Helvetica-Bold", 16)
            c.drawCentredString(w/2, y,self.header_info["college"])
            y -= 20

            c.setFont("Helvetica-Bold", 12)
            c.drawCentredString(w/2, y, self.header_info["department"])
            y -= 20

            c.drawString(margin, y, f"Subject: {self.header_info['subject']}")
            

            c.drawRightString(w-margin, y, f"Subject Code: {self.header_info['subject_code']}")
            y -= 20

            c.drawCentredString(w/2, y,self.header_info["exam_name"])
            y -= 25

        

            c.line(margin, y, w-margin, y)
            y -= 20
        ##
        for i, q in enumerate(questions, start=1):
            ##
            key = self.get_active_tab_key()
            groups = sorted(self.tabs.get(key, {}).get("groups", []), key=lambda x: x["start_question"])

            current_group = None

            for idx, g in enumerate(groups):
                start = g["start_question"]
                next_start = groups[idx + 1]["start_question"] if idx + 1 < len(groups) else float("inf")

                if start <= i < next_start:
                    current_group = g
                    break

            if current_group and i == current_group["start_question"]:
                c.setFont("Helvetica-Bold", 13)
                c.drawCentredString(w/2, y, f" {current_group['group_name']} ")
                y -= 15

                c.setFont("Helvetica", 11)
                c.drawString(margin, y, f" {current_group['instruction']}")
                #y -= 15

                c.drawRightString(w-margin, y, f"Marks: {current_group['marks']}")
                y -= 20
            ##
            if y < margin + 120:
                c.showPage()
                y = h - margin
                c.setFont("Helvetica", 10)
            # Strip image tags entirely from textual content (they will be embedded instead)
            text_without_tags = re.sub(r"\[IMG:[^\]]+\]", "", q.text).strip()
            lines = self._split_text_for_pdf(f"{i}. {text_without_tags}", 90)
            for n, ln in enumerate(lines):
                c.drawString(margin, y, ln)
                #
                # Print marks on the right of the FIRST line only
                if n == 0:
                    c.drawRightString(w - margin, y, f"({q.marks})")

                y -= 14

            y -= 6
            #c.drawString(margin, y, f"[{q.marks} marks]")
            #y -= 16
            if q.qtype == "MCQ":
                for j,opt in enumerate(q.options):
                    letter = chr(ord('a') + j)
                    olines = self._split_text_for_pdf(f"   {letter}) {opt}", 90)
                    for ol in olines:
                        c.drawString(margin+12, y, ol)
                        y -= 12
                    y -= 2
            # embed images where present; if not found -> skip silently (no tag text)
            imgs = self._extract_image_tags(q.text)
            for ip in imgs:
                candidate = None
                # mapping (inserted images)
                if tab_images and ip in tab_images:
                    candidate = tab_images[ip]
                if not candidate:
                    candidate = os.path.join(base_path, ip)
                    if not os.path.isfile(candidate):
                        if os.path.isabs(ip) and os.path.isfile(ip):
                            candidate = ip
                        else:
                            candidate = None
                if not candidate and os.path.isfile(ip):
                    candidate = ip
                if candidate and os.path.isfile(candidate):
                    try:
                        img = Image.open(candidate)
                        iw, ih = img.size
                        max_w = w - 2*margin
                        max_h = min(360, h - 2*margin)
                        scale = min(1.0, max_w/iw, max_h/ih)
                        draw_w = iw * scale
                        draw_h = ih * scale
                        if y - draw_h < margin:
                            c.showPage()
                            y = h - margin
                            c.setFont("Helvetica", 10)
                        c.drawInlineImage(candidate, margin, y - draw_h, width=draw_w, height=draw_h)
                        y -= draw_h + 10
                    except Exception:
                        # skip silently
                        pass
                else:
                    # skip silently (user asked to remove tag text)
                    pass
            y -= 6
        c.save()

    def _split_text_for_pdf(self, text, max_chars):
        words = text.split()
        lines = []
        cur = ""
        for w in words:
            if len(cur) + len(w) + (1 if cur else 0) <= max_chars:
                cur = (cur + " " + w).strip()
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
        return lines
    
    ##
    # ---------- Header ----------
    def add_header_info(self):
        self.header_info["college"] = self.college_var.get()
        self.header_info["department"] = self.department_var.get()
        self.header_info["subject"] = self.subject_var.get()
        self.header_info["subject_code"] = self.subject_code_var.get()
        self.header_info["exam_name"] = self.exam_name_var.get()

        self.update_preview()
        self.set_status("Header info added")

    # ---------- Group ----------
    def add_group_section(self):
        group_data = {
            "group_name": self.group_name_var.get(),
            "instruction": self.group_instruction_var.get(),
            "marks": self.group_marks_var.get(),
            "start_question": int(self.group_start_var.get())
        }
        ##
        #self.group_sections.append(group_data)
        key = self.get_active_tab_key()

        if key:
            if "groups" not in self.tabs[key]:
                self.tabs[key]["groups"] = []

            self.tabs[key]["groups"].append(group_data)
        ##
        self.update_preview()

        self.set_status("Group added successfully")
    ##
    # ---------- Toggle Header ----------
    def toggle_header_section(self):
        if self.header_visible:
            self.header_drop.grid_forget()
            self.header_visible = False
        else:
            self.header_drop.grid(row=7, column=0, columnspan=6, sticky="we", pady=5)
            self.header_visible = True

    # ---------- Toggle Group ----------
    def toggle_group_section(self):
        if self.group_visible:
            self.group_drop.grid_forget()
            self.group_visible = False
        else:
            self.group_drop.grid(row=8, column=0, columnspan=6, sticky="we", pady=5)
            self.group_visible = True
    ##
    def set_status(self, text):
        self.status_var.set(text)

# ---------- Run ----------
if __name__ == "__main__":
    root = tk.Tk()
    app = MoodleEditorApp(root)
    root.mainloop()

