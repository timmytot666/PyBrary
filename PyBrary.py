# main_app.py
#
# Implements a PySide6 desktop application for managing a personal book collection.
# Features include:
# - Adding books via ISBN lookup (using OpenLibrary API).
# - Storing book details (title, author, publisher, published date, cover image).
# - Displaying the collection in a list view.
# - Showing detailed information for a selected book.
# - A horizontally scrollable carousel of book covers for quick navigation.
# - Marking books as "Read" or "Unread".
# - Searching the collection by title, author, ISBN, or publisher.
# - Saving and loading the collection from/to a CSV file.
# - Basic QSS styling for a modern look and feel.

import sys
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QSplitter,
    QListWidget,
    QListWidgetItem, 
    QAbstractItemView, 
    QCheckBox,
    QStatusBar,
    QMessageBox, 
    QScrollArea, 
)
from PySide6.QtCore import Qt, QSize, Signal 
from PySide6.QtGui import QPalette, QColor, QPixmap 

import os 
import csv 
import json 
import requests 
import requests.exceptions 
from datetime import datetime 
from PIL import Image # Pillow library for image manipulation (e.g., creating placeholder)

# --- Application Stylesheet ---
# Defines the overall look and feel of the application using Qt Style Sheets (QSS).
APP_STYLESHEET = """
/* General */
QMainWindow, QWidget {
    background-color: #F4F4F4; /* Slightly off-white background */
    color: #333333; 
    font-family: "Segoe UI", Arial, sans-serif; /* Common modern fonts */
    font-size: 10pt;
}

/* Buttons */
QPushButton {
    background-color: #0078D7; /* Primary blue */
    color: white;
    border: 1px solid #005A9E; /* Darker blue border */
    padding: 8px 15px;
    border-radius: 4px;
    font-size: 10pt;
}
QPushButton:hover {
    background-color: #005A9E; /* Darker blue on hover */
}
QPushButton:pressed {
    background-color: #003C6A; /* Even darker blue when pressed */
}

/* LineEdits */
QLineEdit {
    padding: 6px;
    border: 1px solid #BDBDBD; /* Grey border */
    border-radius: 4px;
    background-color: #FFFFFF; /* White background */
    font-size: 10pt;
}
QLineEdit:focus {
    border: 1px solid #0078D7; /* Blue border on focus */
    background-color: #E6F2FF; /* Light blueish background on focus */
}

/* ListWidget for book collection display */
QListWidget {
    background-color: white;
    border: 1px solid #DCDCDC; /* Light grey border */
    border-radius: 4px;
    font-size: 10pt;
    /* alternate-background-color: #F9F9F9; */ /* Can be enabled for striped rows */
}
QListWidget::item {
    padding: 8px;
    border-bottom: 1px solid #EEEEEE; /* Separator line for items */
}
QListWidget::item:selected {
    background-color: #0078D7; /* Blue selection background */
    color: white;
    border-left: 3px solid #005A9E; /* Accent for selected item */
}
QListWidget::item:hover {
    background-color: #E0E0E0; /* Light grey hover */
    color: #222222;
}

/* General Labels */
QLabel {
    font-size: 10pt;
    padding: 2px; 
}

/* CheckBox for "Read Status" */
QCheckBox {
    spacing: 8px; /* Space between indicator and text */
    font-size: 10pt;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #777777;
    border-radius: 3px;
    background-color: #FFFFFF;
}
QCheckBox::indicator:hover {
    border: 1px solid #0078D7;
}
QCheckBox::indicator:checked {
    background-color: #0078D7; /* Blue background when checked */
    border-color: #005A9E;
    /* A real checkmark image would be better but requires resource handling. */
    /* For simplicity, a colored box is used. */
}
QCheckBox::indicator:checked:hover {
    background-color: #005A9E;
    border-color: #003C6A;
}

/* StatusBar */
QStatusBar {
    background-color: #E8E8E8; /* Light grey status bar */
    color: #444444;
    padding: 4px;
    font-size: 9pt;
    border-top: 1px solid #D0D0D0;
}

/* Carousel Scroll Area */
QScrollArea {
    border: 1px solid #DCDCDC;
    border-radius: 4px;
    background-color: #FFFFFF; 
}

/* Carousel Cover Labels */
ClickableCoverLabel {
    padding: 3px;
    border: 2px solid transparent; /* Transparent border initially */
    border-radius: 3px; 
    background-color: #EAEAEA; /* Light background for the label itself */
}
ClickableCoverLabel:hover {
    border: 2px solid #0078D7; /* Blue border on hover */
    background-color: #F0F0F0;
}

/* Splitter Handle */
QSplitter::handle {
    background-color: #D0D0D0; 
    border: 1px solid #B0B0B0; 
    width: 6px; /* For horizontal splitter */
    margin: 2px; 
    border-radius: 3px;
}
QSplitter::handle:hover {
    background-color: #B8B8B8; 
}
QSplitter::handle:pressed {
    background-color: #A0A0A0; 
}

/* ScrollBar Styling */
QScrollBar:horizontal {
    border: 1px solid #C0C0C0;
    background: #F0F0F0;
    height: 12px; 
    margin: 0px 15px 0 15px; 
    border-radius: 6px;
}
QScrollBar::handle:horizontal {
    background: #A0A0A0; 
    min-width: 20px;
    border-radius: 5px;
    border: 1px solid #888888;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    border: 1px solid #C0C0C0;
    background: #D8D8D8;
    width: 14px;
    border-radius: 6px;
    subcontrol-origin: margin;
}
QScrollBar::add-line:horizontal { subcontrol-position: right; }
QScrollBar::sub-line:horizontal { subcontrol-position: left; }
QScrollBar::add-line:horizontal:hover, QScrollBar::sub-line:horizontal:hover { background: #C0C0C0; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }

QScrollBar:vertical {
    border: 1px solid #C0C0C0;
    background: #F0F0F0;
    width: 12px;
    margin: 15px 0 15px 0;
    border-radius: 6px;
}
QScrollBar::handle:vertical {
    background: #A0A0A0;
    min-height: 20px;
    border-radius: 5px;
    border: 1px solid #888888;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: 1px solid #C0C0C0;
    background: #D8D8D8;
    height: 14px;
    border-radius: 6px;
    subcontrol-origin: margin;
}
QScrollBar::add-line:vertical { subcontrol-position: bottom; }
QScrollBar::sub-line:vertical { subcontrol-position: top; }
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover { background: #C0C0C0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
"""

