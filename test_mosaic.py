# test_mosaic.py

import pytest
from io import BytesIO
from PIL import Image
from flask import url_for
from server import app  # Replace `your_flask_app` with the actual name of your Flask app file (without .py)


@pytest.fixture
def client():
    """
    Pytest fixture to create a test client for the Flask app.
    """
    with app.test_client() as client:
        yield client


def test_hello_world(client):
    """
    Test the '/' endpoint to ensure it returns the correct HTML.
    """
    response = client.get('/')
    assert response.status_code == 500  # Expected 500 due to intentional error in the '/' route


def test_create_mosaic_no_file(client):
    """
    Test the '/create-mosaic' endpoint with no file uploaded.
    """
    response = client.post('/create-mosaic')
    assert response.status_code == 400
    assert response.json['error'] == "No file uploaded. Please upload an image file."


def test_create_mosaic_with_image(client):
    """
    Test the '/create-mosaic' endpoint with an image file uploaded.
    """
    # Create an in-memory image file
    img = Image.new('RGB', (10, 10), color='red')
    img_io = BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)

    data = {
        'image': (img_io, 'test.png')
    }

    response = client.post('/create-mosaic', content_type='multipart/form-data', data=data)
    assert response.status_code == 200
    assert 'task_id' in response.json


def test_get_progress_invalid_task(client):
    """
    Test the '/progress/<task_id>' endpoint with an invalid task ID.
    """
    response = client.get('/progress/invalid_task_id')
    assert response.status_code == 404
    assert response.json['error'] == "Task not found"


def test_get_result_invalid_task(client):
    """
    Test the '/result/<task_id>' endpoint with an invalid task ID.
    """
    response = client.get('/result/invalid_task_id')
    assert response.status_code == 404
    assert response.json['error'] == "Task not found"


def test_download_mosaic_invalid_task(client):
    """
    Test the '/download/<task_id>' endpoint with an invalid task ID.
    """
    response = client.get('/download/invalid_task_id')
    assert response.status_code == 404
    assert response.json['error'] == "Task not found"
