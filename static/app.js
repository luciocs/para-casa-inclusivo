let imageKeywords = [];
let adaptedText = "";
let carouselIndex = 0;
let whatsappUrl = "";
let comicRow = null;

// Function to update the status on the page
function updateStatus(message) {
    const statusText = document.getElementById('status-text');
    const spinner = document.getElementById('spinner');
    const buttons = document.querySelectorAll('button'); // Selects all buttons on the page

    if (message) {
        spinner.style.display = 'block';
        // Disable all buttons
        buttons.forEach(button => button.disabled = true);
    } else {
        spinner.style.display = 'none';
        // Enable all buttons
        buttons.forEach(button => button.disabled = false);
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
        alert('Texto copiado para área de transferência. Agora é só colar onde você precisar!');
    } catch (err) {
        alert('Falha ao copiar o texto: ' + err);
    }
}

function handleFeedback(isPositive) {
  // Add 'active' class to the clicked button and remove from the other
  document.getElementById('thumbs-up').classList.toggle('active', isPositive);
  document.getElementById('thumbs-down').classList.toggle('active', !isPositive);

  // Placeholder for the next step: Sending the feedback to the server
  console.log('Feedback given:', isPositive ? 'Positive' : 'Negative');
  
  // Show the additional feedback input
  document.getElementById('additional-feedback').style.display = 'block';
}

// Step 1: Define the sendTextFeedbackToServer function with consistent error handling
function sendTextFeedbackToServer(isPositive, textFeedback) {
  fetch('/feedback', { // The URL to the feedback route on your server
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      positive: isPositive, // Boolean indicating positive or negative feedback
      text: textFeedback // The additional text feedback from the user
    })
  })
  .then(response => {
    if (!response.ok) {
      // If the server response is not ok, throw an error
      throw new Error('Network response was not ok: ' + response.statusText);
    }
  })
  .catch(error => {
    // Handle any errors that occurred during the fetch operation
    console.error('Error sending feedback:', error);
    alert('Houve um erro ao enviar o seu feedback. Por favor, tente novamente.'); // Error message in Portuguese
  });
}

function categorizeFilesByNames(files) {
    // Define categories with associated keywords
    const categories = {
        'portugues': ['portugues', 'gramatica', 'vocabulario', 'redacao', 'ensaio', 'resumo', 'artigo', 'verbo', 'conjugacao', 'pronomes'],
        'imagens': ['imagens', 'fotos', 'figuras', 'gráficos', 'ilustracoes', 'desenhos', 'pinturas', 'diagramas'],
        'matematica': ['matematica', 'algebra', 'geometria', 'calculo', 'estatistica', 'probabilidade', 'logica', 'numeros', 'equacoes', 'funcoes'],
        'ciencias': ['ciencias', 'biologia', 'quimica', 'fisica', 'ecologia', 'genetica', 'astronomia', 'experiencias', 'laboratorio', 'cientifico'],
        'historia': ['historia', 'eventos', 'datas', 'civilizacoes', 'guerras', 'revolucoes', 'biografia', 'monarquia', 'republica', 'antiguidade'],
        'geografia': ['geografia', 'mapas', 'paises', 'continentes', 'capitais', 'clima', 'demografia', 'urbanizacao', 'relevo', 'hidrografia'],
        'literatura': ['livro', 'poema', 'literatura', 'conto', 'novela', 'crônica', 'fábula', 'drama', 'autobiografia', 'ensaio literario'],
        'arte': ['arte', 'pintura', 'desenho', 'escultura', 'cinema', 'fotografia', 'musica', 'danca', 'teatro', 'arquitetura'],
        'idiomas': ['ingles', 'espanhol', 'frances', 'linguas', 'conversacao', 'leitura', 'escrita'],
        'tecnologia': ['tecnologia', 'informatica', 'programacao', 'computacao', 'robotica', 'internet', 'software', 'hardware', 'redes', 'seguranca digital'],
    };

    // Use a Set to store categories to ensure uniqueness
    let usedCategoriesSet = new Set();

    files.forEach(file => {
        const fileNameNormalized = file.name.toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
        let fileCategorized = false;
        
        Object.entries(categories).forEach(([category, keywords]) => {
            if (keywords.some(keyword => fileNameNormalized.includes(keyword.normalize("NFD").replace(/[\u0300-\u036f]/g, "")))) {
                usedCategoriesSet.add(category);
                fileCategorized = true;
            }
        });

        // If the file does not match any category, add it to the "unknown" category
        if (!fileCategorized) {
            usedCategoriesSet.add('desconhecido'); // 'desconhecido' translates to 'unknown' in Portuguese
        }
    });

    // In case no files were categorized (for example, if there were no files or all were uncategorizable),
    // ensure the 'unknown' category is still present
    if (usedCategoriesSet.size === 0) {
        usedCategoriesSet.add('desconhecido');
    }

    return Array.from(usedCategoriesSet);
}

