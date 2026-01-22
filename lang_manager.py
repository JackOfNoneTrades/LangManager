import os
import sys
import argparse
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# ----------------------------
# Lang file parsing utilities
# ----------------------------

def parse_lang_file(path):
    lines = []
    entries = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f.readlines():
            raw = line.rstrip("\n")
            if "=" in raw and not raw.strip().startswith("#"):
                key, val = raw.split("=", 1)
                entries[key] = val
                lines.append(("entry", key, val))
            else:
                lines.append(("raw", raw))
    return lines, entries


def write_lang_file(path, lines):
    with open(path, "w", encoding="utf-8") as f:
        for item in lines:
            if item[0] == "raw":
                f.write(item[1] + "\n")
            else:
                f.write(f"{item[1]}={item[2]}\n")


# ----------------------------
# Main application
# ----------------------------

class LangTool:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Minecraft Lang Manager")
        self.root.geometry("900x600")

        # ---- state variables (MUST be before create_ui)
        self.lang_dir = None
        self.lang_files = {}
        self.all_keys = set()
        self.key_sources = {}  # key -> set of file names that contain it

        self.model_file = tk.StringVar()
        self.current_file = tk.StringVar()
        self.add_totranslate = tk.BooleanVar()

        # ---- build UI last
        self.create_ui()

    def create_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=5, pady=5)

        tk.Button(top, text="Select Lang Folder", command=self.select_folder).pack(side="left")
        tk.Button(top, text="Scan All Lang Files", command=self.scan_all).pack(side="left", padx=5)

        tk.Label(top, text="Model lang:").pack(side="left", padx=5)
        self.model_combo = ttk.Combobox(top, textvariable=self.model_file, state="readonly", width=25)
        self.model_combo.pack(side="left")

        tk.Checkbutton(top, text="Add TOTRANSLATE", variable=self.add_totranslate).pack(side="left", padx=5)

        # Apply buttons on a new row
        apply_row = tk.Frame(self.root)
        apply_row.pack(fill="x", padx=5, pady=2)
        tk.Button(apply_row, text="Apply Model to Current", command=self.apply_model).pack(side="left", padx=5)
        tk.Button(apply_row, text="Apply Model to All", command=self.apply_model_to_all).pack(side="left", padx=5)

        mid = tk.Frame(self.root)
        mid.pack(fill="x", padx=5, pady=2)

        tk.Label(mid, text="View lang file:").pack(side="left")
        self.file_combo = ttk.Combobox(mid, textvariable=self.current_file, state="readonly", width=30)
        self.file_combo.pack(side="left", padx=5)
        self.file_combo.bind("<<ComboboxSelected>>", lambda e: self.display_file())

        # Working directory display
        self.dir_label = tk.Label(mid, text="", fg="gray", font=("TkDefaultFont", 8))
        self.dir_label.pack(side="left", padx=10)

        # Status info row (below working directory)
        status_row = tk.Frame(self.root)
        status_row.pack(fill="x", padx=5, pady=2)
        self.files_count_label = tk.Label(status_row, text="Files: 0", fg="gray", font=("TkDefaultFont", 9))
        self.files_count_label.pack(side="left", padx=5)
        self.keys_count_label = tk.Label(status_row, text="Unique keys: 0", fg="gray", font=("TkDefaultFont", 9))
        self.keys_count_label.pack(side="left", padx=5)

        # Text display
        self.text = tk.Text(self.root)
        self.text.pack(fill="both", expand=True, padx=5, pady=5)

        self.text.tag_configure("missing", foreground="red")
        self.text.tag_configure("invalid", foreground="red")

    # ----------------------------
    # Actions
    # ----------------------------

    def load_folder(self, folder):
        """Load lang files from a folder. Can be called from GUI or CLI."""
        if not folder or not os.path.isdir(folder):
            return False

        self.lang_dir = folder
        self.lang_files.clear()

        for fname in os.listdir(folder):
            if fname.endswith(".lang"):
                path = os.path.join(folder, fname)
                self.lang_files[fname] = {
                    "path": path,
                    "lines": [],
                    "entries": {}
                }

        names = sorted(self.lang_files.keys())
        if hasattr(self, 'file_combo'):
            self.file_combo["values"] = names
            self.model_combo["values"] = names
            # Update working directory display
            if hasattr(self, 'dir_label'):
                self.dir_label.config(text=f"Working dir: {self.lang_dir}")

        self.scan_all()
        
        # Update files count label
        if hasattr(self, 'files_count_label'):
            self.files_count_label.config(text=f"Files: {len(names)}")
        
        # Display first file if available (after scanning)
        if hasattr(self, 'file_combo') and names:
            self.current_file.set(names[0])
            self.display_file()
        
        return True

    def select_folder(self):
        folder = filedialog.askdirectory()
        if not folder:
            return

        self.load_folder(folder)

    def scan_all(self):
        if not self.lang_files:
            return

        self.all_keys.clear()
        self.key_sources.clear()

        for fname, data in self.lang_files.items():
            lines, entries = parse_lang_file(data["path"])
            data["lines"] = lines
            data["entries"] = entries
            self.all_keys.update(entries.keys())
            # Track which files contain each key
            for key in entries.keys():
                if key not in self.key_sources:
                    self.key_sources[key] = set()
                self.key_sources[key].add(fname)

        # Update keys count label
        if hasattr(self, 'keys_count_label'):
            self.keys_count_label.config(text=f"Unique keys: {len(self.all_keys)}")
        
        # Refresh displayed file in case it changed
        if hasattr(self, 'root') and self.current_file.get():
            self.display_file()

    def display_file(self):
        name = self.current_file.get()
        if not name:
            return

        if name not in self.lang_files:
            return

        data = self.lang_files[name]
        
        # Ensure file is parsed if not already
        if not data["lines"]:
            lines, entries = parse_lang_file(data["path"])
            data["lines"] = lines
            data["entries"] = entries
        
        self.text.delete("1.0", "end")

        for item in data["lines"]:
            if item[0] == "raw":
                raw_line = item[1]
                # Check if it's a comment (starts with #) or empty
                if raw_line.strip().startswith("#") or not raw_line.strip():
                    self.text.insert("end", raw_line + "\n")
                else:
                    # Invalid raw line (not a comment and not empty)
                    self.text.insert("end", raw_line + "  # INVALID\n", "invalid")
            else:
                self.text.insert("end", f"{item[1]}={item[2]}\n")

        missing = sorted(self.all_keys - set(data["entries"].keys()))
        if missing:
            self.text.insert("end", "\n# Missing entries:\n", "missing")
            for key in missing:
                sources = self.key_sources.get(key, set())
                if sources:
                    source_list = ", ".join(sorted(sources))
                    self.text.insert("end", f"{key}=  # from: {source_list}\n", "missing")
                else:
                    self.text.insert("end", f"{key}=\n", "missing")

    def apply_model_to_file(self, model_name, target_name, add_totranslate=False):
        """Apply model file to target file. Returns True on success."""
        if model_name not in self.lang_files or target_name not in self.lang_files:
            return False

        model = self.lang_files[model_name]
        target = self.lang_files[target_name]

        model_lines = model["lines"]
        model_entries = model["entries"]
        target_entries = target["entries"]
        target_lines = target["lines"]

        new_lines = []

        used_keys = set()
        # Track raw lines from model
        model_raw_lines = set()
        
        # Process model lines in order
        for item in model_lines:
            if item[0] == "raw":
                raw_line = item[1]
                # Only propagate valid raw lines (comments or empty lines)
                # Skip invalid lines (non-comment, non-empty raw lines)
                if raw_line.strip().startswith("#") or not raw_line.strip():
                    model_raw_lines.add(raw_line)
                    new_lines.append(item)
            else:  # entry
                key = item[1]
                if key in target_entries:
                    new_lines.append(("entry", key, target_entries[key]))
                else:
                    val = model_entries[key]
                    if add_totranslate:
                        val += " TOTRANSLATE"
                    new_lines.append(("entry", key, val))
                used_keys.add(key)

        # Add target entries not in model
        for key, val in target_entries.items():
            if key not in used_keys:
                new_lines.append(("entry", key, val))

        # Move target file comments to the bottom (preserve information)
        target_comments = []
        for item in target_lines:
            if item[0] == "raw":
                # Only add comments that aren't already in the model
                if item[1] not in model_raw_lines:
                    target_comments.append(item)
        
        if target_comments:
            new_lines.append(("raw", ""))  # Empty line separator
            new_lines.extend(target_comments)

        write_lang_file(target["path"], new_lines)
        target["lines"], target["entries"] = parse_lang_file(target["path"])
        return True

    def apply_model(self):
        model_name = self.model_file.get()
        target_name = self.current_file.get()

        if not model_name or not target_name:
            return

        if self.apply_model_to_file(model_name, target_name, self.add_totranslate.get()):
            self.display_file()
            messagebox.showinfo("Done", "Model applied successfully.")

    def apply_model_to_all(self):
        model_name = self.model_file.get()

        if not model_name:
            messagebox.showwarning("Warning", "Please select a model file first.")
            return

        if model_name not in self.lang_files:
            messagebox.showerror("Error", "Model file not found.")
            return

        current_name = self.current_file.get()
        count = 0
        for target_name in self.lang_files.keys():
            if target_name != model_name:
                if self.apply_model_to_file(model_name, target_name, self.add_totranslate.get()):
                    count += 1

        # Reload displayed file if it was one of the targets
        if current_name and current_name != model_name:
            self.display_file()

        messagebox.showinfo("Done", f"Model applied to {count} file(s).")


