// Function to update the status on the page
function updateStatus(message) {
    const statusDiv = document.getElementById('status');
    statusDiv.innerHTML = message;
}

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');
    const copyButton = document.getElementById('copyButton');

    copyButton.addEventListener('click', () => {
        // Create a temporary div element to hold the HTML content
        const tempDiv = document.createElement('div');

        // Get the adapted text in HTML form
        const adaptedTextHtml = resultDiv.innerHTML;

        // Set the temporary div's inner HTML to the adapted text
        tempDiv.innerHTML = adaptedTextHtml;

        // Extract plain text from the temporary div
        const adaptedText = tempDiv.textContent || tempDiv.innerText;

        // Continue with the existing copy to clipboard logic...
        // Create a textarea element to hold the text
        const textarea = document.createElement('textarea');

        // Set the textarea value to the adapted text
        textarea.value = adaptedText;

        // Append the textarea to the DOM
        document.body.appendChild(textarea);

        // Select the text
        textarea.select();

        // Execute the "copy" command
        document.execCommand('copy');

        // Remove the textarea from the DOM
        document.body.removeChild(textarea);

        // Notify the user
        alert('Texto copiado para a área de transferência!');
    });


    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Step 1: Receiving Image/PDF
        updateStatus('Carregando Imagem/PDF...');
        
        const fileInput = document.getElementById('fileInput');
        const file = fileInput.files[0];

        if (!file) {
            resultDiv.innerHTML = '<p>Por favor selecione um arquivo.</p>';
            return;
        }

        const formData = new FormData();
        formData.append('file', file);

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