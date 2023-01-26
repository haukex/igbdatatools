#!/usr/bin/env python3
import threading
import queue
import hashlib
from pathlib import Path
from enum import Enum
from typing import NamedTuple
import tkinter as tk  # https://tkdocs.com/
from tkinter import ttk, filedialog, messagebox
from errorutils import javaishstacktrace
from more_itertools import partition
from igbitertools import SizedCallbackIterator
from hashedfile import hashes_from_file, sort_hashedfiles, SortingType
from checksum import list_hashable_files, match_hashes, check_hashes, ResultCode, FileResult
from typing import Union

SortingType.fromstr = { 'no sort':SortingType.NO_SORT, 'by line':SortingType.BY_LINE,
    'by hash':SortingType.BY_HASH, 'by file':SortingType.BY_FILE }

window = tk.Tk()
window.report_callback_exception = \
    lambda ty,ex,tb: messagebox.showerror('Error', repr(ex), detail='\n'.join(javaishstacktrace(ex)))
window.title("Checksum Tool")
frm_main = ttk.Frame(window, padding=5, borderwidth=2, relief='ridge')

dirname = tk.StringVar()
def browse_dirname():
    dirname.set( filedialog.askdirectory(title="Choose Directory to Hash", initialdir=dirname.get()) )
filename = tk.StringVar()
rel_path = tk.BooleanVar(value=True)
ign_path = tk.BooleanVar(value=False)
algo = tk.StringVar(value='sha512')
sorting = tk.StringVar(value='no sort')

sty = ttk.Style()
sty.configure('RedFrame.TFrame', background='red')
sty.configure('GreenFrame.TFrame', background='green')

frm_dirname = ttk.Frame(frm_main, padding=5)
lbl_dirname = ttk.Label(frm_dirname, text="Directory")
lbl_dirname.grid(row=0, column=0, sticky="nw")
tb_dirname = ttk.Entry(frm_dirname, textvariable=dirname)
tb_dirname.grid(row=0, column=1, sticky="nwe", padx=5)
btn_dirname = ttk.Button(frm_dirname, text="Browse", command=browse_dirname)
btn_dirname.grid(row=0, column=2, sticky="ne")
frm_dirname.columnconfigure(1, weight=1)
frm_dirname.grid(row=0, column=0, sticky="new")

frm_file = ttk.Frame(frm_main, padding=5)
lbl_file = ttk.Label(frm_file, text="Filename")
lbl_file.grid(row=0, column=0, sticky="nw")
tb_filename = ttk.Entry(frm_file, textvariable=filename)
tb_filename.grid(row=0, column=1, sticky="nwe", padx=(5,0))
frm_file.columnconfigure(1, weight=1)
frm_file.grid(row=1, column=0, sticky="new")

frm_cmds = ttk.Frame(frm_main, padding=5)
btn_writefile = ttk.Button(frm_cmds, text="Generate Hashes and Save Hash File")
btn_writefile.grid(row=0, column=0, sticky="ne", pady=(0,5))
cb_rel_path = ttk.Checkbutton(frm_cmds, text="Relative Pathnames", variable=rel_path)
cb_rel_path.grid(row=0, column=1, sticky="nw", padx=10)
sel_algo = ttk.Combobox(frm_cmds, textvariable=algo, width=7)
sel_algo['values'] = ('sha512','sha384','sha256','sha224','sha1','md5')
sel_algo.state(["readonly"])
sel_algo.bind('<<ComboboxSelected>>', lambda _: sel_algo.selection_clear())
sel_algo.grid(row=0, column=2, sticky="nw", padx=(0,5))
sel_sort = ttk.Combobox(frm_cmds, textvariable=sorting, width=max(len(s) for s in SortingType.fromstr.keys())+1)
sel_sort['values'] = tuple(SortingType.fromstr.keys())
sel_sort.state(["readonly"])
sel_sort.bind('<<ComboboxSelected>>', lambda _: sel_sort.selection_clear())
sel_sort.grid(row=0, column=3, sticky="nw")
btn_readfile = ttk.Button(frm_cmds, text="Load Hash File and Check Hashes")
btn_readfile.grid(row=1, column=0, sticky="ne")
cb_ign_path = ttk.Checkbutton(frm_cmds, text="Ignore Pathnames", variable=ign_path)
cb_ign_path.grid(row=1, column=1, sticky="nw", padx=10)
frm_cmds.grid(row=2, column=0, sticky="nw")

