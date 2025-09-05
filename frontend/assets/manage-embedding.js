// JavaScript for manage-embedding.html

document.addEventListener('DOMContentLoaded', () => {
    const dataSourceType = document.getElementById('data-source-type');
    const webSourceSection = document.getElementById('web-source-section');
    const codeSourceSection = document.getElementById('code-source-section');
    const pdfSourceSection = document.getElementById('pdf-source-section');
    const scrapeBtn = document.getElementById('scrape-btn');
    const loadCodeBtn = document.getElementById('load-code-btn');
    const scrapePdfBtn = document.getElementById('scrape-pdf-btn');
    const createVectorstoreBtn = document.getElementById('create-vectorstore-btn');
    const clearDocumentsBtn = document.getElementById('clear-documents-btn');
    const urlsInput = document.getElementById('urls-input');
    const scrapingMethodSelect = document.getElementById('scraping-method');
    const maxDepthGroup = document.getElementById('max-depth-group');
    const maxPagesGroup = document.getElementById('max-pages-group');
    const maxPagesInput = document.getElementById('max-pages-input');
    const urlsLabel = document.getElementById('urls-label');
    // Show/hide max-depth field based on scraping method
    scrapingMethodSelect.addEventListener('change', () => {
        if (scrapingMethodSelect.value === 'recursive') {
            maxDepthGroup.style.display = '';
            maxPagesGroup.style.display = 'none';
            urlsLabel.textContent = 'Enter starting URL for recursive crawling:';
            urlsInput.placeholder = 'https://www.odoo.com/documentation/17.0/';
        } else if (scrapingMethodSelect.value === 'sitemap') {
            maxDepthGroup.style.display = '';
            maxPagesGroup.style.display = '';
            urlsLabel.textContent = 'Enter sitemap.xml URL:';
            urlsInput.placeholder = 'https://www.example.com/sitemap.xml';
        } else if (scrapingMethodSelect.value === 'pdf-async') {
            maxDepthGroup.style.display = 'none';
            maxPagesGroup.style.display = 'none';
            urlsLabel.textContent = 'Enter PDF URLs to scrape (one per line):';
            urlsInput.placeholder = 'https://example.com/document.pdf\nhttps://another-site.com/manual.pdf';
        } else {
            maxDepthGroup.style.display = 'none';
            maxPagesGroup.style.display = 'none';
            urlsLabel.textContent = 'Enter URLs to scrape (one per line):';
            urlsInput.placeholder = 'https://www.odoo.com/documentation/17.0/\nhttps://en.wikipedia.org/wiki/Odoo';
        }
    });
    // Initialize visibility on page load
    if (scrapingMethodSelect.value === 'recursive') {
        maxDepthGroup.style.display = '';
        maxPagesGroup.style.display = 'none';
        urlsLabel.textContent = 'Enter starting URL for recursive crawling:';
        urlsInput.placeholder = 'https://www.odoo.com/documentation/17.0/';
    } else if (scrapingMethodSelect.value === 'sitemap') {
        maxDepthGroup.style.display = '';
        maxPagesGroup.style.display = '';
        urlsLabel.textContent = 'Enter sitemap.xml URL:';
        urlsInput.placeholder = 'https://www.example.com/sitemap.xml';
    } else if (scrapingMethodSelect.value === 'pdf-async') {
        maxDepthGroup.style.display = 'none';
        maxPagesGroup.style.display = 'none';
        urlsLabel.textContent = 'Enter PDF URLs to scrape (one per line):';
        urlsInput.placeholder = 'https://example.com/document.pdf\nhttps://another-site.com/manual.pdf';
    } else {
        maxDepthGroup.style.display = 'none';
        maxPagesGroup.style.display = 'none';
        urlsLabel.textContent = 'Enter URLs to scrape (one per line):';
        urlsInput.placeholder = 'https://www.odoo.com/documentation/17.0/\nhttps://en.wikipedia.org/wiki/Odoo';
    }
    const codeDirInput = document.getElementById('code-dir-input');
    const vectorstoreNameInput = document.getElementById('vectorstore-name');
    const docCountSpan = document.getElementById('doc-count');
    const documentList = document.getElementById('document-list');
    const logsPre = document.getElementById('logs');

    let scrapedDocuments = [];

    function logMessage(message, type = 'info') {
        const timestamp = new Date().toLocaleTimeString();
        const logLine = document.createElement('div');
        logLine.textContent = `[${timestamp}] ${message}`;
        if (type === 'error') {
            logLine.style.color = '#ff6b6b';
        } else if (type === 'success') {
            logLine.style.color = '#6bcb77';
        }
        logsPre.appendChild(logLine);
        logsPre.scrollTop = logsPre.scrollHeight;
    }

    function updateDocumentList() {
        docCountSpan.textContent = scrapedDocuments.length;
        documentList.innerHTML = '';
        const sources = {};
        scrapedDocuments.forEach(doc => {
            const source = doc.metadata.source || 'unknown';
            sources[source] = (sources[source] || 0) + 1;
        });
        for (const [source, count] of Object.entries(sources)) {
            const li = document.createElement('li');
            li.className = 'list-group-item d-flex justify-content-between align-items-center';
            li.textContent = source;
            const badge = document.createElement('span');
            badge.className = 'badge bg-primary rounded-pill';
            badge.textContent = `${count} chunks`;
            li.appendChild(badge);
            documentList.appendChild(li);
        }
    }

    // Toggle data source sections
    dataSourceType.addEventListener('change', () => {
        if (dataSourceType.value === 'web') {
            webSourceSection.style.display = '';
            codeSourceSection.style.display = 'none';
            pdfSourceSection.style.display = 'none';
        }else if (dataSourceType.value == 'pdf') {
            webSourceSection.style.display = 'none';
            codeSourceSection.style.display = 'none';
            pdfSourceSection.style.display = '';
        } else {
            webSourceSection.style.display = 'none';
            codeSourceSection.style.display = '';
            pdfSourceSection.style.display = 'none';
        }
    });

    scrapeBtn.addEventListener('click', async () => {
        const urls = urlsInput.value.trim().split('\n').filter(url => url.trim() !== '');
        const method = scrapingMethodSelect.value;
        if (urls.length === 0) {
            logMessage('Please enter at least one URL.', 'error');
            return;
        }
        logMessage(`Starting scraping for ${urls.length} URLs using ${method} method...`);
        scrapeBtn.disabled = true;
        try {
            let body = { urls, method };
            if (method === 'recursive') {
                const maxDepthSelect = document.getElementById('max-depth-select');
                body.max_depth = parseInt(maxDepthSelect.value);
            } else if (method === 'sitemap') {
                const maxDepthSelect = document.getElementById('max-depth-select');
                body.max_depth = parseInt(maxDepthSelect.value);
                const maxPages = maxPagesInput.value.trim();
                if (maxPages) {
                    body.max_pages = parseInt(maxPages);
                }
            }
            const response = await fetch('/scrape', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            if (result.success) {
                scrapedDocuments.push(...result.documents);
                logMessage(`Successfully scraped ${result.documents.length} document chunks.`, 'success');
                updateDocumentList();
            } else {
                logMessage(`Scraping failed: ${result.error}`, 'error');
            }
        } catch (error) {
            logMessage(`An error occurred: ${error.message}`, 'error');
        } finally {
            scrapeBtn.disabled = false;
        }
    });

    loadCodeBtn.addEventListener('click', async () => {
        const dirPath = codeDirInput.value.trim();
        if (!dirPath) {
            logMessage('Please enter a directory path.', 'error');
            return;
        }
        logMessage(`Loading Python source code from directory: ${dirPath}`);
        loadCodeBtn.disabled = true;
        try {
            const response = await fetch('/load-code', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ dir_path: dirPath }),
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            if (result.success) {
                scrapedDocuments.push(...result.documents);
                logMessage(`Loaded ${result.documents.length} code document chunks.`, 'success');
                updateDocumentList();
            } else {
                logMessage(`Code loading failed: ${result.error}`, 'error');
            }
        } catch (error) {
            logMessage(`An error occurred: ${error.message}`, 'error');
        } finally {
            loadCodeBtn.disabled = false;
        }
    });

    scrapePdfBtn.addEventListener('click', async () => {
        // upload PDFs and post for scrape
        const pdfUploadInput = document.getElementById('pdf-upload-input');
        const files = pdfUploadInput.files;
        
        if (files.length === 0) {
            logMessage('Please select PDF files to upload.', 'error');
            return;
        }
        
        logMessage(`Uploading and processing ${files.length} PDF file(s)...`);
        scrapePdfBtn.disabled = true;
        
        try {
            const formData = new FormData();
            for (let i = 0; i < files.length; i++) {
                formData.append('pdf_files', files[i]);
            }
            
            const response = await fetch('/load-pdfs', {
                method: 'POST',
                body: formData,
            });
            
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            
            if (result.success) {
                scrapedDocuments.push(...result.documents);
                logMessage(`Successfully processed ${result.documents.length} PDF document chunks.`, 'success');
                updateDocumentList();
                // Clear the file input
                pdfUploadInput.value = '';
            } else {
                logMessage(`PDF processing failed: ${result.error}`, 'error');
            }
        } catch (error) {
            logMessage(`An error occurred: ${error.message}`, 'error');
        } finally {
            scrapePdfBtn.disabled = false;
        }
    });

    createVectorstoreBtn.addEventListener('click', async () => {
        const vectorstoreName = vectorstoreNameInput.value.trim();
        if (scrapedDocuments.length === 0) {
            logMessage('No documents to process. Please add some data first.', 'error');
            return;
        }
        if (!vectorstoreName) {
            logMessage('Please provide a name for the vector store.', 'error');
            return;
        }
        logMessage(`Creating/updating vector store "${vectorstoreName}"...`);
        createVectorstoreBtn.disabled = true;
        try {
            const response = await fetch('/create-vectorstore', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    documents: scrapedDocuments,
                    name: vectorstoreName,
                }),
            });
            if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
            const result = await response.json();
            if (result.success) {
                logMessage(`Vector store "${vectorstoreName}" created/updated successfully at ${result.path}.`, 'success');
            } else {
                logMessage(`Failed to create vector store: ${result.error}`, 'error');
            }
        } catch (error) {
            logMessage(`An error occurred: ${error.message}`, 'error');
        } finally {
            createVectorstoreBtn.disabled = false;
        }
    });

    clearDocumentsBtn.addEventListener('click', () => {
        scrapedDocuments = [];
        updateDocumentList();
        logMessage('Cleared scraped documents list.');
    });

    logMessage('Embedding management UI initialized.');
});
