# PyBrary - Personal Book Collection Manager

Librarian is a desktop application built with Python and Tkinter that helps you manage your personal book collection. It allows you to fetch book details from the OpenLibrary API using an ISBN, store this information locally in a CSV file, and view your collection with book cover images.

## Features

* **Add Books via ISBN:** Enter an ISBN to fetch book details (Title, Author, Publisher, Published Date) from the OpenLibrary API.
* **Local Collection Storage:** Saves your book collection to a `book_collection.csv` file.
* **Cover Image Download:** Attempts to download and save book cover images from OpenLibrary.
* **Display Collection:** Shows your book collection in a sortable list.
* **View Book Details:** Select a book from the list to see its full details and cover image.
* **Read Status Tracking:** Mark books as "Read" or "Unread".
* **Date Added Tracking:** Automatically records the date a book is added to the collection.
* **User-Friendly Interface:** Simple GUI built with Tkinter.
* **Placeholder Image:** Uses a placeholder image if a cover cannot be found or loaded.
* **Error Handling:** Includes basic error handling for API requests, file operations, and image loading.

## Requirements

* Python 3.x
* Pillow (PIL Fork): For image processing.
    ```bash
    pip install Pillow
    ```
* Requests: For making HTTP requests to the OpenLibrary API.
    ```bash
    pip install requests
    ```

## Setup and Installation

1.  **Clone the repository (or download the script):**
    ```bash
    # If you've set up a git repository
    git clone <your-repository-url>
    cd <repository-directory>
    ```
    Alternatively, download `Library RC1.py` (or the final script name) to a directory on your computer.

2.  **Install Dependencies:**
    Open your terminal or command prompt and run:
    ```bash
    pip install Pillow requests
    ```

3.  **Placeholder Image (Optional but Recommended):**
    Create a `placeholder.png` image in the same directory as the script. This image will be displayed if a book's cover image cannot be found or downloaded. The script will create a default gray image if `placeholder.png` is missing, but a custom one might look better. The recommended dimensions are around 150x220 pixels.

4.  **Covers Directory:**
    The script will automatically create a `covers` subdirectory in the same location as the script. This is where downloaded book cover images will be stored. Ensure you have write permissions in the script's directory.

## Usage

1.  **Run the script:**
    ```bash
    python "Library RC1.py"
    ```
    (Replace `"Library RC1.py"` with the actual name of your Python file if you've renamed it).

2.  **Adding a Book:**
    * Enter the ISBN of the book you want to add into the "Enter ISBN" field.
    * Click the "Fetch & Add Book" button or press Enter.
    * The application will search OpenLibrary for the book.
    * A confirmation dialog will appear with the fetched book details. Click "Yes" to add it to your collection.
    * The book's cover image (if available) will be downloaded to the `covers` directory.

3.  **Viewing Your Collection:**
    * The main list on the left displays the Title and Author of the books in your collection.
    * Click on a book in the list to see its full details (including ISBN, Publisher, Published Date, Date Added, and Read Status) and cover image on the right.

4.  **Updating Read Status:**
    * Select a book from the list.
    * In the details panel on the right, click the "Read" checkbox to toggle the book's read status. The change is saved automatically.

5.  **Saving the Collection:**
    * The collection is automatically saved to `book_collection.csv` whenever a book is added or its read status is changed.
    * You can also manually save the collection by clicking the "Save Collection" button.

## File Structure

The script expects and creates the following file/directory structure in the directory where it is run:

.├── Library RC1.py         # Or your script's name
    ├── book_collection.csv    # Stores your book data
        ├── covers/                # Directory for downloaded cover images│   
        ├── ISBN1.jpg│   
        └── ISBN2.jpg│   
        └── ...
    └── placeholder.png        # Optional: Your custom placeholder image
## Error Handling & Logging

* The application displays error messages using dialog boxes for common issues like:
    * Missing Pillow library.
    * Network errors or API timeouts when fetching book data or images.
    * ISBN not found.
    * File I/O errors (loading/saving collection, creating directories).
* Informational messages and some error details are printed to the console, which can be helpful for debugging.

## Future Enhancements (Ideas)

* Editing existing book details.
* Deleting books from the collection.
* More advanced sorting and filtering options.
* Import/Export collection in different formats.
* Custom fields.
* Better UI themes or styling.