frm_main.columnconfigure("all", weight=1)
frm_main.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

frm_status = ttk.Frame(window, padding=5, borderwidth=2, relief='ridge')
lbl_progbar = ttk.Label(frm_status, text="Idle")
lbl_progbar.grid(row=0, column=0, sticky="ew", padx=5)
progbar = ttk.Progressbar(frm_status, orient=tk.HORIZONTAL, mode='determinate')
progbar.grid(row=1, column=0, sticky="ew", padx=5)
btn_stop = ttk.Button(frm_status, text="Stop")
btn_stop.grid(row=0, column=1, rowspan=2, sticky="e", padx=5)

frm_log = ttk.Frame(frm_status)
txt_log = tk.Text(frm_log, state='disabled', width=80, height=10, wrap='none')
txt_log_ys = ttk.Scrollbar(frm_log, orient='vertical', command=txt_log.yview)
txt_log_xs = ttk.Scrollbar(frm_log, orient='horizontal', command=txt_log.xview)
txt_log['yscrollcommand'] = txt_log_ys.set
txt_log['xscrollcommand'] = txt_log_xs.set
txt_log.grid(row=0, column=0, sticky='nsew')
txt_log_xs.grid(row=1, column=0, sticky='we')
txt_log_ys.grid(row=0, column=1, sticky='ns')
frm_log.grid_columnconfigure(0, weight=1)
frm_log.grid_rowconfigure(0, weight=1)
frm_log.grid(row=2, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)

frm_status.columnconfigure(0, weight=1)
frm_status.rowconfigure(2, weight=1)
frm_status.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

window.columnconfigure("all", weight=1)
window.rowconfigure(1, weight=1)
window.update()  # so we can get the current size and set min size:
window.minsize(window.winfo_width(), window.winfo_height())

def log_msg(msg):
    txt_log['state'] = 'normal'
    txt_log.insert(tk.END, msg + "\n")
    txt_log.see(tk.END)
    txt_log['state'] = 'disabled'

def log_clear():
    txt_log['state'] = 'normal'
    txt_log.delete('1.0', tk.END)
    txt_log['state'] = 'disabled'

def check_dirname() -> bool:
    if not dirname.get():
        browse_dirname()
        if not dirname.get(): return False
    d = Path(dirname.get())
    if not d.exists():
        messagebox.showerror("Directory doesn't exist",f"Directory doesn't exist",detail=str(d))
        return False
    if not d.is_dir():
        messagebox.showerror("Not a directory",f"Not a directory",detail=str(d))
        return False
    return True

def lock_gui(lock :bool):
    st = ["disabled" if lock else "!disabled"]
    tb_dirname.state(st)
    tb_filename.state(st)
    btn_dirname.state(st)
    btn_readfile.state(st)
    btn_writefile.state(st)
    cb_rel_path.state(st)
    cb_ign_path.state(st)
    sel_algo.state(["readonly"]+st)
    sel_sort.state(["readonly"]+st)
    btn_stop.state(["!disabled" if lock else "disabled"])

class ShortMsg(Enum):
    BEGIN = 0
    PROG = 1
    MSG = 2
    FINISHGOOD = 3
    FINISHBAD = 4
    FATAL = 5

class MyMessage(NamedTuple):
    sm :ShortMsg
    prg :float = 0  # 0.0 to 1.0
    msg :str = None

QUEUE_EVENT_NAME = '<<MyProgUpdate>>'
the_queue = queue.SimpleQueue()
def queue_message(item :MyMessage):
    the_queue.put(item)
    window.event_generate(QUEUE_EVENT_NAME, when="tail")

