import tkinter as tk
from tkinter import messagebox, ttk
from tkcalendar import DateEntry
from datetime import datetime, timedelta
import sqlite3
from dotenv import load_dotenv
from email_utils import send_email  # Import from our new email utility module
import threading
import time
import os

import pystray
from PIL import Image, ImageDraw


def decode_recurrence_days(bitmask):
    """
    Convert the recurrence_days integer (bitmask) into a list of weekday strings.
    """
    day_map = {1: "Mon", 2: "Tue", 4: "Wed", 8: "Thu", 16: "Fri", 32: "Sat", 64: "Sun"}
    weekdays = [name for bit, name in day_map.items() if bitmask and (bitmask & bit)]
    return ", ".join(weekdays)

import pystray
from PIL import Image, ImageDraw

load_dotenv()

# Connect to SQLite database and create table if not exists
conn = sqlite3.connect('tasks.db', check_same_thread=False)
cursor = conn.cursor()
# Create table if it doesn't exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks
    (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        course TEXT,
        start TEXT,
        due TEXT,
        status TEXT,
        recurrence_days INTEGER
    )
''')
conn.commit()

# Add reminder_hours column if it doesn't exist
try:
    cursor.execute('ALTER TABLE tasks ADD COLUMN reminder_hours INTEGER DEFAULT 24')
    conn.commit()
except sqlite3.OperationalError:
    # Column already exists, ignore
    pass

# Add reminder_sent column if it doesn't exist
try:
    cursor.execute('ALTER TABLE tasks ADD COLUMN reminder_sent INTEGER DEFAULT 0')
    # Mark all tasks in the past as already reminded
    cursor.execute('''
                   UPDATE tasks
                   SET reminder_sent = 1
                   WHERE reminder_sent IS NULL
                      OR reminder_sent = 0
                       AND datetime(due, '-' || reminder_hours || ' hours') < datetime('now')
                   ''')
    conn.commit()
except sqlite3.OperationalError:
    # Column already exists, ignore
    pass

# --- System Tray Icon Functions ---
def create_image(width, height, color1, color2):
    # Generate an icon image
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        [(width // 3, height // 3), (width * 2 // 3, height * 2 // 3)],
        fill=color2)
    return image

def on_quit(icon, item):
    root.quit()
    icon.stop()

def setup_tray():
    image = create_image(64, 64, "black", "white")
    menu = pystray.Menu(
        pystray.MenuItem("Show Task Manager", lambda icon, item: root.deiconify()),
        pystray.MenuItem("Quit", on_quit)
    )
    tray_icon = pystray.Icon("taskmanager", image, "Task Manager", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

# --- System Tray Icon Functions ---
def create_image(width, height, color1, color2):
    # Generate an icon image
    image = Image.new('RGB', (width, height), color1)
    dc = ImageDraw.Draw(image)
    dc.rectangle(
        [(width // 3, height // 3), (width * 2 // 3, height * 2 // 3)],
        fill=color2)
    return image

def on_quit(icon, item):
    icon.stop()
    root.destroy()

# --- Add function to show window from tray ---
def show_window(icon, item):
    root.deiconify()
    root.lift()
    root.attributes('-topmost', True)
    root.after(100, lambda: root.attributes('-topmost', False))

def setup_tray():
    global tray_icon
    image = create_image(64, 64, "black", "white")
    menu = pystray.Menu(
        pystray.MenuItem("Show Task Manager", show_window),
        pystray.MenuItem("Quit", on_quit)
    )
    tray_icon = pystray.Icon("taskmanager", image, "Task Manager", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

# Main application window
root = tk.Tk()
root.title("Task Manager")
root.geometry("900x700")

# Handler to hide window instead of quitting
def on_close():
    root.withdraw()  # Hide the window instead of closing
root.protocol("WM_DELETE_WINDOW", on_close)

# Handler to hide window instead of quitting
def on_close():
    root.withdraw()  # Hide the window instead of closing
root.protocol("WM_DELETE_WINDOW", on_close)

# Treeview setup
# Treeview to display tasks, now including Class/Course as the second column, but hiding Recurrence column
tree = ttk.Treeview(root, columns=("Name", "Class", "Start", "Due", "Status"), show="headings")
tree.heading("Name", text="Assignment Name")
tree.heading("Class", text="Class")
tree.heading("Start", text="Start Date/Time")
tree.heading("Due", text="Due Date/Time")
tree.heading("Status", text="Status")
tree.pack(fill="both", expand=True)

# Configure tags for background colors
tree.tag_configure("Not Started", background="#EB8673")
tree.tag_configure("In Progress", background="#EDE17B")
tree.tag_configure("Completed", background="#7BED86")
tree.tag_configure("Graded", background="#7BE2ED")

# Load existing tasks from database and print them
# NOTE: Old tasks in DB do not have 'Course' or 'Status'; only show what is available.
cursor.execute('SELECT id, name, course, start, due, status, recurrence_days FROM tasks')
rows = cursor.fetchall()
for task in rows:
    status_tag = task[5] if task[5] else "Not Started"
    tree.insert(
        "",
        tk.END,
        iid=str(task[0]),
        values=(task[1], task[2], task[3], task[4], task[5]),
        tags=(status_tag,)
    )


# Function to open add assignment window
def open_new_window():
    new_window = tk.Toplevel(root)
    new_window.title("Add New Assignment")
    new_window.geometry("800x600")

    tk.Label(new_window, text="Add New Assignment", font=("Arial", 16)).grid(column=0, row=0, columnspan=2, pady=10)
    form_frame = tk.Frame(new_window)
    form_frame.grid(column=0, row=1, padx=20, pady=10)

    tk.Label(form_frame, text="Assignment Name:").grid(column=0, row=0, sticky="w", padx=5, pady=5)
    name_entry = tk.Entry(form_frame, width=40)
    name_entry.grid(column=1, row=0, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Class:").grid(column=0, row=1, sticky="w", padx=5, pady=5)
    classes = [
        "Select Class",
        "Database Design",
        "Computer Organization & Assembly Language",
        "Modern Software Design & Development",
        "Web Application Development",
        "CTC"
    ]
    selected_class = tk.StringVar(value=classes[0])
    tk.OptionMenu(form_frame, selected_class, *classes).grid(column=1, row=1, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Date:").grid(column=0, row=2, sticky="w", padx=5, pady=5)
    start_date = DateEntry(form_frame, width=40)
    start_date.grid(column=1, row=2, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Time (HH:MM AM/PM):").grid(column=0, row=3, sticky="w", padx=5, pady=5)
    start_time_entry = tk.Entry(form_frame, width=40)
    start_time_entry.insert(0, "09:00 AM")
    start_time_entry.grid(column=1, row=3, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Date:").grid(column=0, row=4, sticky="w", padx=5, pady=5)
    due_date = DateEntry(form_frame, width=40)
    due_date.grid(column=1, row=4, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Time (HH:MM AM/PM):").grid(column=0, row=5, sticky="w", padx=5, pady=5)
    due_time_entry = tk.Entry(form_frame, width=40)
    due_time_entry.insert(0, "05:00 PM")
    due_time_entry.grid(column=1, row=5, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Status:").grid(column=0, row=6, sticky="w", padx=5, pady=5)
    status_options = ["Select Status", "Not Started", "In Progress", "Completed", "Graded"]
    current_status = tk.StringVar(value=status_options[0])
    tk.OptionMenu(form_frame, current_status, *status_options).grid(column=1, row=6, sticky="w", padx=5, pady=5)

    recurring_var = tk.BooleanVar(value=False)
    tk.Checkbutton(form_frame, text="Make this task recurring?", variable=recurring_var).grid(column=0, row=7,
                                                                                              columnspan=2, sticky="w",
                                                                                              padx=5, pady=5)

    recurring_frame = tk.Frame(form_frame)
    recurring_frame.grid(column=0, row=8, columnspan=2, sticky="w", padx=5, pady=5)
    recurring_frame.grid_remove()

    tk.Label(recurring_frame, text="Recurring on:").grid(column=0, row=0, sticky="nw", padx=5, pady=5)
    days_frame = tk.Frame(recurring_frame)
    days_frame.grid(column=1, row=0, sticky="w", padx=5, pady=5)

    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_vars = {}
    for i, day in enumerate(weekdays):
        var = tk.BooleanVar(value=False)
        tk.Checkbutton(days_frame, text=day, variable=var).grid(row=0, column=i, sticky="w")
        weekday_vars[day] = var

    tk.Label(recurring_frame, text="Recurrence End Date:").grid(column=0, row=1, sticky="w", padx=5, pady=5)
    recurrence_end = DateEntry(recurring_frame, width=40)
    recurrence_end.grid(column=1, row=1, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Reminder Hours Before Due:").grid(column=0, row=9, sticky="w", padx=5, pady=5)
    reminder_hours_entry = tk.Entry(form_frame, width=10)
    reminder_hours_entry.insert(0, "24")
    reminder_hours_entry.grid(column=1, row=9, sticky="w", padx=5, pady=5)

    def toggle_recurring():
        if recurring_var.get():
            recurring_frame.grid()
        else:
            recurring_frame.grid_remove()

    recurring_var.trace_add("write", lambda *args: toggle_recurring())

    def save_assignment():
        name = name_entry.get().strip()
        course = selected_class.get()
        status = current_status.get()

        if not name or course == "Select Class" or status == "Select Status":
            messagebox.showerror("Error", "Please fill all required fields.")
            return

        try:
            start_date_val = datetime.strptime(start_date.get(), "%m/%d/%y")
            start_time_val = datetime.strptime(start_time_entry.get().strip(), "%I:%M %p").time()
            start = datetime.combine(start_date_val, start_time_val)

            due_date_val = datetime.strptime(due_date.get(), "%m/%d/%y")
            due_time_val = datetime.strptime(due_time_entry.get().strip(), "%I:%M %p").time()
            due = datetime.combine(due_date_val, due_time_val)

            reminder_hours = int(reminder_hours_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid date or time format. Use HH:MM AM/PM for time (e.g., 02:30 PM).")
            return

        if due < start:
            messagebox.showerror("Error", "Due date/time cannot be before start date/time.")
            return

        # Prepare recurrence days string for display
        recurrence_days = 0
        recurrence_days_str = ""
        if recurring_var.get():
            day_map = {"Mon": 1, "Tue": 2, "Wed": 4, "Thu": 8, "Fri": 16, "Sat": 32, "Sun": 64}
            recurrence_days = sum(day_map[d] for d, var in weekday_vars.items() if var.get())
            recurrence_days_str = ", ".join([d for d, var in weekday_vars.items() if var.get()])

        # Insert task into the database, including reminder_hours and reminder_sent (default 0)
        cursor.execute(
            'INSERT INTO tasks (name, course, start, due, status, recurrence_days, reminder_hours, reminder_sent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (name, course, start.strftime("%Y-%m-%d %H:%M:%S"), due.strftime("%Y-%m-%d %H:%M:%S"), status,
             recurrence_days, reminder_hours, 0)
        )
        conn.commit()
        task_id = cursor.lastrowid

        # Insert new row into Treeview with columns: Name, Class, Start, Due, Status
        tree.insert(
            "",
            tk.END,
            iid=str(task_id),
            values=(
                name,
                course,
                start.strftime("%m/%d/%y %I:%M %p"),
                due.strftime("%m/%d/%y %I:%M %p"),
                status
            ),
            tags=(status,)
        )
        # Reminder scheduling handled externally

        if recurring_var.get():
            end_dt_date = datetime.strptime(recurrence_end.get(), "%m/%d/%y")
            day_map = {"Mon": 0, "Tue": 1, "Wed": 2, "Thu": 3, "Fri": 4, "Sat": 5, "Sun": 6}
            selected_days = [day_map[d] for d, var in weekday_vars.items() if var.get()]
            if not selected_days:
                messagebox.showerror("Error", "Select at least one weekday for recurring tasks.")
                return
            current_date = start
            while current_date.date() <= end_dt_date.date():
                if current_date.weekday() in selected_days and current_date != start:
                    delta = due - start
                    current_due = current_date + delta
                    # Insert each recurring task into the database and Treeview with unique id, including reminder_hours and reminder_sent
                    cursor.execute(
                        'INSERT INTO tasks (name, course, start, due, status, recurrence_days, reminder_hours, reminder_sent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        (name, course, current_date.strftime("%Y-%m-%d %H:%M:%S"),
                         current_due.strftime("%Y-%m-%d %H:%M:%S"), status, recurrence_days, reminder_hours, 0)
                    )
                    conn.commit()
                    recurring_task_id = cursor.lastrowid
                    tree.insert(
                        "",
                        tk.END,
                        iid=str(recurring_task_id),
                        values=(
                            name,
                            course,
                            current_date.strftime("%m/%d/%y %I:%M %p"),
                            current_due.strftime("%m/%d/%y %I:%M %p"),
                            status
                        ),
                        tags=(status,)
                    )
                    # Reminder scheduling handled externally
                current_date += timedelta(days=1)

        new_window.destroy()

    tk.Button(new_window, text="Save & Close", command=save_assignment).grid(column=0, row=10, columnspan=2, pady=20)


# Function to view assignments by class
def open_view_by_class_window():
    view_window = tk.Toplevel(root)
    view_window.title("View Assignments by Class")
    view_window.geometry("700x400")

    tk.Label(view_window, text="Select Class:").pack(pady=5)
    classes = ["Database Design", "Computer Organization & Assembly Language",
               "Modern Software Design & Development", "Web Application Development"]
    selected_class = tk.StringVar(value=classes[0])
    tk.OptionMenu(view_window, selected_class, *classes).pack(pady=5)

    class_tree = ttk.Treeview(view_window, columns=("Name", "Start", "Due", "Status"), show='headings')
    class_tree.heading("Name", text="Assignment Name")
    class_tree.heading("Start", text="Start Date")
    class_tree.heading("Due", text="Due Date")
    class_tree.heading("Status", text="Status")
    class_tree.pack(fill="both", expand=True)

    class_tree.tag_configure("Not Started", background="#f0f0f0")
    class_tree.tag_configure("In Progress", background="#fffacd")
    class_tree.tag_configure("Completed", background="#d0f0c0")
    class_tree.tag_configure("Graded", background="#add8e6")

    def update_tree(*args):
        for item in class_tree.get_children():
            class_tree.delete(item)
        for item in tree.get_children():
            vals = tree.item(item, "values")
            name, cls, start, due, status, recurrence = vals
            if cls == selected_class.get():
                class_tree.insert("", tk.END, values=(name, start, due, status), tags=(status,))

    selected_class.trace_add("write", update_tree)
    update_tree()


# Function to edit selected task
def open_edit_window():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Edit Task", "Please select a task to edit.")
        return

    item = tree.item(selected_item[0])  # Fix: Use selected_item[0]
    values = item['values']
    # Treeview no longer has Recurrence column, so fill dummy value for recurrence_val
    if len(values) == 6:
        name_val, course_val, start_val, due_val, status_val, recurrence_val = values
    else:
        name_val, course_val, start_val, due_val, status_val = values
        recurrence_val = ""

    edit_window = tk.Toplevel(root)
    edit_window.title("Edit Assignment")
    edit_window.geometry("800x600")

    tk.Label(edit_window, text="Edit Assignment", font=("Arial", 16)).grid(column=0, row=0, columnspan=2, pady=10)
    form_frame = tk.Frame(edit_window)
    form_frame.grid(column=0, row=1, padx=20, pady=10)

    # Assignment Name
    tk.Label(form_frame, text="Assignment Name:").grid(column=0, row=0, sticky="w", padx=5, pady=5)
    name_entry = tk.Entry(form_frame, width=40)
    name_entry.insert(0, name_val)
    name_entry.grid(column=1, row=0, sticky="w", padx=5, pady=5)

    # Class
    tk.Label(form_frame, text="Class:").grid(column=0, row=1, sticky="w", padx=5, pady=5)
    classes = [
        "Database Design",
        "Computer Organization & Assembly Language",
        "Modern Software Design & Development",
        "Web Application Development"
    ]
    selected_course = tk.StringVar(value=course_val)
    tk.OptionMenu(form_frame, selected_course, *classes).grid(column=1, row=1, sticky="w", padx=5, pady=5)

    # Dates
    tk.Label(form_frame, text="Start Date:").grid(column=0, row=2, sticky="w", padx=5, pady=5)
    start_date = DateEntry(form_frame, width=40)
    # Try multiple datetime formats for parsing start_val
    start_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%y %I:%M %p"
    ]
    start_datetime = None
    for fmt in start_formats:
        try:
            start_datetime = datetime.strptime(start_val, fmt)
            break
        except ValueError:
            continue
    if start_datetime is None:
        messagebox.showerror("Error", f"Could not parse start datetime: {start_val}")
        edit_window.destroy()
        return
    start_date.set_date(start_datetime)
    start_date.grid(column=1, row=2, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Start Time (HH:MM AM/PM):").grid(column=0, row=3, sticky="w", padx=5, pady=5)
    start_time_entry = tk.Entry(form_frame, width=40)
    start_time_entry.insert(0, start_datetime.strftime("%I:%M %p"))
    start_time_entry.grid(column=1, row=3, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Date:").grid(column=0, row=4, sticky="w", padx=5, pady=5)
    due_date = DateEntry(form_frame, width=40)
    due_formats = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%m/%d/%y %I:%M %p"
    ]
    due_datetime = None
    for fmt in due_formats:
        try:
            due_datetime = datetime.strptime(due_val, fmt)
            break
        except ValueError:
            continue
    if due_datetime is None:
        messagebox.showerror("Error", f"Could not parse due datetime: {due_val}")
        edit_window.destroy()
        return
    due_date.set_date(due_datetime)
    due_date.grid(column=1, row=4, sticky="w", padx=5, pady=5)

    tk.Label(form_frame, text="Due Time (HH:MM AM/PM):").grid(column=0, row=5, sticky="w", padx=5, pady=5)
    due_time_entry = tk.Entry(form_frame, width=40)
    due_time_entry.insert(0, due_datetime.strftime("%I:%M %p"))
    due_time_entry.grid(column=1, row=5, sticky="w", padx=5, pady=5)

    # Status
    tk.Label(form_frame, text="Status:").grid(column=0, row=6, sticky="w", padx=5, pady=5)
    status_options = ["Not Started", "In Progress", "Completed", "Graded"]
    current_status = tk.StringVar(value=status_val)
    tk.OptionMenu(form_frame, current_status, *status_options).grid(column=1, row=6, sticky="w", padx=5, pady=5)

    # Reminder hours
    tk.Label(form_frame, text="Reminder Hours Before Due:").grid(column=0, row=7, sticky="w", padx=5, pady=5)
    reminder_hours_entry = tk.Entry(form_frame, width=10)
    reminder_hours_entry.insert(0, "24")
    reminder_hours_entry.grid(column=1, row=7, sticky="w", padx=5, pady=5)

    # Recurrence checkboxes
    recurring_var = tk.BooleanVar(value=recurrence_val not in ("", None, 0))
    tk.Checkbutton(form_frame, text="Make this task recurring?", variable=recurring_var).grid(column=0, row=8,
                                                                                              columnspan=2, sticky="w",
                                                                                              padx=5, pady=5)

    recurring_frame = tk.Frame(form_frame)
    recurring_frame.grid(column=0, row=9, columnspan=2, sticky="w", padx=5, pady=5)
    if not recurring_var.get():
        recurring_frame.grid_remove()

    tk.Label(recurring_frame, text="Recurring on:").grid(column=0, row=0, sticky="nw", padx=5, pady=5)
    days_frame = tk.Frame(recurring_frame)
    days_frame.grid(column=1, row=0, sticky="w", padx=5, pady=5)

    weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    weekday_vars = {}
    for i, day in enumerate(weekdays):
        var = tk.BooleanVar(value=False)
        tk.Checkbutton(days_frame, text=day, variable=var).grid(row=0, column=i, sticky="w")
        weekday_vars[day] = var

    # Decode recurrence_val and set checkboxes
    if isinstance(recurrence_val, int):
        recurrence_str = decode_recurrence_days(recurrence_val)
    else:
        recurrence_str = recurrence_val
    for day, var in weekday_vars.items():
        var.set(day in recurrence_str.split(", "))

    def toggle_recurring():
        if recurring_var.get():
            recurring_frame.grid()
        else:
            recurring_frame.grid_remove()

    recurring_var.trace_add("write", lambda *args: toggle_recurring())

    # Save changes
    def save_changes():
        new_name = name_entry.get().strip()
        new_course = selected_course.get()
        try:
            new_start = datetime.combine(start_date.get_date(),
                                         datetime.strptime(start_time_entry.get().strip(), "%I:%M %p").time())
            new_due = datetime.combine(due_date.get_date(),
                                       datetime.strptime(due_time_entry.get().strip(), "%I:%M %p").time())
            reminder_hours = int(reminder_hours_entry.get())
        except ValueError as e:
            messagebox.showerror("Error", f"Invalid time format. Use HH:MM AM/PM (e.g., 02:30 PM). Error: {str(e)}")
            return
        new_status = current_status.get()
        if not new_name:
            messagebox.showerror("Error", "Assignment name is required.")
            return

        # Encode recurrence days
        day_map = {"Mon": 1, "Tue": 2, "Wed": 4, "Thu": 8, "Fri": 16, "Sat": 32, "Sun": 64}
        recurrence_days = sum(day_map[d] for d, var in weekday_vars.items() if var.get()) if recurring_var.get() else 0
        recurrence_days_str = decode_recurrence_days(recurrence_days)

        try:
            # Use the item iid as the task ID (guaranteed to be correct)
            task_id = int(selected_item[0])
            # Update database
            cursor.execute(
                'UPDATE tasks SET name=?, course=?, start=?, due=?, status=?, reminder_hours=?, recurrence_days=? WHERE id=?',
                (new_name, new_course, new_start.strftime("%Y-%m-%d %H:%M:%S"),
                 new_due.strftime("%Y-%m-%d %H:%M:%S"), new_status, reminder_hours, recurrence_days, task_id)
            )
            if cursor.rowcount == 0:
                messagebox.showerror("Error", f"No task found with ID {task_id}. Update failed.")
                return
            conn.commit()
            # Update tree display
            tree.item(
                selected_item[0],
                values=(new_name, new_course, new_start.strftime("%m/%d/%y %I:%M %p"),
                        new_due.strftime("%m/%d/%y %I:%M %p"), new_status),
                tags=(new_status,)
            )
            messagebox.showinfo("Success", "Task updated successfully!")
            edit_window.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes: {str(e)}")

    tk.Button(edit_window, text="Save Changes", command=save_changes).grid(column=0, row=10, columnspan=2, pady=20)# Button to test email setup
def test_email():
    """Test the email configuration"""
    from email_utils import test_email_setup
    if test_email_setup():
        messagebox.showinfo("Email Test", "Email test successful! Check your inbox.")
    else:
        messagebox.showerror("Email Test", "Email test failed. Check the console for error details.")


#
# Buttons and Status Update Controls
tk.Button(root, text="Add Assignment", command=open_new_window).pack(pady=5)
tk.Button(root, text="View Assignments by Class", command=open_view_by_class_window).pack(pady=5)
tk.Button(root, text="Edit Selected Task", command=open_edit_window).pack(pady=5)
tk.Button(root, text="Test Email Setup", command=test_email).pack(pady=5)

# --- Status Change Dropdown and Button ---
status_frame = tk.Frame(root)
status_frame.pack(pady=5)
tk.Label(status_frame, text="Change Status:").pack(side=tk.LEFT)
status_options = ["Not Started", "In Progress", "Completed", "Graded"]
status_combobox = ttk.Combobox(status_frame, values=status_options, state="readonly", width=15)
status_combobox.set(status_options[0])
status_combobox.pack(side=tk.LEFT, padx=5)

def update_task_status():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Update Status", "Please select a task to update its status.")
        return
    new_status = status_combobox.get()
    task_id = int(selected_item[0])
    try:
        cursor.execute("UPDATE tasks SET status=? WHERE id=?", (new_status, task_id))
        conn.commit()
        values = list(tree.item(selected_item[0], "values"))
        values[4] = new_status  # Status column
        tree.item(selected_item[0], values=values, tags=(new_status,))
    except Exception as e:
        messagebox.showerror("Update Status", f"Failed to update status: {e}")

tk.Button(status_frame, text="Update Status", command=update_task_status).pack(side=tk.LEFT, padx=5)

# --- New functions for deleting tasks ---
def delete_selected_task():
    selected_item = tree.selection()
    if not selected_item:
        messagebox.showwarning("Delete Task", "Please select a task to delete.")
        return
    task_id = selected_item[0]
    # Remove from database
    try:
        cursor.execute("DELETE FROM tasks WHERE id=?", (int(task_id.lstrip('I')),))
        conn.commit()
        tree.delete(selected_item)
    except Exception as e:
        messagebox.showerror("Delete Task", f"Failed to delete task: {e}")

def delete_all_tasks():
    if not messagebox.askyesno("Delete All Tasks", "Are you sure you want to delete ALL tasks?"):
        return
    try:
        cursor.execute("DELETE FROM tasks")
        conn.commit()
        for item in tree.get_children():
            tree.delete(item)
    except Exception as e:
        messagebox.showerror("Delete All Tasks", f"Failed to delete all tasks: {e}")

# --- New buttons for deleting tasks ---
tk.Button(root, text="Delete Selected Task", command=delete_selected_task).pack(pady=5)
tk.Button(root, text="Delete All Tasks", command=delete_all_tasks).pack(pady=5)

# Initialize system tray icon
setup_tray()


def reminder_loop():
    """Background loop to check for upcoming task reminders. Uses its own SQLite connection for thread safety."""
    import sqlite3
    local_conn = sqlite3.connect('tasks.db')
    local_cursor = local_conn.cursor()
    while True:
        now = datetime.now()
        # Also retrieve reminder_sent
        local_cursor.execute('SELECT id, name, course, due, status, reminder_hours, reminder_sent FROM tasks')
        tasks = local_cursor.fetchall()
        for task in tasks:
            task_id, name, course, due_str, status, reminder_hours, reminder_sent = task
            if not reminder_hours:
                continue  # Skip tasks without reminders

            due = datetime.strptime(due_str, "%Y-%m-%d %H:%M:%S")
            reminder_time = due - timedelta(hours=reminder_hours)

            # Only send if the reminder time has passed, task is not completed, and not already reminded
            if reminder_time <= now < due and status != "Completed" and (reminder_sent is None or reminder_sent == 0):
                try:
                    send_email(
                        os.getenv("EMAIL_USER"),  # recipient email
                        f"Reminder: {name} due soon",  # subject
                        f"Your assignment '{name}' for {course} is due at {due.strftime('%m/%d/%y %I:%M %p')}."  # body
                    )
                    print(f"Reminder sent for task: {name}")
                    # Mark as reminded to avoid multiple emails
                    local_cursor.execute('UPDATE tasks SET reminder_sent=1 WHERE id=?', (task_id,))
                    local_conn.commit()
                except Exception as e:
                    print(f"Failed to send reminder for {name}: {e}")

        # --- Update tray icon tooltip with pending tasks count ---
        try:
            # Re-fetch tasks to get up-to-date info
            local_cursor.execute('SELECT status, due FROM tasks')
            all_tasks = local_cursor.fetchall()
            pending_count = 0
            for status, due_str in all_tasks:
                try:
                    due = datetime.strptime(due_str, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue
                if status != "Completed" and due > now:
                    pending_count += 1
            # Update tray icon tooltip
            if 'tray_icon' in globals():
                tray_icon.title = f"Task Manager - {pending_count} pending"
        except Exception as e:
            # Silently ignore errors in tray update
            pass

        time.sleep(60)  # Check every minute
threading.Thread(target=reminder_loop, daemon=True).start()
root.mainloop()