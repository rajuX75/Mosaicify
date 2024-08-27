document.getElementById('uploadButton').addEventListener('click', function() {
    var fileInput = document.getElementById('imageUpload');
    var file = fileInput.files[0];

    if (!file) {
        alert('Please select an image to upload.');
        return;
    }

    var formData = new FormData();
    formData.append('image', file);

    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/upload', true);

    xhr.upload.onprogress = function(e) {
        if (e.lengthComputable) {
            var percentComplete = (e.loaded / e.total) * 100;
            document.getElementById('progress').style.width = percentComplete + '%';
        }
    };

    xhr.onload = function() {
        if (xhr.status === 200) {
            var response = JSON.parse(xhr.responseText);
            document.getElementById('mosaicImage').src = response.url;
            document.getElementById('mosaicImage').style.display = 'block';
            document.getElementById('downloadLink').href = response.url;
            document.getElementById('downloadLink').style.display = 'block';
        } else {
            alert('An error occurred while processing the image.');
        }
    };

    xhr.send(formData);
});

function streamLogs() {
    var logSource = new EventSource('/logs');
    var logsContainer = document.getElementById('logsContainer');

    logSource.onmessage = function(event) {
        var logEntry = document.createElement('div');
        logEntry.textContent = event.data;
        logsContainer.appendChild(logEntry);
        logsContainer.scrollTop = logsContainer.scrollHeight;
    };
}

function updateServerStatus() {
    fetch('/server-status')
        .then(response => response.json())
        .then(data => {
            document.getElementById('serverStatus').textContent = data["Server Status"];
        })
        .catch(error => console.error('Error fetching server status:', error));
}

document.addEventListener('DOMContentLoaded', function() {
    streamLogs();
    setInterval(updateServerStatus, 5000);
});
