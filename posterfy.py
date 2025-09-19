import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import requests
from PIL import Image
from io import BytesIO
import os
import tempfile
import traceback
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.colors import black, HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from dotenv import load_dotenv
import re
from textwrap import wrap
import qrcode

load_dotenv()

# Set up Spotify API credentials
SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

def get_album_details(album_url):
    try:
        print(f"Fetching album details for: {album_url}")
        # Extract album ID from URL
        album_id = album_url.split("/")[-1].split("?")[0]
        print(f"Extracted album ID: {album_id}")
        
        # Initialize Spotify client
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET
        ))
        
        # Get album information
        album = sp.album(album_id)
        album_name = album["name"]
        artist_name = album["artists"][0]["name"]
        album_cover_url = album["images"][0]["url"] if album["images"] else None
        tracks = [track["name"] for track in album["tracks"]["items"]]
        
        print(f"Successfully fetched album: {album_name} by {artist_name}")
        print(f"Found {len(tracks)} tracks")
        
        return {
            "album_name": album_name,
            "artist_name": artist_name,
            "album_cover_url": album_cover_url,
            "tracks": tracks,
            "album_url": album_url,
            "success": True
        }
    except Exception as e:
        print(f"Error fetching album details: {str(e)}")
        print(traceback.format_exc())
        return {"success": False, "error": str(e)}

