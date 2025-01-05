
document.addEventListener('DOMContentLoaded', () => {
    const fileUpload = document.getElementById('file-upload');
    const fileDisplay = document.getElementById('file-display');
    const thumbnailsContainer = document.getElementById('thumbnails-container');
    const dropZone = document.querySelector('.left-container'); // Changed to use left-container as drop zone

    // Global variables
    let currentFiles = [];
    let currentFileData = null;
    let hasUnsavedChanges = false;

    function showLoader() {
        document.getElementById('loader').style.display = 'block';
    }
    
    function hideLoader() {
        document.getElementById('loader').style.display = 'none';
    }
    // File upload handler
    fileUpload.addEventListener('change', handleFiles);

    async function handleFiles(event) {
        const files = Array.from(event instanceof DragEvent ? event.dataTransfer.files : event.target.files);
        if (files.length === 0) return;

        currentFiles = files;

        const formData = new FormData();
        files.forEach(file => formData.append('files[]', file));

        try {
            showLoader();
            const response = await fetch('/upload', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            currentFileData = data;
            console.log(files)
            

            if (files.length === 1) {
                displaySingleFile(files[0], true);
                clearDetails(); // Clear details first
                setTimeout(() => updateDetails(data.details,files[0].name.toString()), 100); // Update details after a short delay
            } else {
                displayMultipleFiles(files);
                clearDetails();
            }
        } catch (error) {
            console.error('Error:', error);
            alert('Error uploading files'); 
            hideLoader();
        }
        finally{
            hideLoader();
        }
    }

    // Display single file
    function displaySingleFile(file, showDetails = false) {


        thumbnailsContainer.style.display = 'none';
        fileDisplay.style.display = 'flex';
        fileDisplay.innerHTML = '';

        const container = document.createElement('div');
        container.className = 'file-display-container';

        // Create content wrapper
        const contentWrapper = document.createElement('div');
        contentWrapper.className = 'content-wrapper';

  

        if (file.type.startsWith('image/')) {
            const img = document.createElement('img');
            img.src = URL.createObjectURL(file);
            img.className = 'file-content';
            contentWrapper.appendChild(img);
            
        } else if (file.type === 'application/pdf') {
            const embed = document.createElement('embed');
            embed.src = URL.createObjectURL(file);
            embed.type = 'application/pdf';
            embed.className = 'file-content';
            contentWrapper.appendChild(embed);
            
        }

        // Add file name
        const fileName = document.createElement('div');
        fileName.className = 'file-name';
        fileName.textContent = file.name;

        // Add close button if we have multiple files
        if (currentFiles.length > 1) {
            const closeBtn = document.createElement('button');
            closeBtn.className = 'close-button';
            closeBtn.innerHTML = '×';
            closeBtn.onclick = (e) => {
                e.stopPropagation();
                displayMultipleFiles(currentFiles);
                clearDetails();
            };
            container.appendChild(closeBtn);
        }

        container.appendChild(contentWrapper);
        container.appendChild(fileName);
        fileDisplay.appendChild(container);
        console.log(showDetails,currentFileData)
        console.log(file.name)
        if (showDetails && currentFileData) {
            updateDetails(currentFileData.details,file.name);
        }
    }

    // Display multiple files
    function displayMultipleFiles(files) {
        fileDisplay.style.display = 'none';
        thumbnailsContainer.style.display = 'grid';
        thumbnailsContainer.innerHTML = '';

        files.forEach((file, index) => {
            const thumbnail = document.createElement('div');
            thumbnail.className = 'thumbnail';

            // Create thumbnail content
            if (file.type.startsWith('image/')) {
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'cover';
                thumbnail.appendChild(img);
            } else if (file.type === 'application/pdf') {
                const pdfIcon = document.createElement('div');
                pdfIcon.textContent = 'PDF';
                pdfIcon.className = 'pdf-icon';
                thumbnail.appendChild(pdfIcon);
            }

            // Add file name below thumbnail
            const thumbFileName = document.createElement('div');
            thumbFileName.className = 'thumbnail-filename';
            thumbFileName.textContent = file.name;
            thumbnail.appendChild(thumbFileName);

            thumbnail.addEventListener('click', () => {
                displaySingleFile(file, true);
                console.log(file)
            });

            thumbnailsContainer.appendChild(thumbnail);
        });
    }

    // Drag and drop handling
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, highlight, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, unhighlight, false);
    });

    function highlight() {
        dropZone.classList.add('drag-highlight');
    }

    function unhighlight() {
        dropZone.classList.remove('drag-highlight');
    }

    dropZone.addEventListener('drop', (e) => {
        preventDefaults(e);
        unhighlight();
        handleFiles(e);
    });
    // Clear details
    function clearDetails() {
        ['category', 'invoice-number', 'invoice-date', 'tax-details', 'total-amount', 'total-tax','summary']
            .forEach(id => document.getElementById(id).textContent = '');
        document.querySelector('#line-items-table tbody').innerHTML = '';
    }

    // Track unsaved changes

    // Update details section
    function updateDetails(data,filename1) {
        console.log(data)
        console.log(filename1)
        const invoice = data[filename1];


        const updateLabel = (id, value) => {
            const element = document.getElementById(id);
            element.textContent = value;
            element.contentEditable = true;
            element.addEventListener('input', showSaveButton);
        };

        updateLabel('category', invoice.category);
        updateLabel('invoice-number', invoice.Invoice_Number);
        updateLabel('invoice-date', invoice.Invoice_Date);
        updateLabel('tax-details', invoice.Tax_Details);
        updateLabel('total-amount', invoice.Total_amount);
        updateLabel('total-tax', invoice.Total_tax);
        updateLabel('summary', invoice.Summary);

        updateTable(invoice.Line_Item_Details);
    }

    // Update table with editable rows
    function updateTable(lineItems) {
        const tableBody = document.querySelector('#line-items-table tbody');
        tableBody.innerHTML = '';

        lineItems.forEach(item => {
            const row = document.createElement('tr');
            row.innerHTML = `
            <td contenteditable="true">${item.Item_Name}</td>
            <td contenteditable="true">${item.Quantity}</td>
            <td contenteditable="true">$${item.Unit_Price}</td>
            <td contenteditable="true">$${item.Line_Total}</td>
        `;
            tableBody.appendChild(row);
            row.querySelectorAll('td').forEach(cell => cell.addEventListener('input', showSaveButton));
        });
    }

    function showSaveButton() {
        if (hasUnsavedChanges) return;
        hasUnsavedChanges = true;

        let saveBtn = document.querySelector('.save-changes');
        if (!saveBtn) {
            saveBtn = document.createElement('button');
            saveBtn.className = 'save-changes';
            saveBtn.textContent = 'Save Changes';
            saveBtn.addEventListener('click', saveChanges);
            document.body.appendChild(saveBtn);
        }
        saveBtn.classList.add('visible');
    }

    // Save changes and send to Flask
    async function saveChanges() {
        const updatedData = {
            category: document.getElementById('category').textContent,
            invoice_number: document.getElementById('invoice-number').textContent,
            invoice_date: document.getElementById('invoice-date').textContent,
            tax_details: document.getElementById('tax-details').textContent,
            total_amount: document.getElementById('total-amount').textContent.replace('$', ''),
            total_tax: document.getElementById('total-tax').textContent.replace('$', ''),
            Summary: document.getElementById('summary').textContent,
            line_items: Array.from(document.querySelectorAll('#line-items-table tbody tr')).map(row => {
                const cells = row.querySelectorAll('td');
                return {
                    item_name: cells[0].textContent,
                    quantity: cells[1].textContent,
                    unit_price: cells[2].textContent.replace('$', ''),
                    line_total: cells[3].textContent.replace('$', '')
                };
            })
        };

        try {
            const response = await fetch('/update-invoice', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(updatedData)
            });

            const result = await response.json();
            console.log('Server response:', result);

            if (response.ok) {
                alert('Invoice updated successfully!');
                hasUnsavedChanges = false;
                const saveBtn = document.querySelector('.save-changes');
                if (saveBtn) saveBtn.classList.remove('visible');
            } else {
                alert(`Error: ${result.error || 'Failed to update invoice'}`);
            }
        } catch (error) {
            console.error('Error saving changes:', error);
            alert('Failed to update invoice. Please try again.');
        }
    }
});


