# --- Constants ---
# Defines the field names for the book data, used in CSV operations and internal data structures.
FIELDNAMES = [
    "ISBN", "Title", "Author", "Publisher", "PublishedDate", 
    "ImagePath", "DateAdded", "ReadStatus"
]
COLLECTION_FILE = "library_collection.csv"  # Filename for storing the book collection.
COVERS_DIR = "covers"  # Directory to store downloaded cover images.
PLACEHOLDER_IMAGE_NAME = "placeholder.png"  # Filename for the default placeholder cover image.
MAX_IMAGE_WIDTH = 150  # Max width for cover image in the detail view.
MAX_IMAGE_HEIGHT = 220 # Max height for cover image in the detail view.

# --- Global Data ---
collection = []  # In-memory list holding dictionaries, where each dictionary represents a book.

# --- Custom Widgets ---
class ClickableCoverLabel(QLabel):
    """
    A custom QLabel subclass that emits a 'clicked' signal when pressed.
    It's used to display book covers in the carousel and make them interactive.
    The signal emits the associated book data.
    """
    clicked = Signal(object) # Signal to emit when the label is clicked, carrying book data.

    def __init__(self, parent=None):
        """Initializes the ClickableCoverLabel."""
        super().__init__(parent)
        self._book_data = None  # Stores the book data associated with this cover.
        self.setCursor(Qt.CursorShape.PointingHandCursor) # Changes cursor to indicate clickability.

    def set_book_data(self, book_data):
        """Stores the book data dictionary for this label."""
        self._book_data = book_data

    def mousePressEvent(self, event):
        """Handles mouse press events. Emits 'clicked' signal on left-button press."""
        if event.button() == Qt.MouseButton.LeftButton and self._book_data:
            self.clicked.emit(self._book_data)
        super().mousePressEvent(event) # Call base class implementation.

# --- Helper Functions ---
def get_script_directory():
    """
    Returns the absolute directory path of the currently executing script.
    This is useful for locating resources like CSV files or cover images relative to the script.
    """
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def ensure_covers_dir():
    """
    Ensures that the directory for storing cover images exists.
    If it doesn't exist, this function attempts to create it.
    Shows a critical error message if directory creation fails.
    
    Returns:
        bool: True if the directory exists or was created successfully, False otherwise.
    """
    covers_path = os.path.join(get_script_directory(), COVERS_DIR)
    if not os.path.exists(covers_path):
        try:
            os.makedirs(covers_path)
            # print(f"Debug: Created covers directory at {covers_path}") # For debugging
        except OSError as e:
            QMessageBox.critical(None, "Directory Creation Error", f"Could not create covers directory at:\n{covers_path}\n\nError: {e}")
            return False
    return True

def clean_isbn(isbn_string):
    """
    Removes hyphens and spaces from an ISBN string to standardize it.
    
    Args:
        isbn_string (str): The ISBN string to clean.
        
    Returns:
        str: The cleaned ISBN string.
    """
    return isbn_string.replace("-", "").replace(" ", "")

def _sort_collection():
    """
    Sorts the global 'collection' list in-place.
    The primary sort key is 'Title' (case-insensitive), and the secondary key is 'Author' (case-insensitive).
    """
    global collection
    collection.sort(key=lambda x: (str(x.get('Title', '')).lower(), str(x.get('Author', '')).lower()))

def save_collection_to_file():
    """
    Saves the current global 'collection' to a CSV file.
    The CSV file path is determined by 'COLLECTION_FILE' in the script's directory.
    Shows a critical error message if saving fails.
    
    Returns:
        bool: True if saving was successful, False otherwise.
    Side effects:
        Writes to the filesystem.
    """
    file_path = os.path.join(get_script_directory(), COLLECTION_FILE)
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()
            writer.writerows(collection)
        return True
    except IOError as e:
        QMessageBox.critical(None, "File Save Error", f"Could not save collection to file:\n{file_path}\n\nError: {e}\n\nPlease check file permissions or disk space.")
        return False

