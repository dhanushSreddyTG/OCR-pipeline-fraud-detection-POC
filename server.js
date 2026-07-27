const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const { exec } = require('child_process');

const app = express();
const PORT = process.env.PORT || 3060;

// Ensure uploads directory exists
const UPLOADS_DIR = path.join(__dirname, 'public', 'uploads');
if (!fs.existsSync(UPLOADS_DIR)) {
    fs.mkdirSync(UPLOADS_DIR, { recursive: true });
}

// Serve public directory statically
app.use(express.static(path.join(__dirname, 'public')));
app.use(express.json());

// Configure multer storage
const storage = multer.diskStorage({
    destination: (req, file, cb) => {
        cb(null, UPLOADS_DIR);
    },
    filename: (req, file, cb) => {
        // Safe filename with timestamp prefix
        const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
        const ext = path.extname(file.originalname);
        cb(null, file.fieldname + '-' + uniqueSuffix + ext);
    }
});

const upload = multer({
    storage: storage,
    limits: { fileSize: 10 * 1024 * 1024 } // 10MB limit
});

// Endpoint to analyze file
app.post('/api/analyze', upload.single('document'), (req, res) => {
    if (!req.file) {
        return res.status(400).json({ error: 'No file uploaded.' });
    }

    const uploadedFilePath = req.file.path;
    const fileBaseName = path.basename(uploadedFilePath, path.extname(uploadedFilePath));
    const elaImageName = `${fileBaseName}_ela.png`;
    const elaImagePath = path.join(UPLOADS_DIR, elaImageName);

    // Check if docType override is passed in request
    const docType = req.body.docType || '';
    let cmd = `python3 fraud_detector.py "${uploadedFilePath}" -f json --ela-output "${elaImagePath}"`;
    if (docType && /^[a-zA-Z0-9_-]+$/.test(docType)) {
        cmd += ` --doc-type "${docType}"`;
    }

    exec(cmd, (error, stdout, stderr) => {
        if (error) {
            console.error(`Execution error: ${error}`);
            console.error(`stderr: ${stderr}`);
            return res.status(500).json({
                error: 'Failed to run analysis program.',
                details: stderr || error.message
            });
        }

        try {
            const report = JSON.parse(stdout);

            // Add static urls for frontend access
            report.file_system.original_url = `/uploads/${req.file.filename}`;

            // If ELA ran successfully and image was saved
            if (fs.existsSync(elaImagePath)) {
                report.ela_url = `/uploads/${elaImageName}`;
            }

            res.json(report);
        } catch (parseError) {
            console.error(`JSON Parse error: ${parseError}`);
            console.error(`stdout raw: ${stdout}`);
            res.status(500).json({
                error: 'Failed to parse analyzer response.',
                details: stdout
            });
        }
    });
});

app.listen(PORT, '0.0.0.0', () => {
    console.log(`Professional Document Fraud Detection server listening on port ${PORT}`);
});
