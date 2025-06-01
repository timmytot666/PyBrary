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

# Constants - Correct FIELDNAMES for PyBrary.py compatibility
FIELDNAMES = [
    "ISBN", "Title", "Author", "Publisher", "PublishedDate",
    "ImagePath", "DateAdded", "ReadStatus"
]
COLLECTION_FILE = 'library_collection.csv'
COVERS_DIR = 'covers'
PLACEHOLDER_IMAGE_NAME = 'placeholder.png'

# --- Helper Functions (Adapted from PyBrary.py) ---
def get_script_directory():
    """
    Returns the absolute directory path of the currently executing script.
    """
    return os.path.dirname(os.path.abspath(sys.argv[0]))

def ensure_covers_dir():
    """
    Ensures that the directory for storing cover images exists.
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
    Returns a dictionary with keys like 'title', 'authors', 'publisher',
    'published_date', 'cover_id', 'isbn_13', etc.
    """
    url = f"https://openlibrary.org/isbn/{isbn}.json"
    print(f"Fetching book details from: {url}")
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        book_data = response.json()

        details = {"isbn_13": isbn, "title": book_data.get("title", "N/A")}

        authors_data = book_data.get("authors", [])
        author_names = []
        if authors_data:
            for author_ref in authors_data[:2]:
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
                else:
                    author_names.append(str(author_ref))
        details["authors"] = ", ".join(author_names) if author_names else "N/A"

        details["publisher"] = ", ".join(book_data.get("publishers", [])[:2]) if book_data.get("publishers") else "N/A"
        details["published_date"] = book_data.get("publish_date", "N/A")

        # Ensure isbn_13 is present (it's set initially from input)
        if "isbn_13" in book_data and book_data["isbn_13"]:
             details["isbn_13"] = book_data["isbn_13"][0]

        if "covers" in book_data and book_data["covers"] and isinstance(book_data["covers"], list):
            positive_cover_ids = [cid for cid in book_data["covers"] if isinstance(cid, int) and cid > 0]
            if positive_cover_ids:
                details["cover_id"] = positive_cover_ids[0]
            elif book_data["covers"] and isinstance(book_data["covers"][0], int) and book_data["covers"][0] != -1:
                 details["cover_id"] = book_data["covers"][0]
        return details

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Warning: Book with ISBN {isbn} was not found on OpenLibrary.")
        else:
            print(f"Warning: HTTP error for ISBN {isbn}: {e}")
    except requests.exceptions.RequestException as e: # Covers ConnectionError, Timeout etc.
        print(f"Error: API request failed for ISBN {isbn}: {e}")
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON response from OpenLibrary for ISBN {isbn}.")
    return None

def download_cover_image(cover_id, isbn_for_filename):
    """
    Downloads a cover image from OpenLibrary.
    Returns relative image path or empty string.
    """
    if not cover_id or cover_id == -1:
        print(f"No valid cover ID for ISBN {isbn_for_filename}. Skipping download.")
        return ""

    image_filename = f"{clean_isbn(isbn_for_filename)}.jpg"
    covers_dir_path = os.path.join(get_script_directory(), COVERS_DIR)
    full_image_path = os.path.join(covers_dir_path, image_filename)
    relative_image_path = os.path.join(COVERS_DIR, image_filename)

    image_url_large = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"
    image_url_medium = f"https://covers.openlibrary.org/b/id/{cover_id}-M.jpg"

    for i, image_url in enumerate([image_url_large, image_url_medium]):
        size = "Large" if i == 0 else "Medium"
        print(f"Attempting to download {size} cover from: {image_url}")
        try:
            response = requests.get(image_url, stream=True, timeout=15)
            response.raise_for_status()
            content_type = response.headers.get('content-type', '').lower()
            if not content_type.startswith('image/'):
                print(f"Warning: Expected an image for {size} size, but got content-type: {content_type} for cover ID {cover_id}.")
                if size == "Medium": # If Medium also fails, give up
                    return ""
                continue # Try next smaller size

            with open(full_image_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            try: # Verify image
                img = Image.open(full_image_path)
                img.verify()
                print(f"Successfully downloaded and verified {size} cover to {relative_image_path}")
                return relative_image_path
            except Exception as img_err:
                print(f"Warning: Downloaded {size} cover for ISBN {isbn_for_filename} (ID {cover_id}) is corrupted: {img_err}. Deleting.")
                if os.path.exists(full_image_path):
                    try: os.remove(full_image_path)
                    except OSError: pass
                return "" # Do not try smaller if a corrupted image was downloaded

        except requests.exceptions.RequestException as e:
            print(f"Warning: Failed to download {size} cover for ISBN {isbn_for_filename} (ID {cover_id}): {e}")
            if os.path.exists(full_image_path):
                try: os.remove(full_image_path)
                except OSError: pass
            if size == "Medium": # If Medium also fails via request exception
                 return ""
    return "" # Should be unreachable if loop structure is correct

# Main data generation function
def generate_demo_data():
    if not ensure_covers_dir():
        print("Halting demo data generation due to issues with covers directory.")
        return

    collection_data = []

    for isbn_raw in SAMPLE_ISBNS:
        print(f"\nProcessing ISBN: {isbn_raw}...")
        cleaned_isbn = clean_isbn(isbn_raw)

        book_details = fetch_book_details_openlibrary(cleaned_isbn)

        if book_details:
            print(f"Successfully fetched details for '{book_details.get('title', 'N/A')}' (ISBN: {cleaned_isbn})")

            book_entry = {field: "" for field in FIELDNAMES} # Initialize with new FIELDNAMES

            # Map fetched details to the new FIELDNAMES structure
            book_entry['ISBN'] = book_details.get('isbn_13', cleaned_isbn) # Ensure ISBN is populated
            book_entry['Title'] = book_details.get('title', 'N/A')
            book_entry['Author'] = book_details.get('authors', 'N/A')
            book_entry['Publisher'] = book_details.get('publisher', 'N/A')
            book_entry['PublishedDate'] = book_details.get('published_date', 'N/A')

            cover_image_path = ""
            if book_details.get("cover_id"):
                cover_image_path = download_cover_image(book_details.get("cover_id"), cleaned_isbn)
            book_entry['ImagePath'] = cover_image_path # Correct key

            if cover_image_path:
                print(f"Cover downloaded to: {cover_image_path}")
            else:
                print(f"No cover image downloaded for ISBN {cleaned_isbn}.")

            book_entry['DateAdded'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            book_entry['ReadStatus'] = "No"

            collection_data.append(book_entry)
            print(f"Added '{book_entry['Title']}' to collection data.")
        else:
            print(f"Failed to fetch details for ISBN: {cleaned_isbn}. Skipping this entry.")

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
