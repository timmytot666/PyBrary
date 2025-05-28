# --- Imports ---
import tkinter as tk  # Import tkinter and alias it as tk
from tkinter import ttk, messagebox
import requests
from requests import get, exceptions as RequestsExceptions # Alias exceptions for clarity
from json import loads, JSONDecodeError
import csv
import os
import sys
import io
from datetime import date

# --- Pillow Import and Handling ---
try:
    from PIL import Image, ImageTk, UnidentifiedImageError
except ImportError:
    # Use print for critical errors before Tkinter is fully initialized
    print("-----------------------------------------------------------")
    print("ERROR: Pillow library not found.")
    print("Please install it using: pip install Pillow")
    print("-----------------------------------------------------------")
    # Attempt to show a Tkinter message box ONLY IF tkinter itself imported okay
    try:
        root_check = tk.Tk()
        root_check.withdraw() # Hide the empty root window
        messagebox.showerror("Missing Dependency", "Pillow library not found.\nPlease install it using:\npip install Pillow")
        root_check.destroy()
    except tk.TclError:
        print("Tkinter initialization failed - cannot show error dialog.")
    except NameError:
        print("Tkinter (tk) not defined - cannot show error dialog.") # Should not happen if import tk worked
    sys.exit(1) # Exit regardless

# --- Configuration ---
FIELDNAMES = ['ISBN', 'Title', 'Author', 'Publisher', 'PublishedDate', 'ImagePath', 'ReadStatus', 'DateAdded']
COLLECTION_FILE = 'book_collection.csv'
COVERS_DIR = 'covers' # Directory to store downloaded covers
PLACEHOLDER_IMAGE_NAME = 'placeholder.png' # Name of your placeholder image file
MAX_IMAGE_WIDTH = 150 # Maximum width for display image
MAX_IMAGE_HEIGHT = 220 # Maximum height for display image

# --- Global Widgets and Collection ---
root = None
isbn_entry = None
collection_tree = None # ttk.Treeview for the book list
details_frame = None # Frame to show selected book's details
detail_labels = {} # Dictionary to hold labels in the details frame (key: fieldname, value: label widget)
image_label = None # Label specifically for the cover image
status_bar = None # Label for status messages
status_var = None # tk.StringVar for the status bar text
placeholder_photo = None # To hold the PhotoImage for the placeholder

# --- Global Variable for Read Status Checkbutton ---
read_status_var = None # tk.StringVar linked to the Checkbutton's state ('Yes'/'No')
read_status_checkbutton = None # The ttk.Checkbutton widget itself

# --- Global Data Structure ---
collection = [] # Global list to hold book dictionaries

# --- Helper Functions ---

def get_script_directory():
    """Gets the directory where the script/executable is running."""
    try:
        # Best choice: directory of the executable if frozen (PyInstaller)
        if getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        # Next best: directory of the script file
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        # Fallback if __file__ is not defined (e.g., interactive)
        try:
            return os.path.dirname(os.path.abspath(sys.argv[0]))
        except:
             # Final fallback: current working directory
             return os.getcwd()

def ensure_covers_dir():
    """Creates the covers directory if it doesn't exist. Returns True if exists/created, False on error."""
    covers_path = os.path.join(get_script_directory(), COVERS_DIR)
    if not os.path.exists(covers_path):
        try:
            os.makedirs(covers_path)
            print(f"Created directory: {covers_path}")
            return True
        except OSError as e:
            messagebox.showerror("Directory Error", f"Could not create covers directory '{COVERS_DIR}':\n{e}")
            return False
    return True # Directory already exists

