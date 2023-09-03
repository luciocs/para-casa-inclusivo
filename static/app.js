let imageKeywords = [];
let adaptedText = "";

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
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const cameraInput = document.getElementById('cameraInput');
    const cameraLabel = document.getElementById('cameraLabel');
    const searchImagesButton = document.getElementById('searchImagesButton');
    const generateImagesButton = document.getElementById('generateImagesButton');
    const modal = document.getElementById("imageModal");
    const modalImg = document.getElementById("modalImage");
    const span = document.getElementsByClassName("close")[0];  
    const generateComicButton = document.getElementById('generateComicButton');
    const comicDiv = document.getElementById('comicContainer');  
    const printComicBook = document.getElementById('printComicBook');

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
            updateStatus('Adaptando a atividade escolar com IA. Isso pode levar um minutinho...');
            
            const response = await fetch('/', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
                      
            if (data.error) {
                resultDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
                copyButton.style.display = "none";
                searchImagesButton.style.display = "none";
                generateImagesButton.style.display = "none";
                generateComicButton.style.display = "none";
            } else {
                adaptedText = data.adapted_text;
                // Store image_keywords in the variable
                imageKeywords = data.image_keywords;
                
                // Convert Markdown to HTML using Showdown
                let converter = new showdown.Converter();
                let html = converter.makeHtml(adaptedText);              
              
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada:</p>' + html;
                copyButton.style.display = 'inline-block';
                searchImagesButton.style.display = 'inline-block';
                generateImagesButton.style.display = 'inline-block';
                generateComicButton.style.display = 'inline-block';
              
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

    // Event listener for Generate New Images button
    generateImagesButton.addEventListener('click', async () => {
        try {
            // Step 3: Generating new support images using Dall-E
            updateStatus('Criando imagens de apoio usando IA. Isso pode levar um minutinho...');

            const response = await fetch('/generate_images', {
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

    function displayComicPanels(comic_panels) {
      comicDiv.innerHTML = '<p>Gibi:</p>';  // Clear existing panels

      let comicRow = null;

      comic_panels.forEach((panel, index) => {
        // Create a new row every 2 panels
        if (index % 2 === 0) {
          comicRow = document.createElement('div');
          comicRow.className = 'comic-row';
        }

        // Create a comic panel
        const comicPanel = document.createElement('div');
        comicPanel.className = 'comic-panel';

        // Create the narration box
        const narrationBox = document.createElement('div');
        narrationBox.className = 'narration-box';
        // Convert Markdown to HTML using Showdown
        let converter = new showdown.Converter();
        let html = converter.makeHtml(panel.narration);              
        narrationBox.innerHTML = html;

        // Create the image element
        const img = document.createElement('img');
        img.src = panel.image_url;
        img.alt = 'Comic panel image';
        img.className = 'comic-image';

        // Append narration and image to the panel
        comicPanel.appendChild(narrationBox);
        comicPanel.appendChild(img);

        // Append the panel to the row
        comicRow.appendChild(comicPanel);

        // Append the row to the container every 2 panels
        if (index % 2 === 1) {
          comicDiv.appendChild(comicRow);
        }
      });
    }
    
    generateComicButton.addEventListener('click', async () => {
      try {
          // Step 3: Generating Comic Book
          updateStatus('Criando Gibi usando IA. Isso pode levar um minutinho ou dois...');

          // Make the API call to generate the comic book
          const response = await fetch('/generate_comic', {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ adapted_text: adaptedText }),
          });

          // Parse the response and display the comic panels
          const comicData = await response.json();
          if (comicData.error) {
              comicDiv.innerHTML = '<p>Error: ' + comicData.error + '</p>';
              printComicBook.style.display = 'none';
          } else {
              if (comicData.comic_panels) {
                displayComicPanels(comicData.comic_panels);
                printComicBook.style.display = 'inline-block';
              }
          }
          // Clear the status
          updateStatus('');        
      } catch (error) {
          comicDiv.innerHTML = '<p>Error: ' + error + '</p>';
          // Clear the status
          updateStatus('');
      }            
    });
  
    printComicBook.addEventListener("click", function() {
        // Clone the elements you want to print
        const headerClone = document.querySelector('.header').cloneNode(true);
        const comicBookClone = comicDiv.cloneNode(true);

        // Create a temporary container
        const printContainer = document.createElement('div');

        // Append cloned elements to the temporary container
        printContainer.appendChild(headerClone);
        printContainer.appendChild(comicBookClone);

        // Save the current body
        const originalBody = document.body.innerHTML;

        // Replace the body with the temporary container
        document.body.innerHTML = '';
        document.body.appendChild(printContainer);

        // Trigger print
        window.print();

        // Restore the original body
        document.body.innerHTML = originalBody;   
    });
  
});