# --- API & Download Helper Functions ---
def fetch_book_details_openlibrary(isbn):
    """
    Fetches book details from the OpenLibrary API using a given ISBN.
    
    Args:
        isbn (str): The ISBN of the book to fetch.
        
    Returns:
        dict or None: A dictionary containing book details if successful, 
                      or None if an error occurs or the book is not found.
                      The dictionary includes 'cover_id' if a cover is available.
    """
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    # print(f"Debug: Fetching from OpenLibrary: {url}") # For debugging
    try:
        response = requests.get(url, timeout=15) # Increased timeout for potentially slow connections
        response.raise_for_status() # Raises HTTPError for bad responses (4XX or 5XX)
        book_data = response.json()

        details = {"ISBN": isbn, "Title": book_data.get("title", "N/A")}
        
        authors = book_data.get("authors", [])
        if authors:
            author_names = []
            for author_ref in authors[:2]: # Limit to first 2 authors for brevity and to reduce API calls
                if 'key' not in author_ref: 
                    author_names.append("Author data format error")
                    continue
                author_api_url = f"https://openlibrary.org{author_ref['key']}.json"
                try:
                    author_response = requests.get(author_api_url, timeout=5)
                    author_response.raise_for_status()
                    author_data = author_response.json()
                    author_names.append(author_data.get("name", "Unknown Author"))
                except requests.exceptions.RequestException:
                    author_names.append("Author fetch error") 
            details["Author"] = ", ".join(author_names) if author_names else "N/A"
        else:
            details["Author"] = "N/A"
        
        details["Publisher"] = ", ".join(book_data.get("publishers", [])[:2]) if book_data.get("publishers") else "N/A"
        details["PublishedDate"] = book_data.get("publish_date", "N/A")
        details["ImagePath"] = "" # Placeholder; will be filled by download_cover_image if successful

        # Extract cover ID if available
        if "covers" in book_data and book_data["covers"] and isinstance(book_data["covers"], list):
            positive_cover_ids = [cid for cid in book_data["covers"] if isinstance(cid, int) and cid > 0]
            if positive_cover_ids:
                details["cover_id"] = positive_cover_ids[0]
            elif book_data["covers"] and isinstance(book_data["covers"][0], int) and book_data["covers"][0] != -1:
                details["cover_id"] = book_data["covers"][0]
        return details

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            QMessageBox.warning(None, "Book Not Found", f"Book with ISBN {isbn} was not found on OpenLibrary.")
        else:
            QMessageBox.warning(None, "API Request Error", f"An HTTP error occurred while fetching book details:\n{e}\n(ISBN: {isbn})")
    except requests.exceptions.ConnectionError as e: 
        QMessageBox.warning(None, "Network Error", f"Could not connect to OpenLibrary to fetch book details:\n{e}\nPlease check your internet connection. (ISBN: {isbn})")
    except requests.exceptions.Timeout as e:
        QMessageBox.warning(None, "Request Timeout", f"The request to OpenLibrary timed out while fetching book details:\n{e}\n(ISBN: {isbn})")
    except requests.exceptions.RequestException as e: 
        QMessageBox.warning(None, "API Error", f"An unexpected error occurred while fetching book details:\n{e}\n(ISBN: {isbn})")
    except json.JSONDecodeError: 
        QMessageBox.warning(None, "Invalid Data", f"Received invalid data format from OpenLibrary for ISBN {isbn}. The book might not be available or there's an API issue.")
    return None

def download_cover_image(cover_id, isbn_for_filename):
    """
    Downloads a cover image from OpenLibrary using its cover ID.
    Saves the image to the 'covers' directory using the book's ISBN as the filename.
    
    Args:
        cover_id (int or str): The OpenLibrary cover ID.
        isbn_for_filename (str): The ISBN used to name the downloaded image file.
        
    Returns:
        str: The relative path to the saved image (e.g., "covers/isbn.jpg") if successful, 
             or an empty string if the download fails or no valid cover is found.
    Side effects:
        Writes an image file to the 'covers' directory.
    """
    if not cover_id or cover_id == -1: # -1 often indicates no cover
        return ""

    image_filename = f"{clean_isbn(isbn_for_filename)}.jpg"
    full_image_path = os.path.join(get_script_directory(), COVERS_DIR, image_filename)
    relative_image_path = os.path.join(COVERS_DIR, image_filename)
    
    # Attempt to download Medium size cover
    image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
    # print(f"Debug: Downloading cover from {image_url} for ISBN {isbn_for_filename}") # For debugging

    try:
        response = requests.get(image_url, stream=True, timeout=15)
        response.raise_for_status() # Check for HTTP errors

        # Verify content type to ensure it's an image
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            # print(f"Debug: Expected an image, but got content-type: {content_type} for cover ID {cover_id}")
            return "" # Not an image, so skip

        with open(full_image_path, 'wb') as f: 
            for chunk in response.iter_content(chunk_size=8192): # Read in chunks
                f.write(chunk)
        
        # Verify the downloaded image is valid using Pillow
        try:
            img = Image.open(full_image_path)
            img.verify() # Checks for corruption
        except (IOError, SyntaxError, Image.UnidentifiedImageError, Image.DecompressionBombError) as img_err:
            # print(f"Debug: Downloaded cover for ISBN {isbn_for_filename} (ID {cover_id}) is corrupted or invalid: {img_err}. Deleting.")
            if os.path.exists(full_image_path): 
                try: os.remove(full_image_path) # Clean up bad file
                except OSError: pass # Ignore if deletion fails for some reason
            return "" # Return empty if image is bad
        
        return relative_image_path

    except requests.exceptions.RequestException: # Catches HTTPError, ConnectionError, Timeout, etc.
        # print(f"Debug: Network or HTTP error downloading cover {cover_id} (ISBN {isbn_for_filename}): {e}")
        # Silently fail for cover download issues; a placeholder will be used.
        # Clean up partially downloaded file if it exists and an error occurred
        if os.path.exists(full_image_path):
            try: os.remove(full_image_path)
            except OSError: pass
    return ""


