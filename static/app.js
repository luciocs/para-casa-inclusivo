let imageKeywords = [];
let adaptedText = "";
let carouselIndex = 0;
let whatsappUrl = "";
let comicRow = null;

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

// Function to share on WhatsApp
function shareOnWhatsApp() {
    // Google Analytics event for button click
    gtag('event', 'Share on WhatsApp', {
        'event_category': 'Button',
        'event_label': 'Share adapted text on WhatsApp'
    });
    window.open(whatsappUrl, '_blank');
}

// Function to copy text and formatting to clipboard
async function copyToClipboard() {
    // Google Analytics event for button click
    gtag('event', 'Copy to clipboard', {
        'event_category': 'Button',
        'event_label': 'Copy adapted text to clipboard'
    });  
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
    const whatsappButton = document.getElementById("whatsappShareButton");

    // Add event listener to the WhatsApp button
    whatsappButton.addEventListener('click', shareOnWhatsApp);
    // Attach the copy function to the copy button
    copyButton.addEventListener('click', copyToClipboard);  
      
    fileInput.addEventListener('change', () => {
      const numFiles = fileInput.files.length;
      if (numFiles > 0) {
          fileLabel.textContent = `${numFiles} arquivo(s) selecionado(s)`;
      } else {
          fileLabel.textContent = "Escolha o arquivo";
      }
    });

    cameraInput.addEventListener('change', () => {
      const numFiles = cameraInput.files.length;
      if (numFiles > 0) {
          cameraLabel.textContent = `${numFiles} foto(s) tirada(s)`;
      } else {
          cameraLabel.textContent = "Tire uma foto";
      }
    });
 
  
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Google Analytics event for button click
        gtag('event', 'Adapt', {
            'event_category': 'Button',
            'event_label': 'Adapt activity'
        });
        // Collect all files from both inputs into an array
        const allFiles = [...Array.from(fileInput.files), ...Array.from(cameraInput.files)];

        // Check if at least one file is selected
        if (allFiles.length === 0) {
            resultDiv.innerHTML = '<p>Por favor selecione um arquivo ou tire uma foto da atividade.</p>';
            // Warning tracking
            gtag('event', 'No file selected', {
                'event_category': 'Warning',
                'event_label': 'No file selected | Adapt | Warning'
            });          
            return;
        }

        // Step 1: Receiving Image/PDF
        updateStatus('Carregando Imagem/PDF...');
        resultDiv.innerHTML = '';
      
        // Create FormData and append all files to it
        const formData = new FormData();
        allFiles.forEach((file, index) => {
            formData.append('file' + index, file);
        });      
      
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
                whatsappButton.style.display = "none";
                searchImagesButton.style.display = "none";
                generateImagesButton.style.display = "none";
                generateComicButton.style.display = "none";
                // Error tracking
                gtag('event', 'Adaptation Error', {
                    'event_category': 'Error',
                    'event_label': 'Adapt | Error'
                });              
            } else {
                adaptedText = data.adapted_text;
                // Store image_keywords in the variable
                imageKeywords = data.image_keywords;
                // Store image_keywords in the variable
                whatsappUrl = data.whatsapp_url;

                
                // Convert Markdown to HTML using Showdown
                let converter = new showdown.Converter();
                let html = converter.makeHtml(adaptedText);              
              
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada:</p>' + html;
                copyButton.style.display = 'inline-block';
                // Show the button only on mobile
                if (window.innerWidth <= 600) {
                  whatsappButton.style.display = "inline-block";
                }                
                searchImagesButton.style.display = 'inline-block';
                generateImagesButton.style.display = 'inline-block';
                generateComicButton.style.display = 'inline-block';
              
                // Clear the status
                updateStatus('');
                // Success tracking
                gtag('event', 'Adaptation Success', {
                    'event_category': 'Success',
                    'event_label': 'Adapt | Success'
                });              
            }
        } catch (error) {
            resultDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
            // Error tracking
            gtag('event', 'Adaptation Error', {
                'event_category': 'Error',
                'event_label': 'Adapt | Error'
            });                        
        }
    });
  
    // Event listener for Add Support Images button
    searchImagesButton.addEventListener('click', async () => {
        try {
            // Google Analytics event for button click
            gtag('event', 'Search images', {
                'event_category': 'Button',
                'event_label': 'Search support images on web'
            });
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
            // Error tracking
            gtag('event', 'Searching images Error', {
                'event_category': 'Error',
                'event_label': 'Search support images on web | Error'
            });                        
        }            
    });

    // Event listener for Generate New Images button
    generateImagesButton.addEventListener('click', async () => {
        try {
            // Google Analytics event for button click
            gtag('event', 'Generate images', {
                'event_category': 'Button',
                'event_label': 'Generate support images'
            });
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
            // Error tracking
            gtag('event', 'Generating images Error', {
                'event_category': 'Error',
                'event_label': 'Generate support images | Error'
            });                                  
        }            
    });  
  
    // Add an event listener to each image in the 'imageDiv'
    imageDiv.addEventListener("click", function(event) {
      if (event.target.tagName === "IMG") {
        // Google Analytics event for button click
        gtag('event', 'Expand image', {
            'event_category': 'Button',
            'event_label': 'Expand generated image'
        });
        modal.style.display = "flex";
        modalImg.src = event.target.src;
      }
    });  
  
    // Add an event listener to each image in the 'examples'
    document.getElementById('examples').addEventListener("click", function(event) {
      if (event.target.tagName === "IMG") {
        // Google Analytics event for button click
        gtag('event', 'Expand image', {
            'event_category': 'Button',
            'event_label': 'Expand example image'
        });
        modal.style.display = "flex";
        modalImg.src = event.target.src;
      }
    });  

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
      modal.style.display = "none";
    }
  
    async function displaySingleComicPanel(panel_text, index) {
      const response = await fetch('/generate_single_comic_panel', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ panel_text }),
      });

      const panelData = await response.json();
      const panel = panelData.comic_panel;

      const comicPanel = document.createElement('div');
      comicPanel.className = 'comic-panel';

      // Create a new row every 2 panels
      if (index % 2 === 0) {
        comicRow = document.createElement('div');
        comicRow.className = 'comic-row';
      }      
      
      const narrationBox = document.createElement('div');
      narrationBox.className = 'narration-box';
      let converter = new showdown.Converter();
      let html = converter.makeHtml(panel.narration);              
      narrationBox.innerHTML = html;

      const img = document.createElement('img');
      img.src = panel.image_url;
      img.alt = 'Comic panel image';
      img.className = 'comic-image';

      comicPanel.appendChild(narrationBox);
      comicPanel.appendChild(img);

      // Append the panel to the row
      comicRow.appendChild(comicPanel);

      // Append the row to the container every 2 panels
      if (index % 2 === 1) {
        comicDiv.appendChild(comicRow);
      }      
    }

    generateComicButton.addEventListener('click', async () => {
      try {
        // Google Analytics event for button click
        gtag('event', 'Generate comic book', {
            'event_category': 'Button',
            'event_label': 'Generate comic book'
        });
        updateStatus('Criando Gibi usando IA. Isso pode levar um minutinho ou dois...');
        const response = await fetch('/generate_comic_output', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ adapted_text: adaptedText }),
        });

        const comicData = await response.json();
        const comicOutputArray = comicData.comic_output;

        comicDiv.innerHTML = '<p>Gibi:</p>';  // Clear existing panels

        for (let i = 0; i < comicOutputArray.length; i++) {
          updateStatus('Criando Gibi usando IA. Criando painel ' + (i + 1) + ' de ' + comicOutputArray.length + '...');
          await displaySingleComicPanel(comicOutputArray[i], i);
        }

        // Handle the last row if there is an odd number of panels
        if (comicOutputArray.length % 2 !== 0) {
          comicDiv.appendChild(comicRow);
        }

        printComicBook.style.display = 'inline-block';
        updateStatus('');
      } catch (error) {
        comicDiv.innerHTML = '<p>Error: ' + error + '</p>';
        updateStatus('');
        // Error tracking
        gtag('event', 'Generating comic book Error', {
            'event_category': 'Error',
            'event_label': 'Generate comic book | Error'
        });                                  
      }            
    });
    
    printComicBook.addEventListener("click", function() {
        // Google Analytics event for button click
        gtag('event', 'Print comic book', {
            'event_category': 'Button',
            'event_label': 'Print comic book'
        });
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
  
    document.getElementById('prevBtn').addEventListener('click', () => {
      // Google Analytics event for button click
      gtag('event', 'Navegate examples', {
          'event_category': 'Button',
          'event_label': 'Navegate examples'
      });
      move(-2);  // Move two items back
    });

    document.getElementById('nextBtn').addEventListener('click', () => {
      // Google Analytics event for button click
      gtag('event', 'Navegate examples', {
          'event_category': 'Button',
          'event_label': 'Navegate examples'
      });
      move(2);  // Move two items forward
    });

    function move(step) {
      const wrapper = document.querySelector('.carousel-wrapper');
      carouselIndex += step;
      carouselIndex = Math.max(0, Math.min(carouselIndex, wrapper.children.length - 2));  // Adjust here to stop at the correct item
      const newOffset = -carouselIndex * 300;  // 300 is the width of each carousel item
      wrapper.style.transform = `translateX(${newOffset}px)`;
    }
  
});