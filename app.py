import logging
import queue
import time
from flask import Flask, request, jsonify, send_file, Response, url_for, render_template
from PIL import Image
import os
import numpy as np
from scipy.spatial import KDTree
from flask_cors import CORS
import psutil
import uuid
from threading import Lock

app = Flask(__name__)
CORS(app, resources={r"/upload": {"origins": "*"}})

# Disable Flask's default HTTP request logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)

# Directory to save generated images
output_dir = 'static/mosaics'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Create a queue to hold log messages
log_queue = queue.Queue()

# Custom log handler to push logs to the queue with filtering
class QueueHandler(logging.Handler):
    def emit(self, record):
        # Exclude specific debug messages by checking their content
        if "STREAM" not in record.getMessage():
            log_queue.put(self.format(record))

# Define a custom log format
custom_log_format = '%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'

# # Configure logging
# log_formatter = logging.Formatter(custom_log_format)
# file_handler = logging.FileHandler('logs/app.log')
# file_handler.setFormatter(log_formatter)
# file_handler.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
# console_handler.setFormatter(log_formatter)
console_handler.setLevel(logging.DEBUG)

queue_handler = QueueHandler()
# queue_handler.setFormatter(log_formatter)
queue_handler.setLevel(logging.DEBUG)

logging.basicConfig(level=logging.DEBUG, handlers=[ console_handler, queue_handler])

emoji_dir = 'static/emojis'
emoji_data = []
emoji_kd_tree = None
emoji_colors = []


# Record the server start time
server_start_time = time.time()

active_requests = 0
active_requests_lock = Lock()

# Initialize server status dictionary
server_status = {
    "connected": False,
    "progress": "0%",
    "time_elapsed": "0s",
    "approx_time": "Calculating...",
    "emoji_count": 1000585,
    "image_size": "0mb",
    "image_extension": "N/A"
}

def calculate_average_color(image):
    """Calculate the average color of an image."""
    pixels = np.array(image)
    avg_color = pixels.mean(axis=(0, 1))
    logging.debug(f'Calculated average color: {avg_color}')
    return tuple(map(int, avg_color))

def load_emoji_data():
    """Load emoji data and prepare KDTree for color matching."""
    global emoji_data, emoji_kd_tree, emoji_colors
    logging.info('Loading emoji data...')
    for emoji_file in os.listdir(emoji_dir):
        emoji_path = os.path.join(emoji_dir, emoji_file)
        try:
            with Image.open(emoji_path) as emoji_image:
                avg_color = calculate_average_color(emoji_image.convert('RGB'))
                emoji_data.append((emoji_file, avg_color))
                emoji_colors.append(avg_color)
                logging.debug(f'Loaded emoji {emoji_file} with average color {avg_color}')
        except Exception as e:
            logging.error(f'Error loading emoji {emoji_file}: {str(e)}')
    emoji_colors = np.array(emoji_colors)
    emoji_kd_tree = KDTree(emoji_colors)
    logging.info('Emoji data loaded and KDTree created.')

load_emoji_data()

def create_mosaic_image(image, mosaic_size, emoji_tile_size=10):
    """Create a high-quality emoji mosaic image."""
    # Resize the image to the desired mosaic size (thumbnail)
    image.thumbnail(mosaic_size)
    pixels = np.array(image)
    height, width, _ = pixels.shape
    logging.debug(f'Creating mosaic with dimensions: {width}x{height}')

    # Create a blank image with a higher resolution
    mosaic_image = Image.new('RGB', (width * emoji_tile_size, height * emoji_tile_size), (255, 255, 255))
    
    # Loop over each pixel in the thumbnail image
    for y in range(height):
        for x in range(width):
            pixel = pixels[y, x]
            _, index = emoji_kd_tree.query(pixel)  # Find the closest emoji color
            closest_emoji_path = os.path.join(emoji_dir, emoji_data[index][0])
            with Image.open(closest_emoji_path) as emoji:
                # Resize the emoji to the new, smaller tile size
                emoji = emoji.resize((emoji_tile_size, emoji_tile_size))
                # Paste the emoji onto the mosaic
                mosaic_image.paste(emoji, (x * emoji_tile_size, y * emoji_tile_size))
    
    logging.info('High-quality mosaic image created.')
    return mosaic_image

