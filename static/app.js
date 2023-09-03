let imageKeywords = [];

// Function to update the status on the page
function updateStatus(message) {
  const statusText = document.getElementById('status-text');
  const spinner = document.getElementById('spinner');
  if (message) {
    spinner.style.display = 'block';
  } else {
    spinner.style.display = 'none';
  }
  statusText.innerHTML = message;
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
    const imageDiv = document.getElementById('supportImages');  
    const copyButton = document.getElementById('copyButton');
    // Listen for changes to the file input
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    // Listen for changes to the camera input
    const cameraInput = document.getElementById('cameraInput');
    const cameraLabel = document.getElementById('cameraLabel');
    // Add event listener for the "Add Support Images" button
    const searchImagesButton = document.getElementById('searchImagesButton');
    // Get the modal
    const modal = document.getElementById("imageModal");
    // Get the image inside the modal
    const modalImg = document.getElementById("modalImage");
    // Get the <span> element that closes the modal
    const span = document.getElementsByClassName("close")[0];  

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
            // Step 2: Running OCR and GPT-4
            updateStatus('Adaptando a atividade escolar com IA...');
            
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
                      
            if (data.error) {
                resultDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
                copyButton.style.display = "none";
            } else {
                const adaptedText = data.adapted_text;
                // Store image_keywords in the variable
                imageKeywords = data.image_keywords;
                
                // Convert Markdown to HTML using Showdown
                let converter = new showdown.Converter();
                let html = converter.makeHtml(data.adapted_text);              
              
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada:</p>' + html;
                copyButton.style.display = 'inline-block'; // or "block"
                searchImagesButton.style.display = 'inline-block';
              
                // Clear the status
                updateStatus('');
            }
        } catch (error) {
            resultDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
        }
    });
  
    // Event listener for Add Support Images button
    searchImagesButton.addEventListener('click', async () => {
        try {
            // Step 3: Searchin for support images
            updateStatus('Pesquisando imagens de apoio...');

            const response = await fetch('/fetch_images', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({image_keywords: imageKeywords}),
            });

            const imageData = await response.json();

            if (imageData.error) {
                imageDiv.innerHTML = '<p>Error: ' + imageData.error + '</p>';
            } else {
                const imageUrls = imageData.image_urls;

                // Display images
                imageDiv.innerHTML = '<p>Imagens de Apoio:</p>';
                imageUrls.forEach(url => {
                    const img = document.createElement('img');
                    img.src = url;
                    img.alt = 'Imagem de suporte';
                    img.className = 'support-image';
                    imageDiv.appendChild(img);
                });
                // Clear the status
                updateStatus('');
            };
          
        } catch (error) {
            imageDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
        }            
    });
  
    // Add an event listener to each image in the 'imageDiv'
    imageDiv.addEventListener("click", function(event) {
      if (event.target.tagName === "IMG") {
        modal.style.display = "block";
        modalImg.src = event.target.src;
      }
    });  
  
    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
      modal.style.display = "none";
    }  
  
});