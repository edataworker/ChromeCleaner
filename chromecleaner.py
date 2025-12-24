import os
import sys

# Tcl/Tk path fix for PyInstaller
if getattr(sys, 'frozen', False):
    base = sys._MEIPASS
    os.environ['TCL_LIBRARY'] = os.path.join(base, '_tcl_data')
    os.environ['TK_LIBRARY'] = os.path.join(base, '_tk_data')
    print(f"TCL_LIBRARY set to: {os.environ['TCL_LIBRARY']}")

import sqlite3
import shutil
import json
import struct
import subprocess
import time
import signal
import tempfile
import datetime
import traceback
import webbrowser
from pathlib import Path

def fix_tkinter_flattened_structure():
    """Fix for PyInstaller's flattened Tcl/Tk structure"""
    
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        
        print(f"=== FIXING FLATTENED TKINTER STRUCTURE ===")
        
        tcl_data_path = os.path.join(base_path, '_tcl_data')
        tk_data_path = os.path.join(base_path, '_tk_data')
        
        expected_tcl_path = os.path.join(base_path, 'tcl', 'tcl8.6')
        expected_tk_path = os.path.join(base_path, 'tk', 'tk8.6')
        
        if os.path.exists(tcl_data_path) and not os.path.exists(expected_tcl_path):
            print(f"Creating tcl/tcl8.6 structure...")
            try:
                # Create directory
                os.makedirs(expected_tcl_path, exist_ok=True)
                
                # Copy ALL files from _tcl_data to tcl/tcl8.6
                for item in os.listdir(tcl_data_path):
                    src = os.path.join(tcl_data_path, item)
                    dst = os.path.join(expected_tcl_path, item)
                    
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                
                print(f"✓ Created tcl/tcl8.6 with {len(os.listdir(tcl_data_path))} items")
            except Exception as e:
                print(f"✗ Error creating structure: {e}")
                try:
                    if hasattr(os, 'symlink'):
                        os.symlink(tcl_data_path, expected_tcl_path, target_is_directory=True)
                        print(f"✓ Created symlink tcl/tcl8.6 -> _tcl_data")
                except:
                    pass
        
        if os.path.exists(tk_data_path) and not os.path.exists(expected_tk_path):
            print(f"Creating tk/tk8.6 structure...")
            try:
                os.makedirs(expected_tk_path, exist_ok=True)
                for item in os.listdir(tk_data_path):
                    src = os.path.join(tk_data_path, item)
                    dst = os.path.join(expected_tk_path, item)
                    
                    if os.path.isdir(src):
                        shutil.copytree(src, dst, dirs_exist_ok=True)
                    else:
                        shutil.copy2(src, dst)
                
                print(f"✓ Created tk/tk8.6 with {len(os.listdir(tk_data_path))} items")
            except Exception as e:
                print(f"✗ Error creating tk structure: {e}")
        
        if os.path.exists(expected_tcl_path):
            os.environ['TCL_LIBRARY'] = expected_tcl_path
            print(f"Set TCL_LIBRARY to: {expected_tcl_path}")
        elif os.path.exists(tcl_data_path):
            os.environ['TCL_LIBRARY'] = tcl_data_path
            print(f"Set TCL_LIBRARY to: {tcl_data_path}")
        
        if os.path.exists(expected_tk_path):
            os.environ['TK_LIBRARY'] = expected_tk_path
            print(f"Set TK_LIBRARY to: {expected_tk_path}")
        elif os.path.exists(tk_data_path):
            os.environ['TK_LIBRARY'] = tk_data_path
            print(f"Set TK_LIBRARY to: {tk_data_path}")
        
        if 'TCL_LIBRARY' in os.environ:
            init_path = os.path.join(os.environ['TCL_LIBRARY'], 'init.tcl')
            print(f"init.tcl exists at TCL_LIBRARY: {os.path.exists(init_path)}")

fix_tkinter_flattened_structure()

try:
    import tkinter as tk
    from tkinter import messagebox, Listbox, Scrollbar, END, font, ttk
    import tkinter.scrolledtext as scrolledtext
except ImportError as e:
    print(f"✗ Cannot import tkinter: {e}")
    sys.exit(1)
except RuntimeError as e:
    print(f"✗ Tkinter runtime error: {e}")
    
    print("\nTrying manual Tcl load...")
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        
        import ctypes
        tcl_dll_path = os.path.join(base_path, 'tcl86t.dll')
        tk_dll_path = os.path.join(base_path, 'tk86t.dll')
        
        if os.path.exists(tcl_dll_path):
            print(f"Loading Tcl DLL: {tcl_dll_path}")
            tcl_dll = ctypes.CDLL(tcl_dll_path)
            
            
            os.environ['TCL_LIBRARY'] = os.path.join(base_path, '_tcl_data')
            os.environ['TK_LIBRARY'] = os.path.join(base_path, '_tk_data')
            
            try:
                import tkinter as tk
                from tkinter import messagebox, Listbox, Scrollbar, END, font, ttk
                import tkinter.scrolledtext as scrolledtext
                print("✓ Manual load succeeded!")
            except:
                print("✗ Manual load failed")
                sys.exit(1)
    
    sys.exit(1)