def progupd(_evt :tk.Event):
    while True:
        try: mm :MyMessage = the_queue.get_nowait()
        except queue.Empty: return
        if mm.sm == ShortMsg.BEGIN:
            log_clear()
            frm_status['style'] = 'TFrame'
            progbar['mode'] = 'indeterminate'
            progbar['value'] = 0.0
            lbl_progbar['text'] = "Listing files & loading hashes..."
            progbar.start()
            if mm.msg: log_msg(mm.msg)
        elif mm.sm == ShortMsg.PROG:
            if mm.prg:
                if str(progbar['mode'])=='indeterminate':
                    progbar.stop()
                    progbar['mode'] = 'determinate'
                    lbl_progbar['text'] = "Calculating hashes..."
                progbar['value'] = mm.prg*100.0
            if mm.msg: log_msg(mm.msg)
        elif mm.sm == ShortMsg.MSG:
            log_msg(mm.msg)
        elif mm.sm in (ShortMsg.FINISHGOOD, ShortMsg.FINISHBAD, ShortMsg.FATAL):
            progbar.stop()
            progbar['mode'] = 'determinate'
            progbar['value'] = 100.0
            lbl_progbar['text'] = "Done. Idle"
            if mm.sm == ShortMsg.FATAL:
                messagebox.showerror("Thread Error","Error in Thread",detail=mm.msg)
            elif mm.msg: log_msg(mm.msg)
            frm_status['style'] = 'GreenFrame.TFrame' if mm.sm == ShortMsg.FINISHGOOD else 'RedFrame.TFrame'
            lock_gui(False)
        else: raise RuntimeError(repr(mm))

def _thr_excepthook(args):
    if isinstance(args.exc_value, InterruptedError):
        queue_message(MyMessage(ShortMsg.MSG, msg="ERROR: Interrupted"))
    else:
        queue_message(MyMessage(ShortMsg.FATAL, msg="\n".join(javaishstacktrace(args.exc_value))))
threading.excepthook = _thr_excepthook

class MyWorkThread(threading.Thread):
    current_thread_lock = threading.Lock()
    current_thread :Union['MyWorkThread', None] = None
    def __init__(self):
        super().__init__()
        self.int_flag = threading.Event()
        self.filename = filename.get()
        self.dirname = dirname.get()
        self.relpath = rel_path.get()
        self.ignpath = ign_path.get()
        self.algo = getattr(hashlib, algo.get())
        self.sorting = SortingType.fromstr[sorting.get()]
        # Possible To-Do for Later: For now, the only way to cancel a running operation is to close the GUI:
        self.daemon = True
    def run(self):
        with MyWorkThread.current_thread_lock:
            if MyWorkThread.current_thread: raise RuntimeError("current_thread was already set")
            MyWorkThread.current_thread = self
        rv = False
        try:
            queue_message(MyMessage(ShortMsg.BEGIN))
            rv = self.my_run()
        finally:
            with MyWorkThread.current_thread_lock:
                if not MyWorkThread.current_thread: raise RuntimeError("current_thread not set")
                MyWorkThread.current_thread = None
            queue_message(MyMessage( ShortMsg.FINISHGOOD if rv else ShortMsg.FINISHBAD ))
    def my_run(self) -> bool:
        raise NotImplementedError("this is an abstract method, you must implement it")
    @staticmethod
    def interrupt():
        with MyWorkThread.current_thread_lock:
            if MyWorkThread.current_thread:
                MyWorkThread.current_thread.int_flag.set()

