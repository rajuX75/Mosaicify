import threading
import logging
import time
import sentry_sdk
from flask import Flask, request, jsonify, send_file, url_for
from PIL import Image
import os
import numpy as np
from scipy.spatial import KDTree
from flask_cors import CORS
import uuid
from threading import Lock
import json

# Initialize Sentry SDK
sentry_sdk.init(
    dsn="https://ed576ffa6137665e84a9b6c284101d0a@o4507859174948864.ingest.us.sentry.io/4507859176456192",
    traces_sample_rate=1.0,
    profiles_sample_rate=1.0,
)

# Initialize Flask app
app = Flask(__name__)
app.config['SERVER_NAME'] = 'localhost:10000'  # Replace with your actual domain and port
CORS(app, resources={r"/upload": {"origins": "*"}})

# Initial server status
server_status = {
    "connected": False,
    "progress": "0%",
    "time_elapsed": "0s",
    "approx_time": "Calculating...",
    "emoji_count": 1000585,
    "image_size": "0mb",
    "image_extension": "N/A",
    "task_id": None
}

# Mosaic task management
mosaic_tasks = {}
task_lock = Lock()

# Logging configuration
logging.basicConfig(level=logging.INFO)

# Directories for output and emojis
output_dir = 'static/mosaics'
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

emoji_dir = 'static/emojis'
if not os.path.exists(emoji_dir):
    os.makedirs(emoji_dir)

# JSON database file path
json_db_path = 'static/mosaic_db.json'
if not os.path.exists(json_db_path):
    # Initialize the JSON file with an empty dictionary if it doesn't exist
    with open(json_db_path, 'w') as f:
        json.dump({}, f)

# Global variables for emoji data
emoji_data = []
emoji_kd_tree = None
emoji_colors = []

def calculate_average_color(image):
    """
    Calculate the average color of an image.

    Args:
        image (PIL.Image): The image to process.

    Returns:
        tuple: The average RGB color of the image.
    """
    try:
        pixels = np.array(image)
        avg_color = pixels.mean(axis=(0, 1))
        logging.debug(f'Calculated average color: {avg_color}')
        return tuple(map(int, avg_color))
    except Exception as e:
        logging.error(f'Error calculating average color for image: {str(e)}')
        raise RuntimeError(f'Error calculating average color: {str(e)}')

def load_emoji_data():
    """
    Load emoji data and build a KDTree for fast color matching.
    """
    global emoji_data, emoji_kd_tree, emoji_colors
    logging.info('Loading emoji data...')
    try:
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
                continue
        emoji_colors = np.array(emoji_colors)
        emoji_kd_tree = KDTree(emoji_colors)
        logging.info('Emoji data loaded and KDTree created.')
    except Exception as e:
        logging.error(f'General error loading emoji data: {str(e)}')
        raise RuntimeError(f'General error loading emoji data: {str(e)}')

# Call load_emoji_data() to initialize emoji data
load_emoji_data()

def create_mosaic_image(image, mosaic_size, emoji_tile_size=10):
    """
    Create a mosaic image using emojis.

    Args:
        image (PIL.Image): The input image.
        mosaic_size (tuple): Size of the mosaic (width, height).
        emoji_tile_size (int): Size of each emoji tile.

    Returns:
        PIL.Image: The created mosaic image.
    """
    try:
        image.thumbnail(mosaic_size)
        pixels = np.array(image)
        height, width, _ = pixels.shape
        logging.debug(f'Creating mosaic with dimensions: {width}x{height}')

        mosaic_image = Image.new('RGB', (width * emoji_tile_size, height * emoji_tile_size), (255, 255, 255))
        
        for y in range(height):
            for x in range(width):
                pixel = pixels[y, x]
                try:
                    _, index = emoji_kd_tree.query(pixel)
                    closest_emoji_path = os.path.join(emoji_dir, emoji_data[index][0])
                    with Image.open(closest_emoji_path) as emoji:
                        emoji = emoji.resize((emoji_tile_size, emoji_tile_size))
                        mosaic_image.paste(emoji, (x * emoji_tile_size, y * emoji_tile_size))
                except Exception as e:
                    logging.error(f'Error processing pixel at ({x}, {y}) with color {pixel}: {str(e)}')
                    continue
        
        logging.info('High-quality mosaic image created.')
        return mosaic_image
    except Exception as e:
        logging.error(f'Error creating mosaic image: {str(e)}')
        raise RuntimeError(f'Error creating mosaic image: {str(e)}')

def update_progress(task_id, progress):
    """
    Update the progress of a mosaic task.

    Args:
        task_id (str): The ID of the task.
        progress (str): The progress value to update.
    """
    with task_lock:
        if task_id in mosaic_tasks:
            mosaic_tasks[task_id]['progress'] = progress

def save_to_json_db(task_id, data):
    """
    Save task data to the JSON database.

    Args:
        task_id (str): The ID of the task.
        data (dict): The data to save.
    """
    try:
        with open(json_db_path, 'r') as f:
            db = json.load(f)
        db[task_id] = data
        with open(json_db_path, 'w') as f:
            json.dump(db, f, indent=4)
    except Exception as e:
        logging.error(f"Error saving to JSON database: {str(e)}")