def load_placeholder_image():
    """Loads or creates the placeholder image."""
    global placeholder_photo
    placeholder_path = os.path.join(get_script_directory(), PLACEHOLDER_IMAGE_NAME)
    try:
        # Create a default gray image if placeholder file not found
        if not os.path.exists(placeholder_path):
             print(f"Warning: '{PLACEHOLDER_IMAGE_NAME}' not found. Creating default placeholder.")
             img = Image.new('RGB', (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), color='lightgrey')
        else:
             img = Image.open(placeholder_path)

        img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS) # Resize gracefully
        placeholder_photo = ImageTk.PhotoImage(img)
        print("Placeholder image loaded/created successfully.")
    except Exception as e:
        messagebox.showerror("Image Error", f"Failed to load or create placeholder image:\n{e}")
        # Create a minimal fallback if even creation fails
        try:
            img = Image.new('RGB', (50, 75), color = 'grey') # Smaller fallback
            placeholder_photo = ImageTk.PhotoImage(img)
            print("Used minimal fallback placeholder.")
        except Exception as e_fallback:
            print(f"CRITICAL ERROR: Could not create fallback placeholder: {e_fallback}")
            placeholder_photo = None # No image available


def clean_isbn(isbn):
    """Removes hyphens and spaces from ISBN."""
    return isbn.replace('-', '').replace(' ', '').strip()

def _sort_collection():
    """Sorts the global collection list by Title, case-insensitive."""
    global collection
    # Sort safely, handling potential None or non-string titles
    collection.sort(key=lambda book: str(book.get('Title', '')).lower())


def load_collection_on_start():
    """Loads books from CSV, handles missing fields, sorts, populates Treeview, and updates status."""
    global collection, status_var, collection_tree
    filepath = os.path.join(get_script_directory(), COLLECTION_FILE)
    loaded_count = 0
    status_message = "Ready."
    collection = [] # Start fresh before loading

    if os.path.exists(filepath):
        try:
            temp_collection = []
            with open(filepath, mode='r', newline='', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                file_fieldnames = reader.fieldnames if reader.fieldnames else []

                print(f"Loading from {COLLECTION_FILE}. Headers found: {file_fieldnames}")

                for i, row in enumerate(reader):
                    # Basic check for empty row or missing essential data
                    if not row or not row.get('ISBN'):
                         print(f"Skipping empty or invalid row {i+1} in CSV.")
                         continue

                    # Load data, providing defaults for potentially missing new fields
                    book_data = {
                        'ISBN': row.get('ISBN'),
                        'Title': row.get('Title', 'N/A'),
                        'Author': row.get('Author', 'N/A'),
                        'Publisher': row.get('Publisher', 'N/A'),
                        'PublishedDate': row.get('PublishedDate', 'N/A'),
                        'ImagePath': row.get('ImagePath') or None, # Normalize empty path to None
                        'ReadStatus': row.get('ReadStatus', 'No'),  # Default to 'No' if missing
                        'DateAdded': row.get('DateAdded', 'N/A') # Default to 'N/A' if missing
                    }
                    temp_collection.append(book_data)

            collection = temp_collection # Assign loaded data
            loaded_count = len(collection)
            _sort_collection() # Sort after loading
            status_message = f"Loaded {loaded_count} books from '{COLLECTION_FILE}'. Collection sorted."
        except Exception as e:
            messagebox.showerror("Load Error", f"Failed to load or parse '{COLLECTION_FILE}':\n{e}")
            collection = [] # Start fresh on error
            status_message = f"Error loading '{COLLECTION_FILE}'. Starting empty."
            print(f"Load Error Details: {type(e).__name__} - {e}")
    else:
        status_message = f"'{COLLECTION_FILE}' not found. Starting new collection."

    if status_var:
        status_var.set(status_message)

    update_collection_treeview() # Populate Treeview with loaded/empty data
    clear_details_panel() # Clear details and disable checkbutton initially


def save_collection_to_file():
    """Sorts and saves the current collection to the CSV file. Returns True on success, False on error."""
    global collection, status_var
    filepath = os.path.join(get_script_directory(), COLLECTION_FILE)

    _sort_collection() # Ensure collection is sorted before saving

    try:
        with open(filepath, mode='w', newline='', encoding='utf-8') as csvfile:
            # Use the global FIELDNAMES which includes all columns
            writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES, extrasaction='ignore')
            writer.writeheader()
            writer.writerows(collection)
        print(f"Collection saved successfully to '{filepath}'")
        return True
    except Exception as e:
        messagebox.showerror("Save Error", f"Failed to save collection to '{COLLECTION_FILE}':\n{e}")
        if status_var:
            status_var.set(f"Error saving collection: {e}")
        print(f"Save Error Details: {type(e).__name__} - {e}")
        return False