class GenHashesThread(MyWorkThread):
    def my_run(self) -> bool:
        queue_message(MyMessage(ShortMsg.MSG, msg=f"Generating hashes for {self.dirname}..."))
        # get file list
        thefiles = list(list_hashable_files(self.dirname))
        # generator for hashing
        hashes = ( fr.hash_me(algo=self.algo).hsh for fr in thefiles if fr.code != ResultCode.SKIP )
        filecnt = sum( 1 for fr in thefiles if fr.code != ResultCode.SKIP )
        # wrap in generator that sets the filename as desired
        hashes = ( hf.setfn( ( Path(hf.fn).relative_to(self.dirname) if self.relpath else Path(hf.fn) ).as_posix() ) for hf in hashes )
        # wrap in progress callback
        def progcb(i,_):
            if self.int_flag.is_set(): raise InterruptedError()
            queue_message(MyMessage(ShortMsg.PROG, prg=(i+1)/filecnt))
        hashes = SizedCallbackIterator( it=hashes, length=filecnt, strict=True, callback=progcb )
        # wrap in sorting generator
        hashes = sort_hashedfiles(hashes, self.sorting)
        # actually do the hashing
        count = 0
        with open(self.filename, "w", newline='\n') as fh:
            for hf in hashes:
                print(hf.to_line(), file=fh, flush=self.sorting==SortingType.NO_SORT)
                count += 1
        assert count==filecnt
        queue_message(MyMessage(ShortMsg.MSG, msg=f"Done, wrote {count} hashes to {self.filename}"))
        return True

class CheckHashesThread(MyWorkThread):
    def my_run(self) -> bool:
        def relfrfn(tfr :FileResult):  # just for nicer output
            return tfr.fn.relative_to(self.dirname) if tfr.fn.is_relative_to(self.dirname) else tfr.fn
        count = 0
        errors = 0
        # generator to match hash list from file against the files in the filesystem
        matched = match_hashes(sumsrc=hashes_from_file(self.filename), paths=self.dirname, ignorepath=self.ignpath)
        # split output into two iterators, only `needsvalid` needs the progress bar
        noneed, needsvalid = partition(lambda _: _.code == ResultCode.NEEDSVALIDATE, matched)
        # first process the results where we don't need to go out to the filesystem
        for fr in check_hashes(noneed):  # check_hashes not really needed here, but just for consistency...
            assert fr.code not in (ResultCode.NONE,ResultCode.NEEDSVALIDATE,ResultCode.SUMOK,ResultCode.SUMMISMATCH)
            count += 1
            if fr.code!=ResultCode.SKIP:
                errors += 1
                queue_message(MyMessage(ShortMsg.MSG, msg=f"{relfrfn(fr)}: {fr.msg}"))
        if self.int_flag.is_set(): raise InterruptedError()
        # now work on the files that need validation
        needsvalid = list(needsvalid)  # because we need the length
        validcnt = len(needsvalid)
        for i, fr in enumerate(check_hashes(needsvalid), start=1):
            assert fr.code in (ResultCode.SUMOK,ResultCode.SUMMISMATCH)
            count += 1
            if self.int_flag.is_set(): raise InterruptedError()
            msg = None
            if fr.code!=ResultCode.SKIP and fr.code!=ResultCode.SUMOK:
                errors += 1
                msg=f"{relfrfn(fr)}: {fr.msg}"
            queue_message(MyMessage(ShortMsg.PROG, prg=i/validcnt, msg=msg))
        queue_message(MyMessage(ShortMsg.MSG,
            msg=f"ERROR: There were {errors} errors out of {count} results"
                if errors else f"Done, all {count} results OK"))
        return not errors

def cmd_gen_save():
    if not check_dirname(): return
    def getnewfn() -> bool:
        fn = filedialog.asksaveasfilename(title="Hash File to Save As", initialfile=filename.get())
        if fn:
            filename.set(fn)
            return True
        return False
    if not filename.get():
        if not getnewfn(): return
    elif Path(filename.get()).exists():
        if not messagebox.askyesno(icon="warning",
                message=f"File {filename.get()!r} already exists.\nDo you want to overwrite it?"):
            if not getnewfn(): return
    lock_gui(True)
    GenHashesThread().start()

def cmd_load_validate():
    if not check_dirname(): return
    if not filename.get():
        fn = filedialog.askopenfilename(title="Hash File to Load", initialfile=filename.get())
        if fn: filename.set(fn)
        else: return
    lock_gui(True)
    CheckHashesThread().start()

window.bind(QUEUE_EVENT_NAME, progupd)
btn_writefile['command'] = cmd_gen_save
btn_readfile['command'] = cmd_load_validate
btn_stop['command'] = MyWorkThread.interrupt
lock_gui(False)

window.mainloop()
