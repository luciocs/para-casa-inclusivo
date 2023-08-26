// JavaScript to handle file upload and API calls

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');

    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];

        if (!file) {
            resultDiv.innerHTML = '<p>Please select a file.</p>';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

        try {
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.error) {
                resultDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
            } else {
                resultDiv.innerHTML = '<p>Adapted Text:</p><pre>' + data.adapted_text + '</pre>';
            }
        } catch (error) {
            resultDiv.innerHTML = '<p>Error: ' + error + '</p>';
        }
    });
});