# --- Treeview and Details Panel Update Functions ---

def update_collection_treeview():
    """Clears and repopulates the Treeview with the current collection."""
    global collection, collection_tree
    if not collection_tree: return

    # Clear existing items safely
    try:
        for item in collection_tree.get_children():
            collection_tree.delete(item)
    except tk.TclError as e:
        print(f"Error clearing treeview (might happen during shutdown): {e}")
        return # Avoid further errors if widget is destroyed

    # Add items from the sorted collection, using ISBN as the item ID (iid)
    for book in collection:
        isbn = book.get('ISBN', '')
        # Skip if ISBN is missing (shouldn't happen with load checks, but safety)
        if not isbn: continue

        title = book.get('Title', 'N/A')
        author = book.get('Author', 'N/A')
        # Use ISBN as iid for easy lookup, display Title and Author
        try:
             collection_tree.insert('', tk.END, iid=isbn, values=(title, author))
        except tk.TclError as e:
             print(f"Error inserting item into treeview (widget might be destroyed?): {e}")


def display_selected_book_details(event=None):
    """Displays the details (text, image, read status) of the selected book."""
    global collection_tree, detail_labels, image_label, collection, placeholder_photo
    global read_status_var, read_status_checkbutton

    if not collection_tree: return # Exit if treeview doesn't exist

    try:
        selected_items = collection_tree.selection()
        if not selected_items:
            clear_details_panel() # Clear if selection is lost
            return

        selected_iid = selected_items[0] # Get the ISBN (iid) of the selected item
    except tk.TclError as e:
        print(f"Error getting treeview selection (widget might be destroyed?): {e}")
        return

    # Find the book in the main collection list using the ISBN
    selected_book = next((book for book in collection if book.get('ISBN') == selected_iid), None)

    if not selected_book:
        # This might happen if collection/treeview get out of sync somehow
        messagebox.showerror("Sync Error", f"Could not find details for selected ISBN: {selected_iid}")
        clear_details_panel()
        return

    # --- Update text labels ---
    for field, label in detail_labels.items():
        if label: # Check if label exists
            label.config(text=selected_book.get(field, 'N/A')) # Update text

    # --- Update Read Status Checkbutton ---
    if read_status_checkbutton and read_status_var:
        current_status = selected_book.get('ReadStatus', 'No')
        # Set the variable; toggle_read_status handles preventing loops
        read_status_var.set(current_status)
        # Enable the checkbutton for interaction
        read_status_checkbutton.config(state=tk.NORMAL)

    # --- Update Image ---
    loaded_photo = placeholder_photo # Default to placeholder
    image_path = selected_book.get('ImagePath')

    if image_path and os.path.exists(image_path):
        try:
            img = Image.open(image_path)
            # Resize while maintaining aspect ratio to fit within max dimensions
            img.thumbnail((MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), Image.Resampling.LANCZOS)
            loaded_photo = ImageTk.PhotoImage(img)
        except FileNotFoundError:
            print(f"Image file not found, using placeholder: {image_path}")
        except UnidentifiedImageError:
             print(f"Cannot identify image file (corrupted?), using placeholder: {image_path}")
        except Exception as e:
            print(f"Error loading image {image_path}, using placeholder: {e}")
            # Keep loaded_photo as placeholder_photo
    # else: Use placeholder if no path or file doesn't exist

    if image_label:
        image_label.config(image=loaded_photo)
        # **IMPORTANT**: Keep a reference to prevent garbage collection!
        image_label.image = loaded_photo


