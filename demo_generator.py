import os
import sys # Added for get_script_directory
import csv
import json
import requests
from datetime import datetime
from PIL import Image # Pillow library for image manipulation

# Sample ISBNs
SAMPLE_ISBNS = [
    "9780590353427",  # Harry Potter and the Sorcerer's Stone
    "9780261102384",  # The Hobbit
    "9780743273565",  # The Great Gatsby
    "9780140283334",  # The Catcher in the Rye
    "9781984801958",  # Where the Crawdads Sing
]

# Constants - FIELDNAMES from the original demo_generator.py is more comprehensive
FIELDNAMES = [
    'id', 'title', 'authors', 'illustrators', 'translators', 'editors',
    'publisher', 'published_date', 'description', 'isbn_13', 'isbn_10',
    'page_count', 'categories', 'average_rating', 'ratings_count',
    'info_link', 'cover_image_path', 'tags', 'notes', 'read_status',
    'date_added', 'date_modified', 'openlibrary_id', 'goodreads_id', 'librarything_id'
]
COLLECTION_FILE = 'library_collection.csv' # Same as PyBrary.py
COVERS_DIR = 'covers' # Same as PyBrary.py
PLACEHOLDER_IMAGE_NAME = 'placeholder.png' # Same as PyBrary.py (though not directly used in this script for generation)

# --- Helper Functions (Adapted from PyBrary.py) ---
def get_script_directory():
    """
    Returns the absolute directory path of the currently executing script.
    """
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def ensure_covers_dir():
    """
    Ensures that the directory for storing cover images exists.
    If it doesn't exist, this function attempts to create it.
    Prints an error message if directory creation fails.

    Returns:
        bool: True if the directory exists or was created successfully, False otherwise.
    """
    covers_path = os.path.join(get_script_directory(), COVERS_DIR)
    if not os.path.exists(covers_path):
        try:
            os.makedirs(covers_path)
            print(f"Created covers directory at {covers_path}")
        except OSError as e:
            print(f"Error: Could not create covers directory at:\n{covers_path}\nError: {e}")
            return False
    else:
        print(f"Covers directory '{covers_path}' already exists.")
    return True

def clean_isbn(isbn_string):
    """
    Removes hyphens and spaces from an ISBN string to standardize it.
    """
    return isbn_string.replace("-", "").replace(" ", "")