document.addEventListener('DOMContentLoaded', function() {
    const surveyModal = document.getElementById('surveyModal');
    const surveyForm = document.getElementById('surveyForm');
    
    // Check if profile survey was already submitted to avoid showing the modal again
    if (!localStorage.getItem('profileSurveySubmitted')) {
        surveyModal.style.display = "block";
    }

    surveyForm.addEventListener('submit', function(event) {
        event.preventDefault();

        // Collect survey form data
        const formData = new FormData(surveyForm);
        const userRole = formData.get('userRole');
        const schoolPhase = formData.get('schoolPhase');
        const childAge = formData.get('childAge');
        const diagnosis = formData.get('diagnosis');

        // This sets the user properties using the 'set' command
        gtag('set', {
          'user_properties': {
            'user_role': userRole,
            'school_phase': schoolPhase,
            'child_age': childAge,
            'diagnosis': diagnosis
          }
        });
      
        // Send a single tracking event to Google Analytics with custom dimensions
        gtag('event', 'survey_response', {
            'event_category': 'Survey',
            'event_label': 'User Survey',
            'non_interaction': true,
            'user_role': userRole, 
            'school_phase': schoolPhase, 
            'child_age': childAge, 
            'diagnosis': diagnosis
        });

        // Hide modal and mark survey as submitted
        localStorage.setItem('profileSurveySubmitted', 'true');
        surveyModal.style.display = "none";
        alert('Obrigado pelas suas respostas!');
    });
});


// Event Listener for the Submit Feedback Button
document.getElementById('submit-feedback').addEventListener('click', function() {
  const textFeedback = document.getElementById('feedback-text').value;
  const isPositive = document.getElementById('thumbs-up').classList.contains('active');
  if(textFeedback)
  {
    sendTextFeedbackToServer(isPositive, textFeedback);
  }
  alert('Obrigado pelo seu feedback!'); // Thank the user in Portuguese
  // Optionally, hide the additional feedback input after submission
  document.getElementById('additional-feedback').style.display = 'none';
});

document.getElementById('newAdaptationButton').addEventListener('click', function() {
  // New Adaptation tranking
  gtag('event', 'New Adaptation', {
      'event_category': 'Button',
      'event_label': 'New Adaptation'
  });
  window.open('https://www.paracasainclusivo.com.br', '_blank');
});