def clear_details_panel():
    """Clears text labels, sets placeholder image, resets/disables ReadStatus checkbutton."""
    global detail_labels, image_label, placeholder_photo
    global read_status_var, read_status_checkbutton

    # Clear text labels
    for label in detail_labels.values():
        if label: label.config(text="N/A")

    # Set placeholder image
    if image_label and placeholder_photo:
        image_label.config(image=placeholder_photo)
        image_label.image = placeholder_photo # Keep reference

    # Reset and disable the ReadStatus checkbutton
    if read_status_var:
        read_status_var.set('No') # Reset variable to 'No'
    if read_status_checkbutton:
        read_status_checkbutton.config(state=tk.DISABLED)


# --- Read Status Toggle Function ---

def toggle_read_status():
    """Called when the ReadStatus checkbutton is clicked. Updates data and saves."""
    global collection, collection_tree, read_status_var, status_var, root

    if not read_status_var or not collection_tree: return # Widgets not ready

    try:
        selected_items = collection_tree.selection()
        if not selected_items:
            if read_status_checkbutton: read_status_checkbutton.config(state=tk.DISABLED)
            return # No item selected, disable button

        selected_iid = selected_items[0]
    except tk.TclError as e:
         print(f"Error accessing treeview in toggle_read_status: {e}")
         return

    # Get the new status reflecting the user's click ('Yes' or 'No')
    new_status = read_status_var.get()

    # Find the book and update its status in the main collection list
    book_found = False
    for book in collection:
        if book.get('ISBN') == selected_iid:
            book_found = True
            # Only update and save if the status actually changed from what's stored
            if book.get('ReadStatus') != new_status:
                book['ReadStatus'] = new_status
                title = book.get('Title', 'Unknown Title')
                print(f"User changed ReadStatus for '{title}' to '{new_status}'")

                # Update status bar and attempt to save immediately
                if status_var: status_var.set(f"Saving ReadStatus change for '{title}'...")
                if root: root.update_idletasks() # Force GUI update

                if save_collection_to_file():
                    if status_var: status_var.set(f"ReadStatus for '{title}' updated to '{new_status}'. Saved.")
                else:
                    # Save failed - error message shown by save_collection_to_file
                    if status_var: status_var.set(f"FAILED to save ReadStatus change for '{title}'.")
                    # Optional: Revert the change in memory?
                    # book['ReadStatus'] = 'Yes' if new_status == 'No' else 'No'
            # else: Status didn't change, likely programmatic update, do nothing.
            break # Exit loop once book is found and processed

    if not book_found:
         print(f"Warning: toggle_read_status - No book found for selected ISBN {selected_iid}.")
         if read_status_checkbutton: read_status_checkbutton.config(state=tk.DISABLED)


# --- Core Functionality: Fetch and Add Book ---