def download_album_cover(url):
    try:
        print(f"Downloading album cover from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise exception for bad responses
        img = Image.open(BytesIO(response.content))
        img = img.resize((400, 400))  # Resize for consistency
        print("Album cover downloaded and resized successfully")
        return img
    except Exception as e:
        print(f"Error downloading album cover: {str(e)}")
        print(traceback.format_exc())
        return None

def safe_filename(filename):
    # Replace invalid characters with underscore
    safe_name = re.sub(r'[\\/*?:"<>|]', "_", filename)
    print(f"Converted filename '{filename}' to safe filename '{safe_name}'")
    return safe_name

# Function to calculate required height for track list with given font size
def calculate_tracklist_height(c, tracks, first_column_width, second_column_width, font_name, font_size):
    line_height = font_size + 5
    
    # Calculate height for first column
    first_column_tracks = min(len(tracks) // 2 + len(tracks) % 2, len(tracks))
    first_column_height = 0
    
    for i in range(first_column_tracks):
        track_name = tracks[i]
        lines_needed = calculate_lines_needed(c, track_name, first_column_width, font_name, font_size)
        first_column_height += lines_needed * line_height + 2  # Add 2 for small spacing between tracks
    
    # Calculate height for second column
    second_column_height = 0
    for i in range(first_column_tracks, len(tracks)):
        track_name = tracks[i]
        lines_needed = calculate_lines_needed(c, track_name, second_column_width, font_name, font_size)
        second_column_height += lines_needed * line_height + 2  # Add 2 for small spacing between tracks
    
    # Return the taller of the two columns
    return max(first_column_height, second_column_height)

# Function to calculate how many lines a text needs when wrapped
def calculate_lines_needed(c, text, max_width, font_name, font_size):
    # Calculate how many characters can fit in the available width
    text_width = c.stringWidth(text, font_name, font_size)
    
    if text_width <= max_width:
        return 1  # Text fits on one line
    else:
        # Estimate chars per line (approximate)
        chars_per_line = max(10, int(len(text) * (max_width / text_width)))
        lines_needed = 0
        remaining = text
        
        while remaining:
            # Start with estimated chars per line
            test_len = min(chars_per_line, len(remaining))
            test_text = remaining[:test_len]
            
            # If this isn't the end, try to find a space to break at
            if test_len < len(remaining) and test_len > 0:
                # Find last space within the test text
                last_space = test_text.rfind(' ')
                if last_space > 0:
                    test_len = last_space + 1  # +1 to include the space
                    test_text = remaining[:test_len]
            
            # Check if this segment actually fits
            while c.stringWidth(test_text, font_name, font_size) > max_width and test_len > 1:
                test_len -= 1
                test_text = remaining[:test_len]
            
            lines_needed += 1
            remaining = remaining[test_len:].strip()
        
        return lines_needed

# Function to draw wrapped text and return new y position
def draw_wrapped_text(c, text, x, y, max_width, line_height, font_name, font_size):
    # Calculate how many characters can fit in the available width
    text_width = c.stringWidth(text, font_name, font_size)
    
    if text_width <= max_width:
        # Text fits on one line
        c.drawString(x, y, text)
        return y - line_height, 1, text_width  # Return new y position, line count, and text width
    else:
        # Text needs to be wrapped
        # Estimate chars per line (approximate)
        chars_per_line = max(10, int(len(text) * (max_width / text_width)))
        
        # Try to wrap text smartly
        wrapped_lines = []
        remaining = text
        
        while remaining:
            # Start with estimated chars per line
            test_len = min(chars_per_line, len(remaining))
            test_text = remaining[:test_len]
            
            # If this isn't the end, try to find a space to break at
            if test_len < len(remaining) and test_len > 0:
                # Find last space within the test text
                last_space = test_text.rfind(' ')
                if last_space > 0:
                    test_len = last_space + 1  # +1 to include the space
                    test_text = remaining[:test_len]
            
            # Check if this segment actually fits
            while c.stringWidth(test_text, font_name, font_size) > max_width and test_len > 1:
                test_len -= 1
                test_text = remaining[:test_len]
            
            wrapped_lines.append(test_text.strip())
            remaining = remaining[test_len:].strip()
        
        # Draw each line
        current_y = y
        for line in wrapped_lines:
            c.drawString(x, current_y, line)
            current_y -= line_height
        
        # For wrapped text, we return the width of the last line
        last_line_width = c.stringWidth(wrapped_lines[-1], font_name, font_size)
        
        # Return the new y position, line count, and width of the last line
        return current_y, len(wrapped_lines), last_line_width

def create_fallback_qr_code(album_url, temp_dir, size=100):
    try:
        print(f"Creating fallback QR code for URL: {album_url}")
        
        # Create QR code for the album URL
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(album_url)
        qr.make(fit=True)
        
        # Create QR code image
        qr_img = qr.make_image(fill_color="black", back_color="white")
        qr_img = qr_img.resize((size, size))
        
        # Save the QR code
        code_path = os.path.join(temp_dir, "spotify_code.png")
        qr_img.save(code_path, format="PNG")
        print(f"Fallback QR code saved to: {code_path}")
        
        return code_path
    except Exception as e:
        print(f"Error creating fallback QR code: {str(e)}")
        print(traceback.format_exc())
        return None

def create_spotify_code(album_url, temp_dir, size=100):
    try:
        print(f"Creating Spotify code for URL: {album_url}")
        
        # Extract Spotify ID from URL
        if "spotify.com/album/" in album_url:
            album_id = album_url.split("/")[-1].split("?")[0]
        else:
            print("Invalid Spotify URL format. Using fallback QR code.")
            return create_fallback_qr_code(album_url, temp_dir, size)
        
        # Use Spotify's official code API
        # Modified: Use the same off-white color (F8F8F5) as the poster background
        spotify_code_url = f"https://scannables.scdn.co/uri/plain/png/F8F8F5/black/640/spotify:album:{album_id}"
        
        try:
            print(f"Fetching Spotify code from: {spotify_code_url}")
            code_response = requests.get(spotify_code_url, timeout=10)
            code_response.raise_for_status()
            
            # Save the Spotify code image
            spotify_code = Image.open(BytesIO(code_response.content))
            
            # Make the code wider by setting a fixed width and proportional height
            new_width = 250  # Wider fixed width
            original_width, original_height = spotify_code.size
            new_height = int((new_width / original_width) * original_height)
            
            spotify_code = spotify_code.resize((new_width, new_height), Image.LANCZOS)
            
            code_path = os.path.join(temp_dir, "spotify_code.png")
            spotify_code.save(code_path, format="PNG")
            print(f"Spotify code saved to: {code_path}")
            
            return code_path
        except Exception as e:
            print(f"Error fetching Spotify code: {str(e)}")
            print(traceback.format_exc())
            print("Using fallback QR code instead.")
            return create_fallback_qr_code(album_url, temp_dir, size)
            
    except Exception as e:
        print(f"Error creating Spotify code: {str(e)}")
        print(traceback.format_exc())
        return create_fallback_qr_code(album_url, temp_dir, size)

def generate_pdf(album_details, temp_dir):
    try:
        print("Starting PDF generation")
        album_name = album_details["album_name"].upper()  # Convert to uppercase
        artist_name = album_details["artist_name"].upper()  # Convert to uppercase
        tracks = [track.upper() for track in album_details["tracks"]]  # Convert all tracks to uppercase
        album_url = album_details["album_url"]  # URL for Spotify code
        
        # Create safe filename
        safe_name = safe_filename(f"{artist_name} - {album_name}")
        
        # Save PDF in current working directory
        current_dir = os.getcwd()
        pdf_filename = os.path.join(current_dir, f"{safe_name}.pdf")
        print(f"PDF will be saved as: {pdf_filename}")
        
        # Create PDF canvas
        print("Creating PDF canvas")
        c = canvas.Canvas(pdf_filename, pagesize=A4)
        width, height = A4
        print(f"PDF dimensions: {width}x{height}")
        
        # Define margins and border width - INCREASED FOR VISIBILITY
        margin = 50  # Consistent margin for all sides
        border_width = 10  # Increased from 2 to 5 for better visibility
        
        # Define inner content area with some padding from the border
        border_padding = 5  # Space between border and content
        inner_x = border_width + border_padding
        inner_y = border_width + border_padding
        inner_width = width - 2 * (border_width + border_padding)
        inner_height = height - 2 * (border_width + border_padding)
        
        # Set off-white background with inset from border
        # Instead of filling the entire page, fill only the inner area
        # This ensures the border will be visible
        # Fill the entire page with off-white background
        c.setFillColor(HexColor("#F8F8F5"))  # Off-white color
        c.rect(0, 0, width, height, fill=1, stroke=0)
        
        # Try to register Helvetica Inserat font if available
        font_name = "Helvetica"  # Default font
        try:
            # Check if Helvetica Inserat font is already registered in ReportLab
            helvetica_inserat_registered = False
            for font in pdfmetrics.getRegisteredFontNames():
                if font == "Helvetica-Inserat":
                    helvetica_inserat_registered = True
                    break
            
            if not helvetica_inserat_registered:
                # Try to find Helvetica Inserat font on system
                possible_paths = [
                    # Windows paths
                    "C:/Windows/Fonts/HelveticaInserat.ttf",
                    "C:/Windows/Fonts/helvetica_inserat.ttf",
                    "C:/Windows/Fonts/Helvetica Inserat.ttf",
                    # macOS paths
                    "/Library/Fonts/Helvetica Inserat.ttf",
                    "/System/Library/Fonts/Helvetica Inserat.ttf",
                    # Linux paths
                    "/usr/share/fonts/truetype/Helvetica-Inserat.ttf",
                    # Current directory
                    os.path.join(current_dir, "helveticainserat.ttf"),
                    os.path.join(current_dir, "Helvetica-Inserat.ttf"),
                    os.path.join(current_dir, "Helvetica Inserat.ttf"),
                ]
                
                for font_path in possible_paths:
                    if os.path.exists(font_path):
                        print(f"Found Helvetica Inserat font at: {font_path}")
                        pdfmetrics.registerFont(TTFont("Helvetica-Inserat", font_path))
                        font_name = "Helvetica-Inserat"
                        break
                        
                if font_name == "Helvetica":
                    print("Helvetica Inserat font not found, using Helvetica instead.")
            else:
                font_name = "Helvetica-Inserat"
                print("Helvetica Inserat font already registered")
                
        except Exception as e:
            print(f"Error registering font: {str(e)}")
            print(traceback.format_exc())
            print("Using Helvetica instead.")
        
        # Create Spotify code with inverted colors and wider format
        spotify_code_path = create_spotify_code(album_url, temp_dir)
        
        # Get actual dimensions of the Spotify code
        spotify_code_img = Image.open(spotify_code_path)
        spotify_code_width, spotify_code_height = spotify_code_img.size
        
        # Area for Spotify code - bottom right corner, with padding from border
        spotify_code_padding = 15  # Padding from border
        spotify_code_x = width - border_width - spotify_code_padding - spotify_code_width
        spotify_code_y = border_width + spotify_code_padding
        
        # Draw album cover if available
        cover_height = 400
        cover_top_margin = margin
        cover_space_after = 40  # Increased space after cover
        if album_details["album_cover_url"]:
            print("Processing album cover")
            album_cover = download_album_cover(album_details["album_cover_url"])
            if album_cover:
                img_path = os.path.join(temp_dir, "album_cover.png")
                print(f"Saving album cover to: {img_path}")
                album_cover.save(img_path, format="PNG")
                c.drawImage(img_path, (width - cover_height) / 2, height - cover_height - cover_top_margin, 
                            width=cover_height, height=cover_height)
                print("Album cover added to PDF")
        
        # Starting position for album title
        title_y = height - cover_height - cover_top_margin - cover_space_after - 10
        
        # Initial font sizes
        initial_album_title_size = int(30 * 1.35)  # From 30 to ~40
        # MODIFIED: Increased tracklist and artist name font size by 25%
        initial_tracklist_size = int(10 * 1.35 * 0.8 * 1.25)  # Original * 1.25 for 25% increase
        
        # Define minimum font sizes - don't go below these values
        min_album_title_size = int(initial_album_title_size * 0.8)  # 80% of initial size
        min_tracklist_size = int(initial_tracklist_size * 0.8)  # 80% of initial size
        
        # Bottom margin needs to account for Spotify code
        bottom_margin = max(30, spotify_code_y + spotify_code_height + 15)  # Ensure minimum 30px or enough for code
        
        # Available height for content (excluding cover)
        available_height = title_y - bottom_margin
        
        # Calculate initial layout parameters for album title and tracklist
        album_title_size = initial_album_title_size
        tracklist_size = initial_tracklist_size
        
        # Define column widths for text wrapping
        # Adjust second column width to avoid overlap with Spotify code
        first_column_width = (width - 2 * margin) / 2 - 10  # Subtract some padding between columns
        second_column_width = (width - 2 * margin) / 2 - 10  # Subtract some padding between columns
        
        # Ensure tracklist doesn't overlap with Spotify code by adjusting track list boundaries
        second_column_max_right = spotify_code_x - 20  # 20px buffer from Spotify code
        second_column_max_width = second_column_max_right - (width / 2 + 10)  # Max width to avoid overlap
        if second_column_max_width > 0:
            second_column_width = min(second_column_width, second_column_max_width)
        
        # Attempt layout with initial font sizes
        layout_successful = False
        font_reduction_attempts = 0
        max_font_reduction_attempts = 3  # Limit how many times we reduce the font
        
        while not layout_successful and font_reduction_attempts <= max_font_reduction_attempts:
            # Set text color
            c.setFillColor(black)
            
            # Temporary canvas for calculations
            temp_canvas = canvas.Canvas(None)
            temp_canvas.setFont("Helvetica-Bold", album_title_size)
            
            # MODIFIED: Increase the width for album title to use more horizontal space
            # Use almost the full width for the title, only leave a small space for artist name
            title_width = width - 2 * margin - 100  # Reduced reservation from 200 to 100
            lines_needed = calculate_lines_needed(temp_canvas, album_name, title_width, font_name, album_title_size)
            
            # Limit album title wrapping to max 2 lines
            if lines_needed > 2:
                lines_needed = 2  # Force to 2 lines
            
            title_height = lines_needed * (album_title_size + 5)
            artist_name_height = tracklist_size + 5  # Height for artist name
            
            # Space between elements
            title_to_tracklist_spacing = 30
            
            # Calculate how much space we need for tracklist
            tracklist_height = calculate_tracklist_height(
                temp_canvas, tracks, first_column_width, second_column_width, 
                font_name, tracklist_size
            )
            
            # Calculate total required height
            total_required_height = title_height + artist_name_height + title_to_tracklist_spacing + tracklist_height
            
            # Check if everything fits
            if total_required_height <= available_height:
                layout_successful = True
            else:
                # Reduce font sizes and try again, but ensure they don't go below minimums
                album_title_size = max(int(album_title_size * 0.9), min_album_title_size)
                tracklist_size = max(int(tracklist_size * 0.9), min_tracklist_size)
                font_reduction_attempts += 1
                print(f"Reducing font sizes (attempt {font_reduction_attempts}): Album title {album_title_size}, Tracklist {tracklist_size}")
                
                # If we've reached minimum sizes and still can't fit, break out of loop
                if album_title_size == min_album_title_size and tracklist_size == min_tracklist_size:
                    print("Reached minimum font sizes. Some content may be cut off.")
                    break
        
        print(f"Final font sizes: Album title {album_title_size}, Tracklist {tracklist_size}")
        
        # Now draw actual content with the calculated font sizes
        
        # Draw album title with text wrapping (limited to 2 lines)
        print(f"Adding album title with font size {album_title_size}")
        c.setFont("Helvetica-Bold", album_title_size)
        # MODIFIED: Use more horizontal space for album title
        max_album_title_width = width - 2 * margin - 100  # Reduced from 200 to 100
        
        # Draw album title (max 2 lines)
        new_y, title_lines, last_line_width = draw_wrapped_text(c, album_name, margin, title_y, 
                                                               max_album_title_width, album_title_size + 5, 
                                                               font_name, album_title_size)
        
        # If the album name fits on one line, draw artist name on the same line
        # Otherwise, draw it at the end of the second line
        if title_lines == 1:
            # Draw artist name on the same line
            artist_x = margin + last_line_width + 10  # Add some spacing
            artist_y = title_y
        else:
            # Draw artist name on the second line (at the end)
            artist_x = margin + last_line_width + 10  # Add some spacing
            artist_y = new_y + album_title_size + 5
        
        # Draw artist name
        print(f"Adding artist name with font size {tracklist_size}")
        c.setFont(font_name, tracklist_size)
        c.drawString(artist_x, artist_y, artist_name)
        
        # Calculate starting position for tracklist
        tracklist_y = new_y - title_to_tracklist_spacing
        
        # Draw tracklist in two columns with text wrapping
        print(f"Adding tracklist with font size {tracklist_size}")
        c.setFont(font_name, tracklist_size)
        line_height = tracklist_size + 5
        
        # Calculate number of tracks for each column (divide evenly)
        first_column_tracks = len(tracks) // 2
        if len(tracks) % 2 != 0:  # If odd number of tracks, put extra one in first column
            first_column_tracks += 1
        
        # Calculate lowest y-position of tracklist to ensure no overlap with Spotify code
        lowest_y_allowed = spotify_code_y + spotify_code_height + 15  # 15px buffer
        
        # Draw first column
        current_y = tracklist_y
        for i in range(first_column_tracks):
            if i < len(tracks) and current_y > lowest_y_allowed:
                track_name = tracks[i]
                new_y, _, _ = draw_wrapped_text(c, track_name, margin, current_y, 
                                               first_column_width, line_height, font_name, tracklist_size)
                # Move to next track position
                current_y = new_y - 2  # Small extra spacing
        
        # Draw second column
        current_y = tracklist_y
        second_column_x = width / 2 + 10
        for i in range(first_column_tracks, len(tracks)):
            # Check if we're past the start of the Spotify code area and if the track would stretch into it
            track_name = tracks[i]
            if current_y > spotify_code_y + spotify_code_height + 15:  # Add buffer
                new_y, _, _ = draw_wrapped_text(c, track_name, second_column_x, current_y, 
                                               second_column_width, line_height, font_name, tracklist_size)
                # Move to next track position
                current_y = new_y - 2  # Small extra spacing
        
        # Draw Spotify code in bottom right corner with its new dimensions
        if spotify_code_path:
            print(f"Adding Spotify code at position ({spotify_code_x}, {spotify_code_y})")
            c.drawImage(spotify_code_path, spotify_code_x, spotify_code_y, 
                        width=spotify_code_width, height=spotify_code_height)
        
        # MODIFIED: Draw the black border with a gap of border_width from the edge
        # Instead of drawing at (0, 0), draw at (border_width, border_width)
        # And reduce the width and height by 2*border_width
        c.setStrokeColor(black)
        c.setLineWidth(border_width)
        c.rect(
            border_width,           # x position - offset by border_width from the edge
            border_width,           # y position - offset by border_width from the edge
            width - 2*border_width, # width reduced by 2*border_width
            height - 2*border_width,# height reduced by 2*border_width
            fill=0, 
            stroke=1
        )
        
        print("Saving PDF")
        c.save()
        print(f"PDF successfully generated: {pdf_filename}")
        return pdf_filename
    except Exception as e:
        print(f"Error generating PDF: {str(e)}")
        print(traceback.format_exc())
        return None

def main():
    # Create temporary directory for files
    print("Starting Spotify Album PDF Generator")
    with tempfile.TemporaryDirectory() as temp_dir:
        print(f"Created temporary directory: {temp_dir}")
        try:
            # Get album URL from user
            album_url = input("Enter Spotify album URL: ")
            
            # Get album details
            album_details = get_album_details(album_url)
            
            if not album_details["success"]:
                print(f"Failed to get album details: {album_details.get('error', 'Unknown error')}")
                return
            
            # Generate PDF
            pdf_file = generate_pdf(album_details, temp_dir)
            
            if pdf_file:
                print(f"PDF successfully generated: {pdf_file}")
                print(f"You can find your album poster in the current directory")
            else:
                print("Failed to generate PDF")
        
        except Exception as e:
            print(f"An error occurred: {str(e)}")
            print(traceback.format_exc())

if __name__ == "__main__":
    main()