def fetch_book_details_openlibrary(isbn):
    """
    Fetches book details from the OpenLibrary API using a given ISBN.
    Adapted to use print for messages instead of QMessageBox.

    Returns:
        dict or None: A dictionary containing book details if successful, or None.
    """
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    print(f"Fetching book details from: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        book_data = response.json()

        details = {"isbn_13": isbn, "title": book_data.get("title", "N/A")}

        # Process authors
        authors_data = book_data.get("authors", [])
        author_names = []
        if authors_data:
            for author_ref in authors_data[:2]: # Limit to first 2 authors
                if 'key' in author_ref:
                    author_api_url = f"https://openlibrary.org{author_ref['key']}.json"
                    try:
                        author_response = requests.get(author_api_url, timeout=5)
                        author_response.raise_for_status()
                        author_info = author_response.json()
                        author_names.append(author_info.get("name", "Unknown Author"))
                    except requests.exceptions.RequestException as ae:
                        print(f"Warning: Could not fetch author details for {author_ref.get('key')}: {ae}")
                        author_names.append("Author fetch error")
                else: # Author data might be just a string name in some OpenLibrary entries
                    author_names.append(str(author_ref))

        details["authors"] = ", ".join(author_names) if author_names else "N/A"

        details["publisher"] = ", ".join(book_data.get("publishers", [])[:2]) if book_data.get("publishers") else "N/A"
        details["published_date"] = book_data.get("publish_date", "N/A")

        # ISBNs
        if "isbn_10" in book_data and book_data["isbn_10"]:
            details["isbn_10"] = book_data["isbn_10"][0] # Typically a list
        if "isbn_13" in book_data and book_data["isbn_13"]: # API might return it, ensure it's there
            details["isbn_13"] = book_data["isbn_13"][0] # Typically a list
        else: # Ensure the lookup ISBN is stored as isbn_13 if not otherwise found
             details["isbn_13"] = isbn


        details["page_count"] = book_data.get("number_of_pages", book_data.get("pagination", "N/A"))
        details["categories"] = ", ".join(book_data.get("subjects", [])[:3]) if book_data.get("subjects") else ""
        details["description"] = book_data.get("description", {}).get("value", "") if isinstance(book_data.get("description"), dict) else book_data.get("description", "")

        # Extract cover ID if available
        if "covers" in book_data and book_data["covers"] and isinstance(book_data["covers"], list):
            positive_cover_ids = [cid for cid in book_data["covers"] if isinstance(cid, int) and cid > 0]
            if positive_cover_ids:
                details["cover_id"] = positive_cover_ids[0] # Use the first positive ID
            elif book_data["covers"] and isinstance(book_data["covers"][0], int) and book_data["covers"][0] != -1:
                 details["cover_id"] = book_data["covers"][0] # Fallback to the first one if it's not -1

        # OpenLibrary specific IDs
        if "key" in book_data:
            details["openlibrary_id"] = book_data["key"].split('/')[-1] # e.g. /books/OL7353617M -> OL7353617M

        details["info_link"] = f"https://openlibrary.org/isbn/{isbn}"

        return details

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Warning: Book with ISBN {isbn} was not found on OpenLibrary.")
        else:
            print(f"Warning: HTTP error for ISBN {isbn}: {e}")
    except requests.exceptions.ConnectionError as e:
        print(f"Error: Could not connect to OpenLibrary for ISBN {isbn}: {e}")
    except requests.exceptions.Timeout as e:
        print(f"Error: Request timed out for ISBN {isbn}: {e}")
    except requests.exceptions.RequestException as e:
        print(f"Error: API request failed for ISBN {isbn}: {e}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response from OpenLibrary for ISBN {isbn}.")
    return None

def download_cover_image(cover_id, isbn_for_filename):
    """
    Downloads a cover image from OpenLibrary.
    Adapted to use print for messages.
    Returns relative image path or empty string.
    """
    if not cover_id or cover_id == -1:
        print(f"No valid cover ID for ISBN {isbn_for_filename}. Skipping download.")
        return ""

    image_filename = f"{clean_isbn(isbn_for_filename)}.jpg"
    covers_dir_path = os.path.join(get_script_directory(), COVERS_DIR)
    full_image_path = os.path.join(covers_dir_path, image_filename)
    relative_image_path = os.path.join(COVERS_DIR, image_filename)

    image_url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg" # Try Large size
    print(f"Attempting to download cover from: {image_url}")

    try:
        response = requests.get(image_url, stream=True, timeout=15)
        response.raise_for_status()
        content_type = response.headers.get('content-type', '').lower()
        if not content_type.startswith('image/'):
            print(f"Warning: Expected an image, but got content-type: {content_type} for cover ID {cover_id}. Trying Medium size.")
            # Fallback to Medium size if Large is not an image (e.g. redirect to a page)
            image_url_m = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"
            print(f"Attempting to download cover from: {image_url_m}")
            response = requests.get(image_url_m, stream=True, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"Warning: Medium size also not an image (content-type: {content_type}). No cover downloaded for {isbn_for_filename}.")
                return ""


        with open(full_image_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        # Verify the downloaded image
        try:
            img = Image.open(full_image_path)
            img.verify()
            print(f"Successfully downloaded and verified cover to {relative_image_path}")
            return relative_image_path
        except (IOError, SyntaxError, Image.UnidentifiedImageError, Image.DecompressionBombError) as img_err:
            print(f"Warning: Downloaded cover for ISBN {isbn_for_filename} (ID {cover_id}) is corrupted: {img_err}. Deleting.")
            if os.path.exists(full_image_path):
                try: os.remove(full_image_path)
                except OSError: pass
            return ""

    except requests.exceptions.RequestException as e:
        print(f"Warning: Failed to download cover for ISBN {isbn_for_filename} (ID {cover_id}): {e}")
        if os.path.exists(full_image_path): # Clean up partial/failed download
            try: os.remove(full_image_path)
            except OSError: pass
    return ""

# Main data generation function
def generate_demo_data():
    """
    Generates demo book data:
    - Fetches book details using ISBNs from OpenLibrary.
    - Downloads cover images.
    - Writes data to a CSV file.
    """
    if not ensure_covers_dir():
        print("Halting demo data generation due to issues with covers directory.")
        return

    collection_data = [] # Local list for this generation run

    for isbn_raw in SAMPLE_ISBNS:
        print(f"\nProcessing ISBN: {isbn_raw}...")
        cleaned_isbn = clean_isbn(isbn_raw)

        book_details = fetch_book_details_openlibrary(cleaned_isbn)

        if book_details:
            print(f"Successfully fetched details for '{book_details.get('title', 'N/A')}' (ISBN: {cleaned_isbn})")

            # Initialize a book_entry dictionary with all FIELDNAMES keys set to default values
            book_entry = {field: "" for field in FIELDNAMES}

            # Populate known fields from fetched details
            book_entry['id'] = cleaned_isbn # Use ISBN as a simple ID for demo
            book_entry['title'] = book_details.get('title', 'N/A')
            book_entry['authors'] = book_details.get('authors', 'N/A')
            book_entry['publisher'] = book_details.get('publisher', 'N/A')
            book_entry['published_date'] = book_details.get('published_date', 'N/A')
            book_entry['description'] = book_details.get('description', '')
            book_entry['isbn_13'] = book_details.get('isbn_13', cleaned_isbn)
            book_entry['isbn_10'] = book_details.get('isbn_10', '')
            book_entry['page_count'] = str(book_details.get('page_count', 'N/A'))
            book_entry['categories'] = book_details.get('categories', '')
            book_entry['info_link'] = book_details.get('info_link', '')
            book_entry['openlibrary_id'] = book_details.get('openlibrary_id', '')

            # Download cover image
            cover_image_path = ""
            if book_details.get("cover_id"):
                cover_image_path = download_cover_image(book_details.get("cover_id"), cleaned_isbn)
            book_entry['cover_image_path'] = cover_image_path
            if cover_image_path:
                print(f"Cover downloaded to: {cover_image_path}")
            else:
                print(f"No cover image downloaded for ISBN {cleaned_isbn}.")

            # Add/Update standard fields
            book_entry['date_added'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            book_entry['date_modified'] = book_entry['date_added']
            book_entry['read_status'] = "No" # Default for new books

            # Fill any remaining N/A or empty fields that might be expected by a more robust system
            for field in FIELDNAMES:
                if book_entry[field] == "" or book_entry[field] == "N/A":
                    if field in ['average_rating', 'ratings_count']:
                        book_entry[field] = "0" # Default numerical fields to 0
                    elif field not in ['tags', 'notes', 'illustrators', 'translators', 'editors', 'goodreads_id', 'librarything_id']: # These can be empty
                        book_entry[field] = "N/A"


            collection_data.append(book_entry)
            print(f"Added '{book_entry['title']}' to collection data.")
        else:
            print(f"Failed to fetch details for ISBN: {cleaned_isbn}. Skipping this entry.")

    # Write data to CSV
    if collection_data:
        script_dir = get_script_directory()
        collection_file_path = os.path.join(script_dir, COLLECTION_FILE)
        try:
            with open(collection_file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
                writer.writeheader()
                writer.writerows(collection_data)
            print(f"\nSuccessfully wrote {len(collection_data)} books to {collection_file_path}")
        except IOError as e:
            print(f"Error: Could not write to CSV file '{collection_file_path}': {e}")
    else:
        print("\nNo book data was fetched, so no CSV file was written.")

if __name__ == "__main__":
    print("Starting demo data generation process...")
    generate_demo_data()
    print("\nDemo data generation process finished.")
    print(f"Check '{COLLECTION_FILE}' and the '{COVERS_DIR}' directory.")