def fetch_and_add_book():
    """Fetches book info, adds DateAdded/ReadStatus, downloads image, adds, sorts, saves, updates tree."""
    global isbn_entry, status_var, collection, root, collection_tree # Ensure access

    # --- Input Validation ---
    if not all([isbn_entry, status_var, root, collection_tree]):
         messagebox.showerror("Initialization Error", "GUI components are not ready.")
         return

    isbn_input = isbn_entry.get().strip()
    if not isbn_input:
        messagebox.showwarning("Input Required", "Please enter an ISBN.")
        isbn_entry.focus()
        return

    cleaned_isbn = clean_isbn(isbn_input)

    # --- Check for Duplicates (using Treeview iids for efficiency) ---
    try:
        if collection_tree.exists(cleaned_isbn):
            messagebox.showinfo("Duplicate", f"Book with ISBN {cleaned_isbn} already exists in the collection.")
            isbn_entry.delete(0, tk.END)
            isbn_entry.focus()
            return
    except tk.TclError as e:
         print(f"Error checking treeview for duplicate: {e}")
         # Fallback: check in collection list (slower)
         if any(book.get('ISBN') == cleaned_isbn for book in collection):
              messagebox.showinfo("Duplicate", f"Book with ISBN {cleaned_isbn} already exists (checked list).")
              isbn_entry.delete(0, tk.END)
              isbn_entry.focus()
              return


    status_var.set(f"Searching for ISBN: {cleaned_isbn}...")
    root.update_idletasks() # Show status update

    # --- API Call ---
    url = f"https://openlibrary.org/api/books?bibkeys=ISBN:{cleaned_isbn}&format=json&jscmd=data"
    print(f"Fetching URL: {url}")
    # Use a more descriptive User-Agent
    headers = {'User-Agent': f'TkinterBookCollectionApp/0.4 ({sys.platform}; Python/{sys.version.split()[0]})'}

    try:
        response = get(url, headers=headers, timeout=20) # Increased timeout
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

        data = loads(response.text)
        book_key = f"ISBN:{cleaned_isbn}"

        if not data or book_key not in data:
            messagebox.showwarning("Not Found", f"ISBN {cleaned_isbn} was not found or returned no data from OpenLibrary.")
            status_var.set(f"ISBN {cleaned_isbn} not found by API.")
            isbn_entry.focus()
            return

        # --- Process API Data ---
        book_info_raw = data[book_key]
        book_details = {
            'ISBN': cleaned_isbn,
            'Title': book_info_raw.get('title', 'N/A'),
            'Author': ', '.join([a.get('name', 'N/A') for a in book_info_raw.get('authors', [])]) or 'N/A',
            'Publisher': ', '.join([p.get('name', 'N/A') for p in book_info_raw.get('publishers', [])]) or 'N/A',
            'PublishedDate': book_info_raw.get('publish_date', 'N/A'),
            'ImagePath': None, # Initialize image path
            # Add New Fields with defaults/current values
            'ReadStatus': 'No',
            'DateAdded': date.today().isoformat() # Add current date
        }

        # --- Confirmation Dialog ---
        confirm_fields_order = ['Title', 'Author', 'Publisher', 'PublishedDate', 'DateAdded']
        confirm_message_lines = [f"{field}: {book_details.get(field, 'N/A')}" for field in confirm_fields_order]
        confirm_message = "Found the following book:\n\n" + "\n".join(confirm_message_lines) + "\n\nAdd it to your collection?"

        if messagebox.askyesno("Confirm Add", confirm_message):
            status_var.set(f"Adding '{book_details['Title']}'. Checking for cover image...")
            root.update_idletasks()

            # --- Image Download Attempt ---
            cover_url = None
            # OpenLibrary sometimes provides a direct 'cover' dict, sometimes just 'covers' list of IDs
            if 'cover' in book_info_raw and isinstance(book_info_raw['cover'], dict):
                 cover_url = book_info_raw['cover'].get('medium') # Prefer medium size direct URL if available
            # If no direct URL, check the 'covers' list for an ID
            if not cover_url and 'covers' in book_info_raw and isinstance(book_info_raw['covers'], list) and book_info_raw['covers']:
                 cover_id_num = book_info_raw['covers'][0] # Use the first ID
                 if cover_id_num > 0: # IDs seem to be positive integers
                      cover_url = f"https://covers.openlibrary.org/b/id/{cover_id_num}-M.jpg" # Construct URL (Medium size)

            if cover_url:
                 print(f"Attempting to download cover from: {cover_url}")
                 if ensure_covers_dir(): # Make sure directory exists/is created
                     # Use ISBN for a unique local filename
                     local_image_path = os.path.join(get_script_directory(), COVERS_DIR, f"{cleaned_isbn}.jpg")
                     try:
                         img_response = requests.get(cover_url, stream=True, timeout=20, headers=headers)
                         img_response.raise_for_status() # Check download status

                         # Basic check if response looks like an image
                         content_type = img_response.headers.get('content-type', '').lower()
                         if 'image' in content_type:
                             with open(local_image_path, 'wb') as f:
                                 for chunk in img_response.iter_content(8192): # Use larger chunk size
                                     f.write(chunk)
                             book_details['ImagePath'] = local_image_path # Store the *local path*
                             print(f"Cover saved successfully to: {local_image_path}")
                         else:
                             print(f"Warning: URL did not return an image content-type ({content_type}). Skipping download.")
                             status_var.set(f"Added '{book_details['Title']}' (Cover URL was not an image).")

                     # Handle potential errors during download/save
                     except RequestsExceptions.RequestException as img_e:
                         print(f"Error downloading image {cover_url}: {img_e}")
                         messagebox.showwarning("Image Download Failed", f"Could not download cover image:\n{img_e}")
                         status_var.set(f"Added '{book_details['Title']}' (Cover download failed).")
                     except IOError as io_e:
                         print(f"Error saving image to {local_image_path}: {io_e}")
                         messagebox.showwarning("Image Save Failed", f"Could not save cover image locally:\n{io_e}")
                         status_var.set(f"Added '{book_details['Title']}' (Cover save failed).")
                 # else: Error message handled by ensure_covers_dir

            else: # No cover URL found in API response
                print("No cover image URL/ID found in API response.")
                status_var.set(f"Added '{book_details['Title']}' (No cover found).")


            # --- Add to collection, Save, Update GUI ---
            collection.append(book_details)
            # Sorting now happens within save_collection_to_file

            status_var.set(f"Saving '{book_details['Title']}' to collection file...")
            root.update_idletasks()

            if save_collection_to_file(): # Save includes sorting and the new book
                 update_collection_treeview() # Refresh the treeview with new item

                 # Select the newly added item in the treeview for immediate feedback
                 try:
                     if collection_tree.exists(cleaned_isbn):
                         collection_tree.selection_set(cleaned_isbn) # Select
                         collection_tree.focus(cleaned_isbn)        # Set focus
                         collection_tree.see(cleaned_isbn)          # Scroll to make visible
                         display_selected_book_details()            # Show its details
                 except tk.TclError as e:
                      print(f"Error selecting new item in treeview: {e}")


                 status_var.set(f"Book '{book_details['Title']}' added and collection saved.")
                 isbn_entry.delete(0, tk.END) # Clear entry field on success
            else:
                 # Save failed, message shown by save_collection_to_file
                 status_var.set(f"Book '{book_details['Title']}' added to memory, but FAILED TO SAVE file.")
                 # Decide if you want to remove from memory:
                 # collection.pop() # Remove the last added item
                 # update_collection_treeview() # Refresh tree to reflect removal

        else: # User clicked "No" on confirmation dialog
            status_var.set("Add cancelled by user.")

    # --- API/Network Error Handling ---
    except RequestsExceptions.HTTPError as http_err:
         messagebox.showerror("HTTP Error", f"Failed to fetch data. Server returned: {http_err}\nURL: {url}")
         status_var.set(f"HTTP Error: {http_err.response.status_code}")
    except RequestsExceptions.Timeout:
        messagebox.showerror("Timeout", f"The request timed out while connecting to OpenLibrary.\nCheck your internet connection.\nURL: {url}")
        status_var.set("Error: Request timed out.")
    except RequestsExceptions.RequestException as req_e:
        messagebox.showerror("Network Error", f"A network error occurred:\n{req_e}\nURL: {url}")
        status_var.set(f"Network Error.")
    except JSONDecodeError:
        messagebox.showerror("API Error", f"Received invalid data format from OpenLibrary.\nURL: {url}")
        status_var.set("Error decoding server response.")
    except Exception as e:
        messagebox.showerror("Unexpected Error", f"An unexpected error occurred:\n{e}")
        status_var.set("An unexpected error occurred.")
        print(f"Caught general exception during fetch/add: {type(e).__name__} - {e}") # Log details

    # --- Ensure focus returns to entry field ---
    if isbn_entry: isbn_entry.focus()