def create_mosaic_task(image, task_id, mosaic_size=(400, 400), emoji_tile_size=10):
    """
    Create a mosaic image task.

    Args:
        image (PIL.Image): The input image.
        task_id (str): The ID of the task.
        mosaic_size (tuple): Size of the mosaic.
        emoji_tile_size (int): Size of each emoji tile.
    """
    try:
        server_status["connected"] = True
        update_progress(task_id, "10%")
        mosaic_image = create_mosaic_image(image, mosaic_size, emoji_tile_size)
        update_progress(task_id, "80%")

        filename = f"mosaic_{uuid.uuid4().hex}.png"
        filepath = os.path.join(output_dir, filename)
        mosaic_image.save(filepath)
        update_progress(task_id, "100%")

        image_size = f"{round(os.path.getsize(filepath) / (1024 * 1024), 2)} MB"
        creation_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())
        created_time = time.strftime('%H:%M:%S', time.localtime())

        with app.app_context():
            download_url = url_for('download_mosaic', task_id=task_id, _external=True)

        mosaic_tasks[task_id] = {
            'progress': '100%',
            'status': 'completed',
            'filepath': filepath,
            'image_size': image_size,
            'emoji_count': len(emoji_data),
            'creation_date': creation_date,
            'created_time': created_time,
            'download_url': download_url,
            'error': None
        }

        save_to_json_db(task_id, mosaic_tasks[task_id])
    except Exception as e:
        with task_lock:
            mosaic_tasks[task_id]['status'] = 'error'
            mosaic_tasks[task_id]['error'] = f'Error during mosaic creation task {task_id}: {str(e)}'
        logging.error(f"Error in mosaic creation task {task_id} while creating mosaic or saving: {e}")

@app.route("/")
def hello_world():
    1 / 0  # raises an error
    return "<p>Hello, World!</p>"

@app.route('/create-mosaic', methods=['POST'])
def create_mosaic():
    """
    Endpoint to create a mosaic from an uploaded image.
    """
    if 'image' not in request.files:
        logging.warning('No file uploaded')
        return jsonify(error="No file uploaded. Please upload an image file."), 400

    file = request.files['image']
    if not file.content_type.startswith('image/'):
        logging.warning('Uploaded file is not an image')
        return jsonify(error="Uploaded file is not an image. Please upload a valid image file."), 400

    try:
        with Image.open(file.stream) as image:
            image = image.convert('RGB')

        task_id = str(uuid.uuid4())
        mosaic_tasks[task_id] = {
            'progress': '0%',
            'status': 'processing',
            'filepath': None,
            'error': None
        }

        threading.Thread(target=create_mosaic_task, args=(image, task_id)).start()

        return jsonify(task_id=task_id)
    except Exception as e:
        logging.error(f"An error occurred while processing the uploaded image: {str(e)}")
        return jsonify(error=f"An error occurred while processing the image: {str(e)}. Please try again."), 500

@app.route('/progress/<task_id>', methods=['GET'])
def get_progress(task_id):
    """
    Endpoint to get the progress of a mosaic task.

    Args:
        task_id (str): The ID of the task.

    Returns:
        json: The progress information of the task.
    """
    with task_lock:
        task_info = mosaic_tasks.get(task_id)

    if not task_info:
        return jsonify(error="Task not found"), 404

    return jsonify(task_info)

@app.route('/result/<task_id>', methods=['GET'])
def get_result(task_id):
    """
    Endpoint to get the result of a mosaic task.

    Args:
        task_id (str): The ID of the task.

    Returns:
        json: The result information of the task.
    """
    try:
        with open(json_db_path, 'r') as f:
            db = json.load(f)
        
        task_info = db.get(task_id)
        if not task_info:
            return jsonify(error="Task not found"), 404

        return jsonify(task_info)
    except Exception as e:
        logging.error(f"Error retrieving task result: {str(e)}")
        return jsonify(error="An error occurred while retrieving the task result"), 500

@app.route('/download/<task_id>', methods=['GET'])
def download_mosaic(task_id):
    """
    Endpoint to download the created mosaic image.

    Args:
        task_id (str): The ID of the task.

    Returns:
        file: The mosaic image file for download.
    """
    try:
        # Load the task info from JSON database or in-memory dictionary
        with open(json_db_path, 'r') as f:
            db = json.load(f)
        
        task_info = db.get(task_id)
        
        if not task_info:
            return jsonify(error="Task not found"), 404
        
        filepath = task_info.get('filepath')
        
        if not filepath or not os.path.exists(filepath):
            return jsonify(error="File not found"), 404

        return send_file(filepath, as_attachment=True)

    except Exception as e:
        logging.error(f"Error downloading file for task {task_id}: {str(e)}")
        return jsonify(error=f"Error downloading file for task {task_id}: {str(e)}"), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000, debug=True)