document.getElementById('changeButton').addEventListener('click', async function() {
    const newTheme = document.getElementById('newThemeInput').value.trim();
    const resultDiv = document.getElementById('result');
    
    if (newTheme && adaptedText) {
        try {
            // New Theme tranking
            gtag('event', 'New Theme', {
                'event_category': 'Button',
                'event_label': 'Change activity theme',
                'new_theme' : newTheme
            });
            updateStatus('Adaptando a atividade escolar com IA. Isso pode levar um minutinho...');
            // Send new theme to the server
            const response = await fetch('/change_theme', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ adapted_text: adaptedText, new_theme: newTheme })
            });

            const data = await response.json();

            if (data.error) {
                console.error('Error changing theme:', data.error);
                // Check for content policy violation error
                if (data.error === 'Your request was rejected due to a content policy violation.') {
                    alert('Desculpe, sua solicitação foi rejeitada devido a uma violação da política de conteúdo.');
                } else {
                    alert('Erro ao alterar o tema.');
                }
                // Error tracking
                gtag('event', 'New Theme Error', {
                    'event_category': 'Error',
                    'event_label': 'New Theme | Error',
                    'non_interaction': true
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
              
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada com o Novo Tema:</p>' + html;
                // Set the focus to the result div
                resultDiv.focus();
                // Clear the status
                updateStatus('');
                // Success tracking
                gtag('event', 'New Theme Success', {
                    'event_category': 'Success',
                    'event_label': 'New Theme | Success',
                    'non_interaction': true
                });              
            }          
        } catch (error) {
            console.error('Error sending request:', error);
            alert('Erro ao alterar o tema.');
            // Error tracking
            gtag('event', 'New Theme Error', {
                'event_category': 'Error',
                'event_label': 'New Theme | Error',
                'non_interaction': true
            });  
        }
    } else {
        alert('Por favor, insira um novo tema.');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    const uploadForm = document.getElementById('uploadForm');
    const resultDiv = document.getElementById('result');
    const imageDiv = document.getElementById('supportImages');  
    const copyButton = document.getElementById('copyButton');
    const fileInput = document.getElementById('fileInput');
    const fileLabel = document.getElementById('fileLabel');
    const cameraInput = document.getElementById('cameraInput');
    const cameraLabel = document.getElementById('cameraLabel');
    const generateImagesButton = document.getElementById('generateImagesButton');
    const modal = document.getElementById("imageModal");
    const modalImg = document.getElementById("modalImage");
    const span = document.getElementsByClassName("close")[0];  
    const generateComicButton = document.getElementById('generateComicButton');
    const comicDiv = document.getElementById('comicContainer');  
    const printComicBook = document.getElementById('printComicBook');
    const whatsappButton = document.getElementById("whatsappShareButton");
    const thumbsUp = document.getElementById('thumbs-up');
    const thumbsDown = document.getElementById('thumbs-down');
    const feedbackDiv = document.getElementById('feedback-section');
    const actionsDiv = document.getElementById('actions');
    const adaptationDiv = document.getElementById('adaptation-input');

    thumbsUp.addEventListener('click', function() {
      gtag('event', 'Positive feedback', {
          'event_category': 'Button',
          'event_label': 'Thumbs up on Adaptation'
      });
      handleFeedback(true);
    });
    thumbsDown.addEventListener('click', function() {
      gtag('event', 'Negative feedback', {
          'event_category': 'Button',
          'event_label': 'Thumbs down on Adaptation'
      });
      handleFeedback(false);
    });
    // Add event listener to the WhatsApp button
    whatsappButton.addEventListener('click', shareOnWhatsApp);
    // Attach the copy function to the copy button
    copyButton.addEventListener('click', copyToClipboard);  
      
    fileInput.addEventListener('change', () => {
      const maxFileSize = 4 * 1024 * 1024; // 4 MB in bytes
      const numFiles = fileInput.files.length;
      let isTooLarge = false;

      for (let i = 0; i < fileInput.files.length; i++) {
        if (fileInput.files[i].size > maxFileSize) {
          isTooLarge = true;
          break;
        }
      }

      if (isTooLarge) {
        // File too large tracking
        gtag('event', 'File too large', {
            'event_category': 'Warning',
            'event_label': 'File too large | Adapt | Warning'
        });          
        alert('Um ou mais arquivos excedem o limite de tamanho de 4MB. Por favor, selecione arquivos menores.');
        fileInput.value = ''; // Reset the file input
        fileLabel.textContent = "Imagem ou PDF da Atividade (máximo: 4MB)"; // Reset the file label
      } else if (numFiles > 0) {
        fileLabel.textContent = `${numFiles} arquivo(s) selecionado(s)`;
      } else {
        fileLabel.textContent = "Imagem ou PDF da Atividade (máximo: 4MB)";
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

        // Collect all files from both inputs into an array
        const allFiles = [...Array.from(fileInput.files), ...Array.from(cameraInput.files)];
      
        // Google Analytics event for button click
        gtag('event', 'Adapt', {
            'event_category': 'Button',
            'event_label': 'Adapt activity',
            'number_of_files' : allFiles.length,
            'file_types': allFiles.map(file => file.type).join(', '),
            'content_categories': categorizeFilesByNames(allFiles).join(', ')
        });

        // Check if at least one file is selected
        if (allFiles.length === 0) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>Por favor selecione um arquivo ou tire uma foto da atividade.</p>';
            // Warning tracking
            gtag('event', 'No file selected', {
                'event_category': 'Warning',
                'event_label': 'No file selected | Adapt | Warning',
                'non_interaction': true
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
                resultDiv.style.display = 'block';
                // Check for content policy violation error
                if (data.error === 'Your request was rejected due to a content policy violation.') {
                    resultDiv.innerHTML = '<p>Desculpe, sua solicitação foi rejeitada devido a uma violação da política de conteúdo.</p>';
                } else {
                    resultDiv.innerHTML = '<p>Error: ' + data.error + '</p>';
                }
                actionsDiv.style.display = "none";
                feedbackDiv.style.display = "none";
                // Error tracking
                gtag('event', 'Adaptation Error', {
                    'event_category': 'Error',
                    'event_label': 'Adapt | Error',
                    'non_interaction': true
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
              
                resultDiv.style.display = 'block';
                resultDiv.innerHTML = '<p>Atividade Escolar Adaptada:</p>' + html;
                // Set the focus to the result div
                resultDiv.focus();
                actionsDiv.style.display = 'block';
                // Show the button only on mobile
                if (window.innerWidth > 600) {
                  whatsappButton.style.display = "none";
                }
                feedbackDiv.style.display = 'block';
                adaptationDiv.style.display = "none";
              
                // Clear the status
                updateStatus('');
                // Success tracking
                gtag('event', 'Adaptation Success', {
                    'event_category': 'Success',
                    'event_label': 'Adapt | Success',
                    'non_interaction': true
                });              
            }
        } catch (error) {
            resultDiv.style.display = 'block';
            resultDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
            // Error tracking
            gtag('event', 'Adaptation Error', {
                'event_category': 'Error',
                'event_label': 'Adapt | Error',
                'non_interaction': true
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
                imageDiv.style.display = 'block';
                // Check for specific content policy violation error
                if (imageData.error === "Your request was rejected due to a content policy violation.") {
                    imageDiv.innerHTML = '<p>Desculpe, não podemos gerar imagens com base neste conteúdo devido à política de conteúdo.</p>';
                    // Error tracking for content policy violation
                    gtag('event', 'Generating images Error', {
                        'event_category': 'Error',
                        'event_label': 'Generate support images | Content Policy Violation',
                        'non_interaction': true
                    }); 
                } else {
                    imageDiv.innerHTML = '<p>Error: ' + imageData.error + '</p>';
                }
            } else {              
                const imageUrls = imageData.image_urls;

                // Display images
                imageDiv.style.display = 'block';
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
            imageDiv.style.display = 'block';
            imageDiv.innerHTML = '<p>Error: ' + error + '</p>';
            // Clear the status
            updateStatus('');
            // Error tracking
            gtag('event', 'Generating images Error', {
                'event_category': 'Error',
                'event_label': 'Generate support images | Error',
                'non_interaction': true
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
      
      // Check for content policy violation error
      if (panelData.error) {
          if (panelData.error === "Your request was rejected due to a content policy violation.") {
              throw new Error('content_policy_violation');
          } else {
              throw new Error('general_error');
          }
      }
      
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
        if (error.message === 'content_policy_violation') {
            comicDiv.innerHTML = '<p>Desculpe, não podemos gerar imagens com base neste conteúdo devido à política de conteúdo.</p>';
        } else {
            comicDiv.innerHTML = '<p>Erro: ' + error.message + '</p>';
        }
        updateStatus('');
        gtag('event', 'Generating comic book Error', {
            'event_category': 'Error',
            'event_label': 'Generate comic book | Error',
            'non_interaction': true
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