# --- GUI Setup ---

def main():
    """Sets up the main Tkinter window and widgets."""
    global root, isbn_entry, collection_tree, status_bar, status_var
    global details_frame, detail_labels, image_label, placeholder_photo
    global read_status_var, read_status_checkbutton # Make accessible

    # --- Root Window ---
    root = tk.Tk()
    root.title("Librarian v0.4")
    root.geometry("850x650") # Adjusted size
    # Set minimum size to prevent UI elements overlapping badly
    root.minsize(600, 450)


    # --- Load Placeholder Image Early ---
    load_placeholder_image()
    if placeholder_photo is None:
        # Handle critical failure if placeholder couldn't be loaded/created
        messagebox.showerror("Startup Error", "Failed to load or create essential placeholder image. Exiting.")
        root.destroy()
        return

    # --- Configure Root Window Resizing ---
    # Allow the row containing the main content (PanedWindow) to expand vertically
    root.rowconfigure(1, weight=1)
    # Allow the column containing the main content to expand horizontally
    root.columnconfigure(0, weight=1)


    # --- Input Frame (Top) ---
    input_frame = ttk.Frame(root, padding="10")
    input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E))
    # Allow the entry widget's column to expand
    input_frame.columnconfigure(1, weight=1)

    ttk.Label(input_frame, text="Enter ISBN:").grid(row=0, column=0, padx=(0, 5), sticky=tk.W)
    isbn_entry = ttk.Entry(input_frame, width=30)
    isbn_entry.grid(row=0, column=1, sticky=(tk.W, tk.E))
    # Button to trigger the fetch/add process
    add_button = ttk.Button(input_frame, text="Fetch & Add Book", command=fetch_and_add_book)
    add_button.grid(row=0, column=2, padx=(5, 0))
    # Bind Enter key in the entry field to the same action
    isbn_entry.bind("<Return>", lambda event=None: fetch_and_add_book())


    # --- Main Content Area (Paned Window for resizeable split) ---
    main_pane = ttk.PanedWindow(root, orient=tk.HORIZONTAL)
    # Make the PanedWindow fill the available space in row 1, col 0
    main_pane.grid(row=1, column=0, sticky=(tk.N, tk.S, tk.E, tk.W), padx=10, pady=(0, 10))


    # --- Left Pane: Collection Treeview ---
    tree_frame = ttk.Frame(main_pane, padding=(0, 0, 5, 0)) # Padding allows seeing pane handle
    # Allow treeview row/column to expand within its frame
    tree_frame.rowconfigure(0, weight=1)
    tree_frame.columnconfigure(0, weight=1)

    # Define columns for the Treeview (internal names)
    columns = ('title', 'author')
    collection_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse') # 'browse' = single selection

    # Define user-visible headings
    collection_tree.heading('title', text='Title')
    collection_tree.heading('author', text='Author')

    # Configure column properties (adjust widths as desired)
    collection_tree.column('title', width=250, minwidth=150, stretch=tk.YES)
    collection_tree.column('author', width=150, minwidth=100, stretch=tk.YES)

    # Add vertical scrollbar
    tree_scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=collection_tree.yview)
    collection_tree.configure(yscrollcommand=tree_scrollbar.set)

    # Layout Treeview and Scrollbar using grid
    collection_tree.grid(row=0, column=0, sticky=(tk.N, tk.S, tk.E, tk.W))
    tree_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))

    # Bind the selection event to update the details panel
    collection_tree.bind('<<TreeviewSelect>>', display_selected_book_details)

    # Add the tree frame to the left side of the PanedWindow
    main_pane.add(tree_frame, weight=2) # Give treeview more initial space


    # --- Right Pane: Details Frame ---
    details_frame = ttk.Frame(main_pane, padding=(10, 5, 10, 5)) # Padding around details
    # Allow the value column (column 1) to expand horizontally
    details_frame.columnconfigure(1, weight=1)

    row_num = 0
    # Image Label (top of details)
    image_label = ttk.Label(details_frame, image=placeholder_photo, anchor=tk.N) # Anchor North
    image_label.image = placeholder_photo # Keep reference!
    # Span both columns, add padding below
    image_label.grid(row=row_num, column=0, columnspan=2, pady=(0, 15), sticky=tk.N + tk.W + tk.E)
    row_num += 1

    # --- Text Details Labels (using FIELDNAMES for order, excluding handled ones) ---
    text_display_fields = [f for f in FIELDNAMES if f not in ('ImagePath', 'ReadStatus')]
    for field in text_display_fields:
        # Field Name Label (e.g., "Title:")
        ttk.Label(details_frame, text=f"{field}:", anchor=tk.NW).grid(row=row_num, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=1)
        # Field Value Label (holds the actual data)
        # Use wraplength for potentially long fields
        wrap_len = 300 if field in ['Title', 'Author', 'Publisher'] else 0
        value_label = ttk.Label(details_frame, text="N/A", anchor=tk.NW, wraplength=wrap_len, justify=tk.LEFT)
        value_label.grid(row=row_num, column=1, sticky=(tk.W, tk.E, tk.N), pady=1)
        # Store the value label in the dictionary for easy updating
        detail_labels[field] = value_label
        row_num += 1

    # --- Read Status Checkbutton ---
    ttk.Label(details_frame, text="Read Status:", anchor=tk.NW).grid(row=row_num, column=0, sticky=(tk.W, tk.N), padx=(0, 10), pady=3)
    # Initialize the tk.StringVar to hold the checkbutton state ('Yes' or 'No')
    read_status_var = tk.StringVar()
    # Create the Checkbutton
    read_status_checkbutton = ttk.Checkbutton(details_frame,
                                              text="Read", # Optional text next to checkbox
                                              variable=read_status_var, # Link to the StringVar
                                              onvalue='Yes',    # Value when checked
                                              offvalue='No',    # Value when unchecked
                                              command=toggle_read_status, # Function to call on click
                                              state=tk.DISABLED) # Start disabled until book selected
    read_status_checkbutton.grid(row=row_num, column=1, sticky=(tk.W, tk.N), pady=3)
    row_num += 1

    # Add the details frame to the right side of the PanedWindow
    main_pane.add(details_frame, weight=1) # Give details less initial space


    # --- Bottom Action/Status Frame ---
    bottom_frame = ttk.Frame(root, padding=(10, 5, 10, 10))
    bottom_frame.grid(row=2, column=0, sticky=(tk.W, tk.E))
    # Allow status bar area (column 1) to expand
    bottom_frame.columnconfigure(1, weight=1)

    # Manual Save button
    save_button = ttk.Button(bottom_frame, text="Save Collection", command=save_collection_to_file)
    save_button.grid(row=0, column=0, sticky=tk.W)

    # Status Bar
    status_var = tk.StringVar()
    status_bar = ttk.Label(bottom_frame, textvariable=status_var, anchor=tk.W, relief=tk.SUNKEN, padding=(5, 2))
    status_bar.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(10, 0))
    status_var.set("Initializing...")


    # --- Initial Setup and Main Loop ---
    ensure_covers_dir()          # Make sure the covers directory exists
    load_collection_on_start()   # Load data, populate tree, clear details
    if isbn_entry: isbn_entry.focus() # Set focus to ISBN entry field

    # --- Window Closing Behavior ---
    def on_closing():
        """Handles window close event."""
        # Future: Could add check for unsaved changes if needed
        print("Closing application.")
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing) # Call on_closing when 'X' is clicked
    root.mainloop() # Start the Tkinter event loop

# --- Script Execution Entry Point ---
if __name__ == "__main__":
    # --- Set DPI Awareness (Windows specific, optional but recommended) ---
    try:
        from ctypes import windll
        # Try modern context awareness first
        windll.shcore.SetProcessDpiAwarenessContext(-2) # Per Monitor v2
        print("DPI Awareness set (Per Monitor v2).")
    except AttributeError:
         # Fallback for older Windows
        try:
            windll.user32.SetProcessDPIAware()
            print("DPI Awareness set (System Aware).")
        except AttributeError:
            print("Could not set DPI awareness (user32.SetProcessDPIAware not found).")
        except Exception as dpi_e:
             print(f"Error setting legacy DPI awareness: {dpi_e}")
    except ImportError:
        print("ctypes not available (non-Windows?). Skipping DPI awareness setting.")
    except Exception as e:
        print(f"An error occurred during DPI awareness setting: {e}")

    # --- Run the main application ---
    main()