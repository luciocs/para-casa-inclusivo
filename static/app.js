// Function to update the status on the page
function updateStatus(message) {
  const statusDiv = document.getElementById('status');
  const spinner = document.getElementById('spinner');
  if (message) {
    spinner.style.display = 'block';
  } else {
    spinner.style.display = 'none';
  }
  statusDiv.innerHTML = message;
}

// Function to copy text and formatting to clipboard
async function copyToClipboard() {
    const resultDiv = document.getElementById('result');

    // Create a blob with the HTML content
    const blob = new Blob([resultDiv.innerHTML], { type: 'text/html' });

    // Use Clipboard API to copy the blob
    try {
        await navigator.clipboard.write([
            new ClipboardItem({
                'text/html': blob
            })
        ]);
        alert('Text and format copied successfully!');
    } catch (err) {
        alert('Failed to copy text: ' + err);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');
    const copyButton = document.getElementById('copyButton');
    // Listen for changes to the file input
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    // Listen for changes to the camera input
    const cameraInput = document.getElementById('cameraInput');
    const cameraLabel = document.getElementById('cameraLabel');

    // Attach the copy function to the copy button
    copyButton.addEventListener('click', copyToClipboard);  
      
    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            const fileName = fileInput.files[0].name;
            fileLabel.textContent = fileName;
        }
    });
    
    cameraInput.addEventListener('change', () => {
        if (cameraInput.files.length > 0) {
            const fileName = cameraInput.files[0].name;
            cameraLabel.textContent = fileName;
        }
    });  
  
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Step 1: Receiving Image/PDF
        updateStatus('Carregando Imagem/PDF...');
        
        const fileInput = document.getElementById('fileInput');
        const cameraInput = document.getElementById('cameraInput');
        const file = fileInput.files[0];
        const cameraFile = cameraInput.files[0];
        
        // Check if at least one file is selected
        if (!file && !cameraFile) {
            resultDiv.innerHTML = '<p>Por favor selecione um arquivo ou tire uma foto da atividade.</p>';
            return;
        }

        const formData = new FormData();
        
        // Append the selected file to the form data
        if (file) {
            formData.append('file', file);
        } else if (cameraFile) {
            formData.append('file', cameraFile);
        }

        try {
            // Step 2: Running OCR
            updateStatus('Recuperando o texto da Imagem/PDF com IA...');
            
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            // Step 3: Running GPT Prompt
            updateStatus('Adaptando a atividade escolar com GPT-4...');
            
            if (data.error) {
                resultDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
            } else {
                // Step 4: Showing Response
                updateStatus('Preparando para te mostrar o resultado...');
                
                // Convert Markdown to HTML using Showdown
                let converter = new showdown.Converter();
                let html = converter.makeHtml(data.adapted_text);              
              
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada:</p>' + html;
                
                // Clear the status
                updateStatus('');
            }
        } catch (error) {
            resultDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
        }
    });
});