@app.route('/upload', methods=['POST'])
def upload_file():
    """Handle file upload and generate emoji mosaic."""
    global server_status
    server_status["connected"] = True  # Update connection status
    server_status["progress"] = "0%"  # Reset progress

    if 'image' not in request.files:
        logging.warning('No file uploaded')
        return jsonify(error="No file uploaded"), 400

    file = request.files['image']
    if not file.content_type.startswith('image/'):
        logging.warning('Uploaded file is not an image')
        return jsonify(error="Uploaded file is not an image"), 400

    try:
        logging.info('Received image upload.')
        
        # Start measuring time for image upload and conversion
        start_time = time.time()
        with Image.open(file.stream) as image:
            image = image.convert('RGB')
            server_status["progress"] = "10%"  # Example of progress update
            logging.info('Image uploaded and converted to RGB.')
        upload_time = time.time() - start_time
        logging.info(f'Time taken to upload and convert image: {upload_time:.2f} seconds')

        # Start measuring time for mosaic creation
        start_time = time.time()
        mosaic_image = create_mosaic_image(image, (400, 400), emoji_tile_size=10)
        mosaic_creation_time = time.time() - start_time
        logging.info(f'Time taken to create mosaic image: {mosaic_creation_time:.2f} seconds')

        # Start measuring time for saving the image
        start_time = time.time()
        filename = f"mosaic_{uuid.uuid4().hex}.png"
        filepath = os.path.join(output_dir, filename)
        mosaic_image.save(filepath)
        save_time = time.time() - start_time
        logging.info(f'Time taken to save mosaic image: {save_time:.2f} seconds')

        # Update server status
        server_status["progress"] = "100%"  # When processing is done
        server_status["image_size"] = f"{round(os.path.getsize(filepath) / (1024 * 1024), 2)}mb"
        server_status["image_extension"] = "PNG"

        # Generate the URL for the saved image
        mosaic_url = url_for('static', filename=f'mosaics/{filename}', _external=True)
        logging.info(f'Mosaic image URL generated: {mosaic_url}')

        return jsonify(url=mosaic_url)
    except Exception as e:
        logging.error(f"An error occurred: {str(e)}")
        return jsonify(error=f"An error occurred: {str(e)}"), 500

@app.route('/download', methods=['GET'])
def download_image():
    """Serve the image for download."""
    filename = request.args.get('filename')
    if not filename:
        logging.warning('No filename provided for download')
        return jsonify(error="No filename provided"), 400

    filepath = os.path.join(output_dir, filename)
    if not os.path.exists(filepath):
        logging.warning(f'File not found: {filepath}')
        return jsonify(error="File not found"), 404

    logging.info(f'Serving file for download: {filepath}')
    return send_file(filepath, mimetype='image/png', as_attachment=True, download_name=filename)

def stream_logs():
    """Generator function to stream logs."""
    try:
        while True:
            log_entry = log_queue.get()
            if log_entry is None:
                break
            yield f"data: {log_entry}\n\n"
    except GeneratorExit:
        logging.info("Client disconnected from log stream.")

@app.route('/logs')
def logs():
    """Serve real-time logs as Server-Sent Events."""
    return Response(stream_logs(), content_type='text/event-stream')

# Middleware to track active connections
@app.before_request
def before_request():
    global active_requests
    with active_requests_lock:
        active_requests += 1

@app.teardown_request
def teardown_request(exception=None):
    global active_requests
    with active_requests_lock:
        if active_requests > 0:
            active_requests -= 1

@app.route('/server-status', methods=['GET'])
def server_status_route():
    """Provide the server status information."""
    global server_status

    uptime = time.time() - server_start_time

    memory_info = psutil.virtual_memory()
    cpu_usage = psutil.cpu_percent(interval=1)
    disk_usage = psutil.disk_usage('/')
    global active_requests

    return jsonify({
        "Server Status": "Connected" if server_status["connected"] else "Not Connected",
        "Progress": server_status["progress"],
        "Time Elapsed": server_status["time_elapsed"],
        "Approx. Time to Finish": server_status["approx_time"],
        "Emoji Count": server_status["emoji_count"],
        "Image Size": server_status["image_size"],
        "Image Extension": server_status["image_extension"],
        "Uptime": f"{uptime:.2f} seconds",
        "CPU Usage": f"{cpu_usage}%",
        "Memory Usage": f"{memory_info.percent}%",
        "Disk Usage": f"{disk_usage.percent}%",
        "Active Connections": active_requests
    })


@app.route("/")
def index():
    return render_template("index.html")

@app.route('/ping', methods=['GET'])
def health_check():
    """Health check endpoint to verify that the server is running."""
    return jsonify(status="UP", message="Server is running"), 200


if __name__ == '__main__':
    logging.info('Starting the Flask app...')
    app.run(debug=True)