# ============ GLOBAL PATHS & LOGGING ============
CHROME_PROFILE = Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Default'
COOKIES_DB = CHROME_PROFILE / 'Network' / 'Cookies'
LOCAL_STORAGE_PATH = CHROME_PROFILE / 'Local Storage' / 'leveldb'
SESSION_STORAGE_PATH = CHROME_PROFILE / 'Session Storage' / 'leveldb'
INDEXEDDB_PATH = CHROME_PROFILE / 'Indexed DB'
CACHESTORAGE_PATH = CHROME_PROFILE / 'Service Worker' / 'CacheStorage'
SCRIPTCACHE_PATH = CHROME_PROFILE / 'Service Worker' / 'ScriptCache'

# Logging setup
LOG_DIR = Path.home() / 'Documents' / 'ChromeCleaner_Logs'
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f'deletion_log_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.txt'

def setup_logging():
    """Setup logging directory and initial log entry"""
    try:
        with open(LOG_FILE, 'w', encoding='utf-8') as f:
            f.write(f"=== Chrome Site Data Cleaner Log ===\n")
            f.write(f"Timestamp: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Profile: {CHROME_PROFILE}\n")
            f.write(f"App Version: 1.0\n")
            f.write(f"{'='*50}\n\n")
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")

def log_deletion(site, deletion_type, status, details=""):
    """Log a deletion attempt"""
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            f.write(f"[{timestamp}] {deletion_type:<15} {site:<40} {status:<10} {details}\n")
    except Exception as e:
        print(f"Warning: Could not write to log: {e}")

def create_backup():
    """Create a backup of Chrome profile"""
    try:
        backup_dir = LOG_DIR / f'backup_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}'
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy critical files
        files_to_backup = [
            COOKIES_DB,
            LOCAL_STORAGE_PATH.parent if LOCAL_STORAGE_PATH.exists() else None,
            SESSION_STORAGE_PATH.parent if SESSION_STORAGE_PATH.exists() else None,
        ]
        
        backup_count = 0
        for file_path in files_to_backup:
            if file_path and file_path.exists():
                dest = backup_dir / file_path.name
                if file_path.is_file():
                    shutil.copy2(file_path, dest)
                    backup_count += 1
                elif file_path.is_dir():
                    shutil.copytree(file_path, dest, dirs_exist_ok=True)
                    backup_count += 1
        
        # Create backup info file
        backup_info = backup_dir / 'backup_info.txt'
        with open(backup_info, 'w', encoding='utf-8') as f:
            f.write(f"Backup created: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Original profile: {CHROME_PROFILE}\n")
            f.write(f"Files backed up: {backup_count}\n")
            f.write(f"To restore: Copy these files back to their original locations\n")
            f.write(f"WARNING: Chrome must be completely closed during restoration\n")
        
        return backup_dir, backup_count
    except Exception as e:
        print(f"Backup creation failed: {e}")
        return None, 0