# ----------------------------
# Headless mode
# ----------------------------

def run_headless(folder, model_lang, add_totranslate=False):
    """Run in headless mode without GUI."""
    # Create a minimal tool instance without GUI
    class HeadlessTool:
        def __init__(self):
            self.lang_dir = None
            self.lang_files = {}
            self.all_keys = set()
            self.key_sources = {}
        
        def load_folder(self, folder):
            if not folder or not os.path.isdir(folder):
                return False
            self.lang_dir = folder
            self.lang_files.clear()
            for fname in os.listdir(folder):
                if fname.endswith(".lang"):
                    path = os.path.join(folder, fname)
                    self.lang_files[fname] = {
                        "path": path,
                        "lines": [],
                        "entries": {}
                    }
            self.scan_all()
            return True
        
        def scan_all(self):
            if not self.lang_files:
                return
            self.all_keys.clear()
            self.key_sources.clear()
            for fname, data in self.lang_files.items():
                lines, entries = parse_lang_file(data["path"])
                data["lines"] = lines
                data["entries"] = entries
                self.all_keys.update(entries.keys())
                for key in entries.keys():
                    if key not in self.key_sources:
                        self.key_sources[key] = set()
                    self.key_sources[key].add(fname)
        
        def apply_model_to_file(self, model_name, target_name, add_totranslate=False):
            if model_name not in self.lang_files or target_name not in self.lang_files:
                return False
            model = self.lang_files[model_name]
            target = self.lang_files[target_name]
            model_lines = model["lines"]
            model_entries = model["entries"]
            target_entries = target["entries"]
            target_lines = target["lines"]
            new_lines = []
            used_keys = set()
            # Track raw lines from model
            model_raw_lines = set()
            # Process model lines in order
            for item in model_lines:
                if item[0] == "raw":
                    raw_line = item[1]
                    # Only propagate valid raw lines (comments or empty lines)
                    # Skip invalid lines (non-comment, non-empty raw lines)
                    if raw_line.strip().startswith("#") or not raw_line.strip():
                        model_raw_lines.add(raw_line)
                        new_lines.append(item)
                else:  # entry
                    key = item[1]
                    if key in target_entries:
                        new_lines.append(("entry", key, target_entries[key]))
                    else:
                        val = model_entries[key]
                        if add_totranslate:
                            val += " TOTRANSLATE"
                        new_lines.append(("entry", key, val))
                    used_keys.add(key)
            # Add target entries not in model
            for key, val in target_entries.items():
                if key not in used_keys:
                    new_lines.append(("entry", key, val))
            # Move target file comments to the bottom (preserve information)
            target_comments = []
            for item in target_lines:
                if item[0] == "raw":
                    # Only add comments that aren't already in the model
                    if item[1] not in model_raw_lines:
                        target_comments.append(item)
            
            if target_comments:
                new_lines.append(("raw", ""))  # Empty line separator
                new_lines.extend(target_comments)
            write_lang_file(target["path"], new_lines)
            target["lines"], target["entries"] = parse_lang_file(target["path"])
            return True
    
    tool = HeadlessTool()
    
    if not tool.load_folder(folder):
        print(f"Error: Could not load folder: {folder}")
        return False
    
    if model_lang not in tool.lang_files:
        print(f"Error: Model file '{model_lang}' not found in folder.")
        print(f"Available files: {', '.join(sorted(tool.lang_files.keys()))}")
        return False
    
    count = 0
    for target_name in sorted(tool.lang_files.keys()):
        if target_name != model_lang:
            if tool.apply_model_to_file(model_lang, target_name, add_totranslate):
                print(f"Applied model to: {target_name}")
                count += 1
    
    print(f"\nDone! Applied model to {count} file(s).")
    return True


