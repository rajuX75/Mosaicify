# Mosaicify

**Mosaicify** is a web application that transforms your images into colorful emoji mosaics. By using emojis to represent different colors, Mosaicify creates unique and artistic representations of your photos. Upload any image, and watch as it is converted into a mosaic composed entirely of emojis!

## Features

- **Image Upload**: Upload your image through a user-friendly interface.
- **Emoji Mosaic Creation**: Convert your image into a mosaic made up of emojis.
- **Real-time Progress Tracking**: Monitor the progress of your mosaic creation task.
- **Download Mosaic**: Download the final mosaic image once it's created.
- **Task Management**: Track and manage mosaic creation tasks with unique task IDs.

## Getting Started

To get started with Mosaicify, follow these steps:

### Prerequisites

- Python 3.x
- Flask
- PIL (Pillow)
- NumPy
- SciPy
- Flask-CORS
- Sentry SDK
- psutil

### Installation

1. **Clone the Repository**

    ```bash
    git clone https://github.com/yourusername/mosaicify.git
    cd mosaicify
    ```

2. **Create and Activate a Virtual Environment**

    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. **Install Dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Run the Application**

    ```bash
    python app.py
    ```

    The application will be accessible at `http://localhost:10000`.

## Usage

1. **Upload an Image**

    Navigate to `http://localhost:10000` and upload an image file using the `/create-mosaic` endpoint. The file must be a valid image format.

2. **Track Progress**

    Use the `/progress/<task_id>` endpoint to check the progress of your mosaic creation task.

3. **View Task Result**

    Retrieve the result of a completed task using the `/result/<task_id>` endpoint.

4. **Download the Mosaic**

    Once the mosaic is complete, you can download it via the `/download/<task_id>` endpoint.

## API Endpoints

- **`POST /create-mosaic`**: Upload an image to create a mosaic.
- **`GET /progress/<task_id>`**: Get the current progress of a mosaic creation task.
- **`GET /result/<task_id>`**: Get details of a completed mosaic task.
- **`GET /download/<task_id>`**: Download the completed mosaic image.

## Configuration

- **Sentry DSN**: Set up Sentry for error tracking by updating the `dsn` in the `app.py` file.
- **Directories**: Ensure `static/mosaics` and `static/emojis` directories exist or create them as needed.
- **JSON Database**: The JSON database is stored at `static/mosaic_db.json` for persistent task storage.

## Troubleshooting

- **No File Uploaded**: Ensure a valid image file is selected when making the POST request to `/create-mosaic`.
- **Error Creating Mosaic**: Check the server logs for detailed error messages.

## Contributing

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Commit your changes (`git commit -am 'Add new feature'`).
4. Push to the branch (`git push origin feature-branch`).
5. Create a new Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

For questions or feedback, please open an issue on the [GitHub repository](https://github.com/yourusername/mosaicify/issues).

---

Happy mosaic creating with Mosaicify!