class MainWindow(QMainWindow):
    """
    Main application window for the Librarian Qt application.
    Handles UI layout, interactions, data management, and API communication.
    """
    def __init__(self):
        """Initializes the MainWindow, sets up UI, and connects signals."""
        super().__init__()
        self.setWindowTitle("Librarian Qt - Personal Book Collection Manager") 
        self.resize(950, 750) # Adjusted for better layout visibility

        # --- Central Widget and Main Layout ---
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Top Input Area (ISBN, Fetch, Search, Save) ---
        top_area_widget = QWidget()
        top_area_layout = QHBoxLayout(top_area_widget)
        
        self.isbn_input = QLineEdit()
        self.isbn_input.setPlaceholderText("Enter ISBN to add a book...")
        top_area_layout.addWidget(self.isbn_input)
        
        self.fetch_button = QPushButton("Fetch & Add Book")
        self.fetch_button.setToolTip("Fetch book details using ISBN and add to collection.")
        top_area_layout.addWidget(self.fetch_button)
        
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("Search by Title, Author, ISBN, Publisher...")
        top_area_layout.addWidget(self.search_bar)
        
        self.save_button = QPushButton("Save Collection")
        self.save_button.setToolTip("Manually save the current collection to file.")
        top_area_layout.addWidget(self.save_button)
        main_layout.addWidget(top_area_widget)

        # --- Carousel Area (Scrollable Book Covers) ---
        self.carousel_scroll_area = QScrollArea()
        self.carousel_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.carousel_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.carousel_scroll_area.setWidgetResizable(True) 
        self.carousel_scroll_area.setFixedHeight(180) # Fixed height for the carousel display
        
        self.carousel_content_widget = QWidget() 
        self.carousel_layout = QHBoxLayout(self.carousel_content_widget)
        self.carousel_layout.setContentsMargins(10,5,10,5) # Padding around the carousel items
        self.carousel_layout.setSpacing(10) # Spacing between cover images
        self.carousel_scroll_area.setWidget(self.carousel_content_widget)
        main_layout.addWidget(self.carousel_scroll_area)

        # --- Main Content Area (Splitter: Collection List | Book Details) ---
        main_content_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left Pane: Collection List
        self.collection_view_placeholder = QListWidget()
        self.collection_view_placeholder.setToolTip("List of books in your collection.")
        main_content_splitter.addWidget(self.collection_view_placeholder)
        
        # Right Pane: Item Detail View
        item_detail_view_widget = QWidget()
        item_detail_layout = QVBoxLayout(item_detail_view_widget)
        
        self.cover_image_placeholder = QLabel("Cover Image") 
        self.cover_image_placeholder.setFixedSize(150,220) # Standard cover aspect ratio
        self.cover_image_placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.cover_image_placeholder.setStyleSheet(
            "border: 1px dashed #AAAAAA; background-color: #E0E0E0; color: #777777; font-style: italic;"
        ) # Basic styling for empty placeholder
        item_detail_layout.addWidget(self.cover_image_placeholder, 0, Qt.AlignmentFlag.AlignCenter)
        
        self.title_placeholder = QLabel("Title: N/A")
        self.title_placeholder.setStyleSheet("font-size: 12pt; font-weight: bold; padding-bottom: 5px;")
        item_detail_layout.addWidget(self.title_placeholder)
        
        self.author_placeholder = QLabel("Author(s): N/A")
        item_detail_layout.addWidget(self.author_placeholder)
        
        self.isbn_placeholder_detail = QLabel("ISBN: N/A")
        item_detail_layout.addWidget(self.isbn_placeholder_detail)
        
        self.publisher_placeholder = QLabel("Publisher: N/A")
        item_detail_layout.addWidget(self.publisher_placeholder)
        
        self.published_date_placeholder = QLabel("Published Date: N/A")
        item_detail_layout.addWidget(self.published_date_placeholder)
        
        self.dateadded_placeholder = QLabel("Date Added: N/A")
        item_detail_layout.addWidget(self.dateadded_placeholder)
        
        self.read_status_checkbox = QCheckBox("Mark as Read")
        item_detail_layout.addWidget(self.read_status_checkbox)
        
        item_detail_layout.addStretch() # Pushes details to the top
        main_content_splitter.addWidget(item_detail_view_widget)
        
        main_content_splitter.setSizes([250, 650]) # Initial sizing for list and detail panes
        main_layout.addWidget(main_content_splitter, 1) # Make splitter stretchable

        # --- Status Bar ---
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Application Ready.")

        # --- Initial Setup and Data Loading ---
        ensure_covers_dir() # Ensure 'covers' directory exists
        self.load_placeholder_pixmap() # Load or create the default cover image
        self.load_collection() # Load existing book collection from CSV
        self.populate_collection_view() # Populate the main list view
        self.populate_carousel() # Populate the cover carousel

        # --- Connect Signals to Slots ---
        self.collection_view_placeholder.itemSelectionChanged.connect(self.display_selected_book)
        self.save_button.clicked.connect(self.manual_save_collection)
        self.fetch_button.clicked.connect(self.fetch_and_add_book_action)
        self.read_status_checkbox.stateChanged.connect(self.toggle_read_status)
        self.search_bar.textChanged.connect(self.filter_collection_view)

    def populate_carousel(self):
        """
        Populates the carousel QScrollArea with clickable book cover images.
        Clears any existing items before adding new ones.
        Uses the global 'collection' as the data source.
        """
        # Clear existing widgets from carousel_layout to prevent duplicates
        while self.carousel_layout.count():
            child = self.carousel_layout.takeAt(0)
            if child.widget(): 
                child.widget().deleteLater() # Proper way to remove and delete widgets
        
        global collection
        if not collection:
            self.carousel_content_widget.setMinimumWidth(0) # Reset width if no items
            # Optionally, display a placeholder message in the carousel itself
            # empty_carousel_label = QLabel("No books in collection.")
            # empty_carousel_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            # self.carousel_layout.addWidget(empty_carousel_label)
            return

        cover_height = 140 # Desired display height for covers in the carousel
        total_content_width = 0
        # Determine spacing from layout, default if not set
        spacing = self.carousel_layout.spacing() if self.carousel_layout.spacing() != -1 else 5 

        for book in collection:
            cover_label = ClickableCoverLabel() # Custom clickable label
            cover_label.set_book_data(book) # Associate book data with the label

            pixmap_to_display = self.placeholder_pixmap # Default to placeholder
            image_path_str = book.get('ImagePath', '')

            if image_path_str: # If an image path is specified
                full_image_path = os.path.join(get_script_directory(), image_path_str)
                if os.path.exists(full_image_path):
                    loaded_pixmap = QPixmap(full_image_path)
                    if not loaded_pixmap.isNull(): # Check if pixmap loaded successfully
                        pixmap_to_display = loaded_pixmap
            
            # Scale the chosen pixmap (either actual cover or placeholder)
            scaled_pixmap = pixmap_to_display.scaledToHeight(cover_height, Qt.TransformationMode.SmoothTransformation)
            cover_label.setPixmap(scaled_pixmap)
            cover_label.setFixedSize(scaled_pixmap.width(), cover_height) # Set fixed size for layout consistency
            
            cover_label.setToolTip(f"Title: {book.get('Title', 'N/A')}\nAuthor: {book.get('Author', 'N/A')}")
            cover_label.clicked.connect(self.on_carousel_cover_clicked) # Connect click signal
            
            self.carousel_layout.addWidget(cover_label)
            total_content_width += scaled_pixmap.width()
            if self.carousel_layout.count() > 1: # Add spacing if it's not the first item
                total_content_width += spacing
        
        # Set minimum width for the content widget to enable scrolling if content overflows
        self.carousel_content_widget.setMinimumWidth(max(0, total_content_width))

    def on_carousel_cover_clicked(self, book_data):
        """
        Handles the 'clicked' signal from a ClickableCoverLabel in the carousel.
        Finds the corresponding book in the main QListWidget and selects it.
        
        Args:
            book_data (dict): The book data associated with the clicked cover.
        """
        target_isbn = book_data.get("ISBN")
        if not target_isbn: 
            QMessageBox.warning(self, "Carousel Interaction Error", "Clicked cover has no ISBN associated.")
            return

        # Iterate through items in the QListWidget to find the matching book
        for i in range(self.collection_view_placeholder.count()):
            item = self.collection_view_placeholder.item(i)
            item_book_data = item.data(Qt.UserRole) # Book data stored with the item
            if item_book_data and item_book_data.get("ISBN") == target_isbn:
                self.collection_view_placeholder.setCurrentItem(item) # Selects the item
                # display_selected_book is triggered automatically by itemSelectionChanged
                self.status_bar.showMessage(f"Selected '{book_data.get('Title','N/A')}' from carousel.",3000)
                return
        
        # Fallback if book is in carousel source but not found in list (should be rare)
        self.status_bar.showMessage(f"Book '{book_data.get('Title','N/A')}' (ISBN: {target_isbn}) not found in the main list. Refreshing views...", 5000)
        self.populate_collection_view() # Attempt to resynchronize the list
        self.populate_carousel() # Also resync carousel, just in case
        # Try selecting again after views are refreshed
        for i in range(self.collection_view_placeholder.count()):
            item = self.collection_view_placeholder.item(i)
            if item.data(Qt.UserRole).get("ISBN") == target_isbn:
                self.collection_view_placeholder.setCurrentItem(item)
                self.status_bar.showMessage(f"Selected '{book_data.get('Title','N/A')}' from carousel after views refresh.",3000)
                return

    def filter_collection_view(self):
        """
        Filters the books displayed in the QListWidget (collection_view_placeholder)
        based on the text entered in the search bar.
        Search is case-insensitive and checks Title, Author, ISBN, and Publisher.
        The carousel is repopulated with all books if the search is cleared.
        """
        search_term = self.search_bar.text().strip().lower()

        if not search_term: # If search bar is empty, show all books
            self.populate_collection_view()
            self.populate_carousel() # Refresh carousel to show all items
            self.status_bar.showMessage("Search cleared. Displaying all books.", 2000)
            return

        # Filter the global collection based on the search term
        filtered_books = [
            book for book in collection if
            search_term in str(book.get('Title','')).lower() or \
            search_term in str(book.get('Author','')).lower() or \
            search_term in str(book.get('ISBN','')).lower() or \
            search_term in str(book.get('Publisher','')).lower()
        ]
        
        self.collection_view_placeholder.clear() # Clear current list items
        if not filtered_books:
            self.status_bar.showMessage(f"No books found matching '{self.search_bar.text().strip()}'.", 3000)
        else:
            for book in filtered_books:
                display_text = f"{book.get('Title','N/A Title')} by {book.get('Author','N/A Author')}"
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, book) # Store full book data with the item
                self.collection_view_placeholder.addItem(item)
            self.status_bar.showMessage(f"Found {len(filtered_books)} matching books.", 3000)
        
        # If current selection is removed by filter, or list is empty, clear detail view
        if not self.collection_view_placeholder.selectedItems():
             self.display_selected_book() # Clears details if no item is selected

    def fetch_and_add_book_action(self):
        """
        Handles the 'Fetch & Add Book' button click.
        Fetches book details using ISBN, allows user confirmation, and adds the book.
        Updates collection, saves to file, and refreshes UI views.
        Side effects: Modifies global 'collection', saves to file, updates UI.
        """
        isbn = clean_isbn(self.isbn_input.text())
        if not isbn: 
            QMessageBox.warning(self,"Input Error","Please enter a valid ISBN."); return
        
        # Check for duplicates before making API calls
        global collection # Explicitly state usage of global
        if any(book.get("ISBN") == isbn for book in collection):
            QMessageBox.information(self,"Duplicate Book",f"The book with ISBN {isbn} is already in your collection."); return
        
        self.status_bar.showMessage(f"Fetching details for ISBN: {isbn}..."); QApplication.processEvents()
        
        book_details = fetch_book_details_openlibrary(isbn)
        if not book_details: # Error messages handled by fetch_book_details_openlibrary
            self.status_bar.showMessage(f"Could not retrieve details for ISBN: {isbn}. See previous messages.",5000)
            return
        
        book_details["ISBN"] = isbn # Ensure the cleaned ISBN used for lookup is stored

        # Download cover image if a cover ID was found by the API
        if book_details.get("cover_id"):
            self.status_bar.showMessage(f"Downloading cover for '{book_details.get('Title','N/A')}'..."); QApplication.processEvents()
            image_path = download_cover_image(book_details.get("cover_id"), isbn)
            book_details["ImagePath"] = image_path # Store relative path
            if image_path:
                 self.status_bar.showMessage(f"Cover downloaded for '{book_details.get('Title','N/A')}'.", 3000)
            else:
                 self.status_bar.showMessage(f"Cover not available or download failed for '{book_details.get('Title','N/A')}'. Using placeholder.", 3000)
        else:
            self.status_bar.showMessage(f"No cover information found for '{book_details.get('Title','N/A')}'. Using placeholder.", 3000)
        
        # User confirmation dialog
        confirm_title = "Confirm Book Addition"
        confirm_text = (
            f"Title: {details.get('Title', 'N/A')}\n"
            f"Author: {details.get('Author', 'N/A')}\n"
            f"Publisher: {details.get('Publisher', 'N/A')}\n"
            f"Published: {details.get('PublishedDate', 'N/A')}\n\n"
            "Add this book to your collection?"
        )
        reply = QMessageBox.question(self, confirm_title, confirm_text, 
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, 
                                     QMessageBox.StandardButton.Yes) # Default to Yes
        if reply == QMessageBox.StandardButton.No:
            self.status_bar.showMessage("Book addition cancelled by user.",3000); return
        
        # Prepare the final book data dictionary ensuring all FIELDNAMES are present
        final_book_data = {field: book_details.get(field, "") for field in FIELDNAMES}
        final_book_data["DateAdded"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        final_book_data["ReadStatus"] = "No" # Default for new books
        if "cover_id" in final_book_data: # Internal field, not for saving
            del final_book_data["cover_id"] 
        
        collection.append(final_book_data)
        _sort_collection() # Maintain sorted order
        
        if save_collection_to_file():
            self.status_bar.showMessage(f"Book '{final_book_data.get('Title')}' added and collection saved.",5000)
            self.populate_collection_view() # Refresh main list
            self.populate_carousel()        # Refresh carousel
            
            # Attempt to select the newly added book in the list view
            for i in range(self.collection_view_placeholder.count()):
                list_item = self.collection_view_placeholder.item(i)
                if list_item and list_item.data(Qt.UserRole).get("ISBN") == isbn:
                    self.collection_view_placeholder.setCurrentItem(list_item)
                    break
            self.isbn_input.clear()
        else: # save_collection_to_file() shows its own critical error
            self.status_bar.showMessage(f"CRITICAL: Failed to save new book '{final_book_data.get('Title')}' to file.",8000)
            # Revert in-memory addition as the save failed
            try: collection.remove(final_book_data) 
            except ValueError: pass # Should not happen if logic is correct
            _sort_collection() 
            self.populate_collection_view() # Refresh views to reflect reverted state
            self.populate_carousel()
        self.isbn_input.setFocus() # Return focus to ISBN input for next entry

    def manual_save_collection(self):
        """
        Handles the 'Save Collection' button click.
        Saves the current state of the global 'collection' to the CSV file.
        """
        self.status_bar.showMessage("Saving collection manually...");
        if save_collection_to_file(): 
            self.status_bar.showMessage("Collection saved successfully.", 5000)
        else: # Error message is shown by save_collection_to_file
            self.status_bar.showMessage("Failed to save collection. Please check error dialogs.", 5000)

    def toggle_read_status(self, state):
        """
        Handles changes to the 'Read Status' checkbox.
        Updates the selected book's 'ReadStatus', saves the collection, and provides feedback.
        
        Args:
            state (int): The new state of the checkbox (Qt.CheckState enum value).
        Side effects: Modifies global 'collection', saves to file, updates UI.
        """
        selected_items = self.collection_view_placeholder.selectedItems()
        # Only proceed if an item is selected and the checkbox is enabled (i.e., a book is selected)
        if not selected_items or not self.read_status_checkbox.isEnabled(): 
            return
        
        book_data = selected_items[0].data(Qt.UserRole)
        if not book_data: return # Should not happen if item is selected

        new_status = "Yes" if self.read_status_checkbox.isChecked() else "No"
        
        # Prevent action if the status hasn't actually changed 
        # (e.g., if setChecked triggered this programmatically without a real change)
        if book_data.get('ReadStatus') == new_status: 
            return
        
        book_data['ReadStatus'] = new_status
        selected_items[0].setData(Qt.UserRole, book_data) # Update data stored with the item
        
        self.status_bar.showMessage(f"Saving read status for '{book_data.get('Title','N/A')}'...");
        if save_collection_to_file(): 
            self.status_bar.showMessage(f"Read status for '{book_data.get('Title','N/A')}' saved.",5000)
        else: # Error message is shown by save_collection_to_file
            self.status_bar.showMessage(f"Failed to save read status for '{book_data.get('Title','N/A')}'. See error dialogs.",5000)
            # Optional: Revert checkbox state if save failed, though this can be complex
            # self.read_status_checkbox.setChecked(book_data.get('ReadStatus','').lower() != 'yes')


    def load_placeholder_pixmap(self):
        """
        Loads the placeholder cover image from file, or creates it if it doesn't exist.
        The loaded QPixmap is stored in `self.placeholder_pixmap`.
        Shows a critical error if creation/loading fails, using a fallback filled QPixmap.
        """
        placeholder_file_path = os.path.join(get_script_directory(), COVERS_DIR, PLACEHOLDER_IMAGE_NAME)
        if not os.path.exists(placeholder_file_path):
            try:
                # Create a simple gray placeholder image with Pillow
                img = Image.new('RGB', (MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT), color=(200, 200, 200)) # type: ignore
                # One could add text like "No Cover" using ImageDraw, but keeping it simple.
                img.save(placeholder_file_path)
                self.placeholder_pixmap = QPixmap(placeholder_file_path)
            except Exception as e: # Broad exception for Pillow/OS errors
                QMessageBox.critical(self,"Placeholder Image Error",f"Could not create placeholder image file:\n{placeholder_file_path}\n\nError: {e}")
                # Fallback to a dynamically created QPixmap if file operations fail
                self.placeholder_pixmap = QPixmap(MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT)
                self.placeholder_pixmap.fill(QColor("lightgrey")) 
        else: # Placeholder file exists
            self.placeholder_pixmap = QPixmap(placeholder_file_path)
        
        # Final check if placeholder is null (e.g., if file was corrupt and QPixmap couldn't load it)
        if self.placeholder_pixmap.isNull():
            QMessageBox.warning(self, "Placeholder Load Warning", f"Failed to load placeholder image from {placeholder_file_path}. Using a fallback color.")
            self.placeholder_pixmap = QPixmap(MAX_IMAGE_WIDTH, MAX_IMAGE_HEIGHT)
            self.placeholder_pixmap.fill(QColor("lightgrey"))

    def load_collection(self):
        """
        Loads the book collection from the CSV file specified by 'COLLECTION_FILE'.
        Populates the global 'collection' list.
        If the file doesn't exist, it's created with headers.
        Handles file errors and CSV format issues.
        Side effects: Modifies global 'collection', reads from filesystem.
        """
        global collection; collection = [] # Clear existing in-memory collection
        collection_file_path = os.path.join(get_script_directory(), COLLECTION_FILE)

        if not os.path.exists(collection_file_path):
            try: # Create an empty CSV file with headers if it doesn't exist
                with open(collection_file_path,'w',newline='',encoding='utf-8') as f:
                    csv.DictWriter(f, fieldnames=FIELDNAMES).writeheader()
                self.status_bar.showMessage(f"Initialized new collection file: {COLLECTION_FILE}")
            except IOError as e: # If creation fails, show error and return with empty collection
                QMessageBox.critical(self, "File Creation Error", f"Could not create collection file:\n{collection_file_path}\n\nError: {e}")
                # No collection to populate views with, they will be empty.
                return 
        else: # File exists, attempt to read it
            try:
                with open(collection_file_path,'r',newline='',encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    # Basic header validation
                    if not reader.fieldnames or not all(fieldname in reader.fieldnames for fieldname in FIELDNAMES):
                        QMessageBox.warning(self,"CSV Format Warning",f"The collection file '{COLLECTION_FILE}' has incorrect or missing headers. Attempting to load anyway, but data might be misinterpreted.")
                    
                    for row in reader:
                        # Ensure all expected fields are present in the book dictionary, defaulting to empty string
                        book_item = {field: row.get(field, "") for field in FIELDNAMES}
                        collection.append(book_item)
                _sort_collection() # Sort after loading
                self.status_bar.showMessage(f"Loaded {len(collection)} books from {COLLECTION_FILE}.")
            except csv.Error as e: # Specific error for CSV parsing issues
                QMessageBox.critical(self,"CSV Read Error",f"Error reading the collection file '{COLLECTION_FILE}':\n{e}\n\nThe file might be corrupted. Please check its format.")
                collection=[] # Reset collection on critical read error
            except Exception as e: # Catch-all for other unexpected errors during file read
                QMessageBox.critical(self,"Collection Load Error",f"An unexpected error occurred while loading the collection from {collection_file_path}:\n{e}"); collection=[]
        
        # If collection is empty after attempting to load (or if file was just created)
        if not collection:
            self.display_selected_book() # Ensure detail view is cleared/shows N/A
        
        self.populate_carousel() # Refresh carousel based on loaded collection (even if empty)

    def populate_collection_view(self):
        """
        Populates the QListWidget (collection_view_placeholder) with books
        from the global 'collection' list. Each item displays title and author.
        Full book data is stored with each item using Qt.UserRole.
        """
        self.collection_view_placeholder.clear() # Clear existing items
        if not collection: 
            # Optionally, display a message in the list itself if empty
            # self.collection_view_placeholder.addItem("No books in collection.")
            return
        
        for book in collection:
            display_text = f"{book.get('Title','N/A Title')} by {book.get('Author','N/A Author')}"
            list_item = QListWidgetItem(display_text)
            list_item.setData(Qt.UserRole, book) # Store the book dictionary with the item
            self.collection_view_placeholder.addItem(list_item)

    def display_selected_book(self):
        """
        Displays the details of the currently selected book from the QListWidget
        in the right-hand detail pane (QLabel placeholders, QCheckBox).
        If no book is selected, clears the detail pane.
        """
        selected_items = self.collection_view_placeholder.selectedItems()
        
        # If no item is selected, clear all detail fields and show placeholder image
        if not selected_items:
            self.title_placeholder.setText("Title: N/A")
            self.author_placeholder.setText("Author(s): N/A")
            self.isbn_placeholder_detail.setText("ISBN: N/A")
            self.publisher_placeholder.setText("Publisher: N/A")
            self.published_date_placeholder.setText("Published Date: N/A")
            self.dateadded_placeholder.setText("Date Added: N/A")
            self.cover_image_placeholder.setPixmap(
                self.placeholder_pixmap.scaled(self.cover_image_placeholder.size(), 
                                               Qt.AspectRatioMode.KeepAspectRatio, 
                                               Qt.TransformationMode.SmoothTransformation)
            )
            self.read_status_checkbox.setChecked(False)
            self.read_status_checkbox.setEnabled(False) # Disable checkbox if no book is selected
            return

        # An item is selected, retrieve its data
        book_data = selected_items[0].data(Qt.UserRole)
        if not book_data: # Should not happen if data is set correctly
            QMessageBox.warning(self, "Display Error", "Could not retrieve data for the selected book.")
            # Clear fields as a precaution
            self.title_placeholder.setText("Title: Error"); self.author_placeholder.setText("Author(s): Error") 
            # ... (clear other fields similarly)
            return

        # Update detail pane labels with book information
        self.title_placeholder.setText(f"Title: {book_data.get('Title','N/A')}")
        self.author_placeholder.setText(f"Author(s): {book_data.get('Author','N/A')}")
        self.isbn_placeholder_detail.setText(f"ISBN: {book_data.get('ISBN','N/A')}")
        self.publisher_placeholder.setText(f"Publisher: {book_data.get('Publisher','N/A')}")
        self.published_date_placeholder.setText(f"Published Date: {book_data.get('PublishedDate','N/A')}")
        self.dateadded_placeholder.setText(f"Date Added: {book_data.get('DateAdded','N/A')}")
        
        # Update cover image
        pixmap_to_display_detail = self.placeholder_pixmap # Default to placeholder
        cover_image_path_str = book_data.get('ImagePath', '')
        if cover_image_path_str:
            full_cover_path = os.path.join(get_script_directory(), cover_image_path_str)
            if os.path.exists(full_cover_path):
                try:
                    loaded_detail_pixmap = QPixmap(full_cover_path)
                    if not loaded_detail_pixmap.isNull():
                        pixmap_to_display_detail = loaded_detail_pixmap
                    else: # Pixmap loaded as null (e.g. corrupted file)
                        self.status_bar.showMessage(f"Warning: Could not load cover for '{book_data.get('Title', 'N/A')}' from {cover_image_path_str}. Using placeholder.", 5000)
                except Exception as e: # Catch any other exception during QPixmap creation
                    self.status_bar.showMessage(f"Error loading cover for '{book_data.get('Title', 'N/A')}': {e}. Using placeholder.", 5000)
            # else: # Path in CSV but file doesn't exist
                # self.status_bar.showMessage(f"Cover image file not found for '{book_data.get('Title', 'N/A')}' at {cover_image_path_str}. Using placeholder.", 3000)
        
        self.cover_image_placeholder.setPixmap(pixmap_to_display_detail.scaled(
            self.cover_image_placeholder.size(), 
            Qt.AspectRatioMode.KeepAspectRatio, 
            Qt.TransformationMode.SmoothTransformation
        ))
        
        # Update Read Status checkbox
        self.read_status_checkbox.setEnabled(True) # Enable for selected book
        self.read_status_checkbox.setChecked(book_data.get('ReadStatus','').lower() == 'yes')

# --- Application Entry Point ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLESHEET) # Apply the global QSS stylesheet
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())