# ----------------------------
# Run
# ----------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Minecraft Lang Manager")
    parser.add_argument("--folder", type=str, help="Path to folder containing .lang files")
    parser.add_argument("--model", type=str, help="Model language file name (e.g., en_us.lang)")
    parser.add_argument("--apply", action="store_true", help="Apply model to all other files (headless mode)")
    parser.add_argument("--add-totranslate", action="store_true", help="Add 'TOTRANSLATE' suffix to missing translations")
    
    args = parser.parse_args()
    
    if args.apply:
        # Headless mode
        if not args.folder:
            print("Error: --folder is required when using --apply")
            sys.exit(1)
        if not args.model:
            print("Error: --model is required when using --apply")
            sys.exit(1)
        
        success = run_headless(args.folder, args.model, args.add_totranslate)
        sys.exit(0 if success else 1)
    else:
        # GUI mode
        app = LangTool()
        
        # Set add_totranslate checkbox if flag is provided
        if args.add_totranslate:
            app.add_totranslate.set(True)
        
        # If folder is provided, load it
        if args.folder:
            if app.load_folder(args.folder):
                if args.model and args.model in app.lang_files:
                    app.model_file.set(args.model)
                print(f"Loaded {len(app.lang_files)} lang files from {args.folder}")
            else:
                print(f"Warning: Could not load folder: {args.folder}")
        
        app.root.mainloop()