# ============ CHROME PROCESS MANAGEMENT ============
def is_chrome_running():
    """Check if Chrome is running on Windows"""
    try:
        result = subprocess.run(
            ['tasklist', '/FI', 'IMAGENAME eq chrome.exe', '/FI', 'STATUS eq running'], 
            capture_output=True, 
            text=True, 
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        lines = result.stdout.strip().split('\n')
        chrome_count = 0
        for line in lines:
            if 'chrome.exe' in line.lower() and 'k' in line.split()[-2].lower():
                chrome_count += 1
        
        if chrome_count > 0:
            return True
        
        try:
            result = subprocess.run(
                ['wmic', 'process', 'where', "name='chrome.exe'", 'get', 'processid'], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW
            )
            lines = result.stdout.strip().split('\n')
            process_ids = [line.strip() for line in lines if line.strip().isdigit()]
            return len(process_ids) > 0
        except:
            pass
            
        return False
        
    except Exception as e:
        print(f"Error checking Chrome process: {e}")
        return True

def kill_chrome_processes():
    """Force kill all Chrome processes"""
    try:
        print("\n=== ATTEMPTING TO KILL CHROME ===")
        
        killed_count = 0
        
        # Method 1: Taskkill
        try:
            result = subprocess.run(
                ['taskkill', '/F', '/IM', 'chrome.exe', '/T'], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=10
            )
            
            if 'SUCCESS' in result.stdout or 'terminated' in result.stdout.lower():
                lines = result.stdout.split('\n')
                for line in lines:
                    if 'terminated' in line.lower():
                        parts = line.split()
                        for part in parts:
                            if part.isdigit():
                                killed_count += 1
                                break
            
        except Exception as e:
            print(f"Taskkill error: {e}")
        
        time.sleep(2)
        
        # Method 2: PowerShell
        try:
            ps_script = """
            $chromeProcesses = Get-Process -Name chrome -ErrorAction SilentlyContinue
            if ($chromeProcesses) {
                $chromeProcesses | Stop-Process -Force
                return $chromeProcesses.Count
            }
            return 0
            """
            
            result = subprocess.run(
                ['powershell', '-Command', ps_script], 
                capture_output=True, 
                text=True, 
                creationflags=subprocess.CREATE_NO_WINDOW,
                timeout=15
            )
            
            if result.returncode == 0:
                import re
                match = re.search(r'(\d+)', result.stdout)
                if match:
                    ps_killed = int(match.group(1))
                    killed_count += ps_killed
            
        except Exception as e:
            print(f"PowerShell error: {e}")
        
        # Final check
        time.sleep(2)
        still_running = is_chrome_running()
        
        return killed_count, not still_running
            
    except Exception as e:
        print(f"Error in kill_chrome_processes: {e}")
        return 0, False

# ============ DATA MANAGEMENT FUNCTIONS ============
def get_unique_sites():
    """Get unique sites from cookies database"""
    global COOKIES_DB
    
    if not COOKIES_DB.exists():
        default_paths = [
            CHROME_PROFILE / 'Cookies',
            CHROME_PROFILE / 'Network' / 'Cookies',
            Path.home() / 'AppData' / 'Local' / 'Google' / 'Chrome' / 'User Data' / 'Default' / 'Cookies',
        ]
        
        for path in default_paths:
            if path.exists():
                COOKIES_DB = path
                print(f"Found cookies database at: {path}")
                break
        else:
            raise FileNotFoundError(f"Cookies DB not found\nEnsure Chrome is closed and path is correct.")
    
    try:
        temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        temp_db.close()
        
        shutil.copy2(COOKIES_DB, temp_db.name)
        
        conn = sqlite3.connect(temp_db.name)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cookies'")
        if not cursor.fetchone():
            conn.close()
            os.unlink(temp_db.name)
            raise Exception("Cookies table not found in database")
        
        cursor.execute("SELECT DISTINCT host_key FROM cookies WHERE host_key IS NOT NULL AND host_key != ''")
        sites = []
        for row in cursor.fetchall():
            host = row[0]
            if host:
                host = host.lstrip('.')
                if host and host not in sites:
                    sites.append(host)
        
        conn.close()
        os.unlink(temp_db.name)
        
        return sorted(sites)
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            raise Exception("Chrome database is locked. Please close Chrome completely.")
        raise Exception(f"Database error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to read cookies: {str(e)}")

def delete_cookies_for_site(site):
    """Delete cookies for a specific site with comprehensive patterns"""
    try:
        conn = sqlite3.connect(str(COOKIES_DB))
        cursor = conn.cursor()
        
        patterns = [
            f'{site}',
            f'.{site}',
            f'www.{site}',
            f'm.{site}',
            f'mobile.{site}',
            f'api.{site}',
            f'%.{site}',
            f'%.{site}.',
            f'{site}.'
        ]
        
        deleted_count = 0
        for pattern in patterns:
            cursor.execute("DELETE FROM cookies WHERE host_key LIKE ?", (pattern,))
            deleted_count += cursor.rowcount
        
        conn.commit()
        conn.close()
        
        log_deletion(site, "COOKIES", "SUCCESS" if deleted_count > 0 else "NONE", f"{deleted_count} deleted")
        return deleted_count
        
    except Exception as e:
        log_deletion(site, "COOKIES", "ERROR", str(e))
        print(f"Error deleting cookies for {site}: {e}")
        return 0

def delete_site_data_folders(site):
    """Delete site data from various Chrome storage folders"""
    deleted_items = []
    site_lower = site.lower()
    
    storage_paths = [
        (LOCAL_STORAGE_PATH, "Local Storage"),
        (SESSION_STORAGE_PATH, "Session Storage"),
        (INDEXEDDB_PATH, "IndexedDB"),
        (CACHESTORAGE_PATH, "CacheStorage"),
        (SCRIPTCACHE_PATH, "ScriptCache"),
    ]
    
    for path_obj, path_name in storage_paths:
        if not path_obj.exists():
            continue
            
        try:
            if path_obj.is_dir():
                for item in path_obj.iterdir():
                    if site_lower in item.name.lower():
                        try:
                            if item.is_dir():
                                shutil.rmtree(item, ignore_errors=True)
                                deleted_items.append(f"{path_name}: {item.name}")
                            else:
                                item.unlink()
                                deleted_items.append(f"{path_name}: {item.name}")
                        except Exception as e:
                            print(f"  Could not delete {item}: {e}")
            
        except Exception as e:
            print(f"Error processing {path_name} for {site}: {e}")
    
    if deleted_items:
        log_deletion(site, "STORAGE", "SUCCESS", f"{len(deleted_items)} items")
    return deleted_items

# ============ GUI CLASS ============
class SiteManagerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chrome Site Data Cleaner v1.0")
        self.root.geometry("1000x750")
        self.root.minsize(900, 650)
        
        # ============ SET CUSTOM ICON ============
        try:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icon.ico')
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                print(f"✓ Custom icon loaded: {icon_path}")
            else:
                possible_paths = [
                    'icon.ico',
                    '../icon.ico',
                    './assets/icon.ico',
                    os.path.join(os.path.expanduser('~'), 'icon.ico'),
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        self.root.iconbitmap(path)
                        print(f"✓ Custom icon loaded: {path}")
                        break
                else:
                    print("⚠️ Icon file not found, using default")
        except Exception as e:
            print(f"⚠️ Could not load custom icon: {e}")
        # =========================================
        
        setup_logging()
        
        self.first_run = True
        self.setup_styles()
        self.create_gui()
        self.update_chrome_status()
        
        self.root.bind('<F5>', lambda e: self.refresh_list())
        self.root.bind('<Control-a>', lambda e: self.select_all())
        self.root.bind('<Delete>', lambda e: self.initiate_deletion())
        
        self.show_first_run_disclaimer()

    def show_first_run_disclaimer(self):
        """Show safety disclaimer on first run - with checkbox state saving"""
        
        config_file = Path.home() / '.chromecleaner_config.json'
        
        if config_file.exists():
            try:
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    if config.get('skip_disclaimer', False):
                        return
            except:
                pass
        
        disclaimer = tk.Toplevel(self.root)
        disclaimer.title("⚠️ IMPORTANT SAFETY WARNING ⚠️")
        disclaimer.geometry("700x500")
        disclaimer.transient(self.root)
        disclaimer.grab_set()
        
        # Center window
        disclaimer.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (700 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (500 // 2)
        disclaimer.geometry(f"+{x}+{y}")
        
        # Warning label
        warning_label = tk.Label(disclaimer, text="⚠️ USE CAUTIOUSLY ⚠️", 
                                font=("Arial", 14, "bold"), fg='red')
        warning_label.pack(pady=10)
        
        # Disclaimer text
        disclaimer_text = """This tool MODIFIES your Chrome profile data directly.

    🚨 IMPORTANT WARNINGS:
    1. Chrome MUST be closed before deleting data
    2. Data deletion is PERMANENT and CANNOT be undone
    3. Creating a backup is STRONGLY recommended
    4. Incorrect use may corrupt your Chrome profile
    5. You are responsible for any data loss

    ✅ SAFETY RECOMMENDATIONS:
    • Create a backup using the 'Create Backup' button
    • Test with a few non-critical sites first
    • Ensure Chrome is completely closed
    • Read the log files for troubleshooting

    By clicking "I Understand", you acknowledge these risks."""
        
        text_widget = scrolledtext.ScrolledText(disclaimer, wrap=tk.WORD, 
                                            font=("Arial", 10), height=15)
        text_widget.pack(padx=20, pady=10, fill='both', expand=True)
        text_widget.insert('1.0', disclaimer_text)
        text_widget.config(state='disabled')
        
        dont_show_var = tk.BooleanVar(value=False)
        checkbox = tk.Checkbutton(disclaimer, text="Don't show this warning again",
                                variable=dont_show_var, font=("Arial", 9))
        checkbox.pack(pady=5)
        
        # Buttons
        button_frame = tk.Frame(disclaimer)
        button_frame.pack(pady=10)
        
        def on_accept():
            if dont_show_var.get(): 
                try:
                    config = {'skip_disclaimer': True}
                    with open(config_file, 'w') as f:
                        json.dump(config, f)
                    print("Disclaimer setting saved: Won't show again")
                except Exception as e:
                    print(f"Could not save config: {e}")
            
            disclaimer.destroy()
        
        tk.Button(button_frame, text="I Understand & Accept Risks", 
                command=on_accept, bg='red', fg='white',
                font=("Arial", 11, "bold"), padx=20, pady=10).pack(side='left', padx=10)
        
        tk.Button(button_frame, text="Exit Application", 
                command=self.root.quit, bg='gray', fg='white',
                font=("Arial", 11), padx=20, pady=10).pack(side='left', padx=10)
        
        # Print debug info
        print(f"Checkbox initial state: {dont_show_var.get()}")
        print(f"Config file exists: {config_file.exists()}")

    def setup_styles(self):
        """Configure custom styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure("Red.TButton", background="#e74c3c", foreground="white")
        style.configure("Green.TButton", background="#2ecc71", foreground="white")
        style.configure("Blue.TButton", background="#3498db", foreground="white")
        style.configure("Orange.TButton", background="#e67e22", foreground="white")

    def create_gui(self):
        """Create the main GUI"""
        # Header
        header = tk.Frame(self.root, bg='#2c3e50', height=80)
        header.pack(fill='x')
        header.pack_propagate(False)
        
        tk.Label(header, text="Chrome Site Data Cleaner", 
                font=("Arial", 20, "bold"), bg='#2c3e50', fg='white').pack(side='left', padx=25, pady=10)
        
        # Backup button in header
        backup_btn = tk.Button(header, text="💾 Create Backup", 
                              command=self.create_backup_dialog,
                              bg='#3498db', fg='white',
                              font=("Arial", 11, "bold"),
                              padx=15, pady=8)
        backup_btn.pack(side='right', padx=10)
        
        # View logs button
        logs_btn = tk.Button(header, text="📋 View Logs", 
                           command=self.view_logs,
                           bg='#95a5a6', fg='white',
                           font=("Arial", 11),
                           padx=15, pady=8)
        logs_btn.pack(side='right', padx=10)
        
        # ============ DONATION & WEBSITE BUTTONS ============
        def open_donation():
            import webbrowser
            webbrowser.open("https://paypal.me/edataworker")
            try:
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] DONATION_LINK    Opened PayPal donation page\n")
            except:
                pass
        
        def open_website():
            import webbrowser
            webbrowser.open("https://edataworker.github.io/mysite/")
            try:
                with open(LOG_FILE, 'a', encoding='utf-8') as f:
                    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    f.write(f"[{timestamp}] WEBSITE_VISIT    Opened developer website\n")
            except:
                pass
        
        # Donation button
        donate_btn = tk.Button(header, text="❤️ Donate", 
                              command=open_donation,
                              bg='#e74c3c', fg='white',
                              font=("Arial", 11, "bold"),
                              padx=15, pady=8)
        donate_btn.pack(side='right', padx=10)
        
        # Website button
        website_btn = tk.Button(header, text="ℹ️ Website", 
                               command=open_website,
                               bg='#3498db', fg='white',
                               font=("Arial", 11),
                               padx=15, pady=8)
        website_btn.pack(side='right', padx=5)
        
        # Hover effects
        def on_donate_enter(e):
            e.widget.config(bg='#c0392b', cursor='hand2')
        
        def on_donate_leave(e):
            e.widget.config(bg='#e74c3c', cursor='')
        
        def on_website_enter(e):
            e.widget.config(bg='#2980b9', cursor='hand2')
        
        def on_website_leave(e):
            e.widget.config(bg='#3498db', cursor='')
        
        donate_btn.bind("<Enter>", on_donate_enter)
        donate_btn.bind("<Leave>", on_donate_leave)
        website_btn.bind("<Enter>", on_website_enter)
        website_btn.bind("<Leave>", on_website_leave)
        
        # Main container
        main_container = tk.Frame(self.root)
        main_container.pack(fill='both', expand=True, padx=20, pady=15)
        
        # Top control panel
        control_panel = tk.LabelFrame(main_container, text=" Control Panel ", 
                                     font=("Arial", 11, "bold"), padx=10, pady=10)
        control_panel.pack(fill='x', pady=(0, 15))
        
        # Chrome status
        status_frame = tk.Frame(control_panel)
        status_frame.pack(fill='x', pady=5)
        
        self.chrome_status_var = tk.StringVar(value="Checking Chrome status...")
        status_label = tk.Label(status_frame, textvariable=self.chrome_status_var,
                               font=("Arial", 10))
        status_label.pack(side='left')
        
        # Action buttons
        action_frame = tk.Frame(control_panel)
        action_frame.pack(fill='x', pady=10)
        
        self.kill_chrome_btn = tk.Button(action_frame, text="⚠️ Force Close Chrome", 
                                        command=self.kill_chrome_and_refresh,
                                        bg='#e67e22', fg='white',
                                        font=("Arial", 11),
                                        padx=20, pady=8)
        self.kill_chrome_btn.pack(side='left', padx=5)
        
        tk.Button(action_frame, text="🔄 Refresh List", 
                 command=self.refresh_list,
                 bg='#3498db', fg='white',
                 font=("Arial", 11),
                 padx=20, pady=8).pack(side='left', padx=5)
        
        # Search panel
        search_frame = tk.LabelFrame(main_container, text=" Search & Filter ", 
                                    font=("Arial", 11, "bold"), padx=10, pady=10)
        search_frame.pack(fill='x', pady=(0, 15))
        
        tk.Label(search_frame, text="Search:", 
                font=("Arial", 10)).grid(row=0, column=0, padx=(0, 10))
        
        self.search_var = tk.StringVar()
        self.search_var.trace("w", self.update_list)
        search_entry = tk.Entry(search_frame, textvariable=self.search_var, 
                               font=("Arial", 10), width=60)
        search_entry.grid(row=0, column=1, sticky='ew', padx=(0, 20))
        
        self.site_count_var = tk.StringVar(value="Sites: 0")
        tk.Label(search_frame, textvariable=self.site_count_var,
                font=("Arial", 10), fg='#7f8c8d').grid(row=0, column=2)
        
        search_frame.columnconfigure(1, weight=1)
        
        # Sites list
        list_frame = tk.LabelFrame(main_container, text=" Select Sites to Delete ", 
                                  font=("Arial", 11, "bold"), padx=10, pady=10)
        list_frame.pack(fill='both', expand=True, pady=(0, 15))
        
        # Listbox with scrollbars
        list_container = tk.Frame(list_frame)
        list_container.pack(fill='both', expand=True)
        
        self.listbox = Listbox(list_container, selectmode='extended', 
                              font=("Consolas", 9), bg='white')
        
        v_scrollbar = tk.Scrollbar(list_container)
        v_scrollbar.pack(side='right', fill='y')
        
        h_scrollbar = tk.Scrollbar(list_container, orient='horizontal')
        h_scrollbar.pack(side='bottom', fill='x')
        
        self.listbox.config(yscrollcommand=v_scrollbar.set, 
                           xscrollcommand=h_scrollbar.set)
        v_scrollbar.config(command=self.listbox.yview)
        h_scrollbar.config(command=self.listbox.xview)
        
        self.listbox.pack(side='left', fill='both', expand=True)
        
        # Action buttons panel
        action_panel = tk.Frame(main_container)
        action_panel.pack(fill='x', pady=(0, 10))
        
        tk.Button(action_panel, text="✓ Select All", 
                 command=self.select_all,
                 bg='#2ecc71', fg='white',
                 font=("Arial", 11),
                 padx=20, pady=10).pack(side='left', padx=5)
        
        tk.Button(action_panel, text="✗ Deselect All", 
                 command=self.deselect_all,
                 bg='#95a5a6', fg='white',
                 font=("Arial", 11),
                 padx=20, pady=10).pack(side='left', padx=5)
        
        self.delete_btn = tk.Button(action_panel, text="🗑️ Delete Selected", 
                                   command=self.initiate_deletion,
                                   bg='#e67e22', fg='white',
                                   font=("Arial", 12, "bold"),
                                   padx=30, pady=12)
        self.delete_btn.pack(side='left', padx=20)
        
        tk.Button(action_panel, text="Exit", 
                 command=self.root.quit,
                 bg='#34495e', fg='white',
                 font=("Arial", 11),
                 padx=25, pady=10).pack(side='right', padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready - Ensure Chrome is closed before deletion")
        status_bar = tk.Label(self.root, textvariable=self.status_var, 
                             bd=1, relief=tk.SUNKEN, anchor=tk.W,
                             font=("Arial", 9), bg='#ecf0f1', padx=10)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initial load
        self.refresh_list()

    def update_chrome_status(self):
        """Update Chrome running status"""
        if is_chrome_running():
            self.chrome_status_var.set("❌ Chrome is RUNNING - Close it before deletion!")
            self.kill_chrome_btn.config(bg='#e67e22', state='normal')
            self.delete_btn.config(state='normal', 
                                  text="🗑️ Delete Selected (Chrome is running!)")
        else:
            self.chrome_status_var.set("✅ Chrome is CLOSED - Ready for deletion")
            self.kill_chrome_btn.config(bg='#2ecc71', text="✓ Chrome is closed")
            self.delete_btn.config(state='normal', text="🗑️ Delete Selected")
        
        self.root.after(5000, self.update_chrome_status)

    def kill_chrome_and_refresh(self):
        """Kill Chrome processes"""
        if is_chrome_running():
            killed, success = kill_chrome_processes()
            if success:
                messagebox.showinfo("Success", f"Closed {killed} Chrome process(es).")
            else:
                messagebox.showwarning("Warning", 
                    f"Closed {killed} processes but some may remain.\n"
                    "Please check Task Manager.")
        
        self.update_chrome_status()
        self.refresh_list()

    def create_backup_dialog(self):
        """Create backup of Chrome profile"""
        response = messagebox.askyesno(
            "Create Backup",
            "Create a backup of your Chrome profile data?\n\n"
            "This is STRONGLY recommended before deleting any sites.\n"
            "Backup will be saved to Documents/ChromeCleaner_Logs/"
        )
        
        if response:
            backup_dir, count = create_backup()
            if backup_dir:
                messagebox.showinfo("Backup Created", 
                    f"Backup created successfully!\n\n"
                    f"Location: {backup_dir}\n"
                    f"Files backed up: {count}\n\n"
                    f"To restore: Copy files from backup folder to original location.")
                log_deletion("SYSTEM", "BACKUP", "CREATED", f"Backup: {backup_dir}")
            else:
                messagebox.showerror("Backup Failed", "Could not create backup.")

    def view_logs(self):
        """View log files"""
        log_window = tk.Toplevel(self.root)
        log_window.title("Deletion Logs")
        log_window.geometry("800x600")
        
        log_files = list(LOG_DIR.glob("deletion_log_*.txt"))
        log_files.sort(reverse=True)  # Newest first
        
        # File selection
        file_frame = tk.Frame(log_window)
        file_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Label(file_frame, text="Select log file:", 
                font=("Arial", 10)).pack(side='left', padx=(0, 10))
        
        file_var = tk.StringVar()
        if log_files:
            file_var.set(str(log_files[0]))
        
        file_menu = tk.OptionMenu(file_frame, file_var, *[str(f) for f in log_files])
        file_menu.pack(side='left', fill='x', expand=True)
        
        # Log content display
        text_area = scrolledtext.ScrolledText(log_window, wrap=tk.WORD, 
                                             font=("Consolas", 9))
        text_area.pack(fill='both', expand=True, padx=10, pady=(0, 10))
        
        def load_log():
            try:
                with open(file_var.get(), 'r', encoding='utf-8') as f:
                    content = f.read()
                text_area.delete('1.0', tk.END)
                text_area.insert('1.0', content)
            except Exception as e:
                text_area.delete('1.0', tk.END)
                text_area.insert('1.0', f"Error loading log: {e}")
        
        load_log()
        file_var.trace('w', lambda *args: load_log())
        
        # Open folder button
        tk.Button(log_window, text="Open Logs Folder", 
                 command=lambda: os.startfile(LOG_DIR),
                 bg='#3498db', fg='white').pack(pady=10)

    def refresh_list(self):
        """Refresh sites list"""
        try:
            self.status_var.set("Loading sites...")
            self.root.update()
            
            self.sites = get_unique_sites()
            self.update_list()
            
            count = len(self.sites)
            self.site_count_var.set(f"Sites: {count}")
            self.status_var.set(f"Loaded {count} sites")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load sites:\n\n{str(e)}")
            self.status_var.set(f"Error: {str(e)[:50]}...")

    def update_list(self, *args):
        """Update listbox with filtered sites"""
        search_term = self.search_var.get().lower()
        self.listbox.delete(0, END)
        
        if not hasattr(self, 'sites'):
            return
            
        filtered = [site for site in self.sites if search_term in site.lower()]
        
        for site in filtered:
            self.listbox.insert(END, site)

    def select_all(self):
        """Select all sites"""
        if self.listbox.size() > 0:
            self.listbox.select_set(0, END)

    def deselect_all(self):
        """Deselect all sites"""
        self.listbox.select_clear(0, END)

    def initiate_deletion(self):
        """Start the deletion process with confirmation"""
        selected = [self.listbox.get(i) for i in self.listbox.curselection()]
        if not selected:
            messagebox.showwarning("No Selection", "Please select sites to delete.")
            return
        
        # Show final confirmation with countdown
        confirm_window = tk.Toplevel(self.root)
        confirm_window.title("⚠️ FINAL CONFIRMATION ⚠️")
        confirm_window.geometry("700x550")
        confirm_window.transient(self.root)
        confirm_window.grab_set()
        
        # Center window
        confirm_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (700 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (550 // 2)
        confirm_window.geometry(f"+{x}+{y}")
        
        # Warning header
        tk.Label(confirm_window, text="⚠️ FINAL DELETION CONFIRMATION ⚠️", 
                font=("Arial", 14, "bold"), fg='red').pack(pady=10)
        
        # Sites to delete
        sites_text = tk.Text(confirm_window, height=10, width=70, 
                            font=("Consolas", 9), wrap=tk.WORD)
        sites_text.pack(padx=20, pady=10, fill='both', expand=True)
        
        sites_list = "\n".join([f"  • {site}" for site in selected[:50]])
        if len(selected) > 50:
            sites_list += f"\n  ... and {len(selected) - 50} more sites"
        
        sites_text.insert('1.0', f"Sites to delete ({len(selected)} total):\n\n{sites_list}")
        sites_text.config(state='disabled')
        
        # Warning text
        warning_frame = tk.Frame(confirm_window)
        warning_frame.pack(fill='x', padx=20, pady=10)
        
        warning_text = """🚨 YOU ARE ABOUT TO PERMANENTLY DELETE DATA FOR THE ABOVE SITES!

This action:
• CANNOT be undone
• Will delete ALL cookies and site data
• May log you out of websites
• May remove saved preferences

✅ Before proceeding:
1. Ensure Chrome is completely closed
2. You have created a backup
3. You have tested with a few sites first"""
        
        warning_label = tk.Label(warning_frame, text=warning_text, 
                                font=("Arial", 10), justify=tk.LEFT, fg='red')
        warning_label.pack()
        
        # Countdown and buttons
        button_frame = tk.Frame(confirm_window)
        button_frame.pack(pady=20)
        
        self.countdown_var = tk.StringVar(value="Confirm (10)")
        confirm_btn = tk.Button(button_frame, textvariable=self.countdown_var,
                               command=lambda: self.perform_deletion(selected, confirm_window),
                               bg='red', fg='white',
                               font=("Arial", 12, "bold"),
                               state='disabled', padx=30, pady=10)
        confirm_btn.pack(side='left', padx=10)
        
        cancel_btn = tk.Button(button_frame, text="Cancel", 
                              command=confirm_window.destroy,
                              bg='gray', fg='white',
                              font=("Arial", 11),
                              padx=30, pady=10)
        cancel_btn.pack(side='left', padx=10)
        
        # Start countdown
        self.countdown_seconds = 5
        self.confirm_button = confirm_btn
        self.update_countdown(confirm_window)

    def update_countdown(self, window):
        """Update the countdown timer"""
        if self.countdown_seconds > 0:
            self.countdown_var.set(f"Confirm ({self.countdown_seconds})")
            self.countdown_seconds -= 1
            window.after(1000, lambda: self.update_countdown(window))
        else:
            self.countdown_var.set("CONFIRM DELETE")
            self.confirm_button.config(state='normal')

    def perform_deletion(self, sites, confirm_window):
        """Perform the actual deletion"""
        confirm_window.destroy()
        
        if is_chrome_running():
            response = messagebox.askyesno(
                "Chrome Still Running!",
                "Chrome appears to be running!\n\n"
                "This will likely FAIL or CORRUPT data!\n"
                "Do you want to force close Chrome now?"
            )
            if response:
                self.kill_chrome_and_refresh()
                if is_chrome_running():
                    if not messagebox.askyesno("Continue Anyway?", 
                        "Chrome is still running. Continue anyway?\n(This may fail)"):
                        return
            else:
                if not messagebox.askyesno("Continue Anyway?", 
                    "Continue with Chrome running?\n(This may fail or corrupt data)"):
                    return
        
        # Create progress window
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Deleting Site Data")
        progress_window.geometry("600x400")
        progress_window.transient(self.root)
        progress_window.grab_set()
        
        # Center window
        progress_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (600 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (400 // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        # Progress UI
        tk.Label(progress_window, text="Deleting Site Data...", 
                font=("Arial", 12, "bold")).pack(pady=10)
        
        self.current_site_var = tk.StringVar(value="")
        tk.Label(progress_window, textvariable=self.current_site_var,
                font=("Arial", 10)).pack(pady=5)
        
        self.progress_var = tk.StringVar(value="0% Complete")
        tk.Label(progress_window, textvariable=self.progress_var,
                font=("Arial", 10)).pack(pady=5)
        
        self.progress_bar = ttk.Progressbar(progress_window, mode='determinate', length=500)
        self.progress_bar.pack(pady=20, padx=20)
        
        # Log display
        log_frame = tk.Frame(progress_window)
        log_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10, 
                                                 font=("Consolas", 8))
        self.log_text.pack(fill='both', expand=True)
        self.log_text.insert('1.0', "Deletion started...\n")
        self.log_text.see(tk.END)
        
        progress_window.update()
        
        self.root.after(100, lambda: self.execute_deletion(sites, progress_window))

    def execute_deletion(self, sites, progress_window):
        """Execute the deletion process"""
        total_sites = len(sites)
        success_count = 0
        error_count = 0
        
        try:
            for i, site in enumerate(sites, 1):
                # Update progress
                progress = (i-1) / total_sites * 100
                self.current_site_var.set(f"Processing: {site} ({i}/{total_sites})")
                self.progress_var.set(f"{int(progress)}% Complete")
                self.progress_bar['value'] = progress
                
                # Log start
                self.log_text.insert(tk.END, f"\n[{i}/{total_sites}] {site}: ")
                self.log_text.see(tk.END)
                progress_window.update()
                
                try:
                    # Delete cookies
                    cookies_deleted = delete_cookies_for_site(site)
                    
                    # Delete other data
                    other_deleted = delete_site_data_folders(site)
                    
                    # Log result
                    if cookies_deleted > 0 or other_deleted:
                        self.log_text.insert(tk.END, 
                            f"✓ {cookies_deleted} cookies, {len(other_deleted)} storage items\n")
                        success_count += 1
                    else:
                        self.log_text.insert(tk.END, "✓ No data found\n")
                        success_count += 1
                    
                except Exception as e:
                    self.log_text.insert(tk.END, f"✗ Error: {str(e)[:50]}\n")
                    error_count += 1
                    log_deletion(site, "ALL", "ERROR", str(e))
                
                self.log_text.see(tk.END)
                progress_window.update()
            
            # Final update
            self.progress_bar['value'] = 100
            self.progress_var.set("100% Complete")
            self.current_site_var.set("Deletion complete!")
            
            # Add summary to log
            summary = f"\n{'='*50}\n"
            summary += f"DELETION SUMMARY\n"
            summary += f"Total sites processed: {total_sites}\n"
            summary += f"Successfully deleted: {success_count}\n"
            summary += f"Errors: {error_count}\n"
            summary += f"Log file: {LOG_FILE}\n"
            summary += f"{'='*50}"
            
            self.log_text.insert(tk.END, summary)
            self.log_text.see(tk.END)
            
            ok_button = tk.Button(progress_window, text="OK", 
                                command=lambda: self.close_progress_and_refresh(progress_window, success_count, error_count),
                                bg='#2ecc71', fg='white',
                                font=("Arial", 11),
                                padx=20, pady=8)
            ok_button.pack(pady=10)
            
            progress_window.protocol("WM_DELETE_WINDOW", lambda: None)
            
            progress_window.update()
            
        except Exception as e:
            self.log_text.insert(tk.END, f"\n\n{'='*50}\n")
            self.log_text.insert(tk.END, f"FATAL ERROR: {str(e)}\n")
            self.log_text.insert(tk.END, f"Check log file: {LOG_FILE}\n")
            self.log_text.insert(tk.END, f"{'='*50}")
            self.log_text.see(tk.END)
            
            ok_button = tk.Button(progress_window, text="OK", 
                                command=progress_window.destroy,
                                bg='#e67e22', fg='white',
                                font=("Arial", 11),
                                padx=20, pady=8)
            ok_button.pack(pady=10)
            
            log_deletion("SYSTEM", "ALL", "FATAL_ERROR", str(e))
    
    def close_progress_and_refresh(self, progress_window, success_count, error_count):
        """Close progress window and refresh the list"""
        progress_window.destroy()
        
        if error_count == 0:
            self.status_var.set(f"Deleted {success_count} sites successfully")
        else:
            self.status_var.set(f"Deleted {success_count} sites, {error_count} errors")
        
        self.refresh_list()

# ============ MAIN ENTRY POINT ============
if __name__ == "__main__":
    try:
        root = tk.Tk()
        
        try:
            root.iconbitmap(default='icon.ico')
        except:
            pass
        
        # Center window
        window_width = 1000
        window_height = 800
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        root.geometry(f'{window_width}x{window_height}+{center_x}+{center_y}')
        
        app = SiteManagerApp(root)
        root.mainloop()
        
    except Exception as e:
        error_msg = f"Fatal application error:\n\n{str(e)}\n\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}"
        
        try:
            messagebox.showerror("Fatal Error", error_msg[:500] + "...")
        except:
            print(error_msg)