document.addEventListener('DOMContentLoaded', () => {
    // Theme Select Control
    const themeToggle = document.getElementById('theme-toggle');
    const htmlElement = document.documentElement;
    
    const savedTheme = localStorage.getItem('theme') || 'dark';
    htmlElement.setAttribute('data-theme', savedTheme);
    themeToggle.value = savedTheme;

    themeToggle.addEventListener('change', (e) => {
        const newTheme = e.target.value;
        htmlElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    });

    // Collapsible Sidebar Elements & Handlers
    const sidebarToggle = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('control-center-sidebar');
    const overlay = document.getElementById('sidebar-overlay');

    sidebarToggle.addEventListener('click', () => {
        if (window.innerWidth <= 950) {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('show');
        } else {
            document.body.classList.toggle('sidebar-collapsed');
        }
    });

    overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('show');
    });

    // DOM Elements
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const welcomePlaceholder = document.getElementById('welcome-placeholder');
    const resultsArea = document.getElementById('results-area');
    
    // Progress Bar & Steppers
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    const uploadPrompt = document.getElementById('upload-prompt');
    
    // Telemetry Summary Fields
    const resMimetype = document.getElementById('res-mimetype');
    const resFilesize = document.getElementById('res-filesize');
    const resMd5 = document.getElementById('res-md5');
    const overallRiskBadge = document.getElementById('overall-risk-badge');
    
    // Risk Score Values
    const overallScoreTxt = document.getElementById('overall-score-txt');
    const metadataScoreTxt = document.getElementById('metadata-score-txt');
    const pixelGaugeWrapper = document.getElementById('pixel-gauge-wrapper');
    const pixelScoreTxt = document.getElementById('pixel-score-txt');
    const ruleGaugeWrapper = document.getElementById('rule-gauge-wrapper');
    const ruleScoreTxt = document.getElementById('rule-score-txt');
    
    // Visual Panels
    const imageComparisonArea = document.getElementById('image-comparison-area');
    const nonImagePlaceholder = document.getElementById('non-image-placeholder');
    const imgOriginal = document.getElementById('img-original');
    const imgEla = document.getElementById('img-ela');
    const originalOverlays = document.getElementById('original-overlays');
    const elaOverlays = document.getElementById('ela-overlays');
    
    // Accordion Sections
    const accordionMetadata = document.getElementById('accordion-metadata');
    const accordionPixel = document.getElementById('accordion-pixel');
    const accordionRules = document.getElementById('accordion-rules');
    const accordionJson = document.getElementById('accordion-json');
    
    // Data Lists
    const metadataFlagsList = document.getElementById('metadata-flags-list');
    const metadataPropertiesTree = document.getElementById('metadata-properties-tree');
    const pixelAnomaliesList = document.getElementById('pixel-anomalies-list');
    const pixelStatsTree = document.getElementById('pixel-stats-tree');
    const ruleAssertionsList = document.getElementById('rule-assertions-list');
    const ruleExtractedTree = document.getElementById('rule-extracted-tree');
    
    // Developer JSON & Copy
    const jsonOutput = document.getElementById('json-output');
    const btnCopy = document.getElementById('copy-btn');
    const toastCopied = document.getElementById('toast-copied');
    
    // Reset Buttons (Bottom and Nav-bar)
    const btnReset = document.getElementById('btn-reset');
    const btnResetTop = document.getElementById('btn-reset-top');

    let currentReportData = null;

    // Trigger File Input Click
    dropZone.addEventListener('click', () => fileInput.click());

    // Drag & Drop handlers
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length > 0) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileUpload(e.target.files[0]);
        }
    });

    // Collapsible Accordion logic
    document.querySelectorAll('.accordion-header').forEach(header => {
        const section = header.parentElement;
        
        // Collapse JSON report by default on load, expand others
        if (section.id === 'accordion-json') {
            section.classList.add('collapsed');
        }

        header.addEventListener('click', () => {
            section.classList.toggle('collapsed');
        });
    });

    // Reset scanner logic
    function resetAnalysis() {
        resultsArea.style.display = 'none';
        welcomePlaceholder.style.display = 'block';
        btnResetTop.style.display = 'none';
        fileInput.value = '';
        progressContainer.style.display = 'none';
        uploadPrompt.style.display = 'flex';
        const uploadedState = document.getElementById('uploaded-state');
        if (uploadedState) uploadedState.style.display = 'none';
        originalOverlays.innerHTML = '';
        elaOverlays.innerHTML = '';
        const resLatency = document.getElementById('res-latency');
        if (resLatency) resLatency.textContent = '0.00s';
        
        if (ruleGaugeWrapper) ruleGaugeWrapper.style.display = 'none';
        if (accordionRules) accordionRules.style.display = 'none';
        if (ruleAssertionsList) ruleAssertionsList.innerHTML = '';
        if (ruleExtractedTree) ruleExtractedTree.innerHTML = '';
        
        // Reset steppers
        for (let i = 0; i <= 4; i++) {
            const step = document.getElementById(`step-${i}`);
            step.className = 'step-item';
            step.querySelector('.step-icon').textContent = (i + 1).toString();
        }
        progressFill.style.width = '0%';
        progressText.textContent = '0%';
    }

    if (btnReset) {
        btnReset.addEventListener('click', resetAnalysis);
    }
    if (btnResetTop) {
        btnResetTop.addEventListener('click', resetAnalysis);
    }

    // Developer Copy Button
    btnCopy.addEventListener('click', () => {
        if (currentReportData) {
            navigator.clipboard.writeText(JSON.stringify(currentReportData, null, 4))
                .then(() => {
                    toastCopied.classList.add('show');
                    setTimeout(() => {
                        toastCopied.classList.remove('show');
                    }, 2000);
                });
        }
    });

    // File Upload Handler
    function handleFileUpload(file) {
        // Show progress box, hide upload prompt
        uploadPrompt.style.display = 'none';
        progressContainer.style.display = 'block';
        
        // Stepper items refs
        const steppers = [
            { el: document.getElementById('step-0'), num: '1' },
            { el: document.getElementById('step-1'), num: '2' },
            { el: document.getElementById('step-2'), num: '3' },
            { el: document.getElementById('step-3'), num: '4' },
            { el: document.getElementById('step-4'), num: '5' }
        ];

        // Animate progress steppers
        function updateStep(stepIdx, status, pct) {
            const step = steppers[stepIdx];
            if (status === 'active') {
                step.el.className = 'step-item active';
                step.el.querySelector('.step-icon').textContent = step.num;
            } else if (status === 'completed') {
                step.el.className = 'step-item completed';
                step.el.querySelector('.step-icon').textContent = '✓';
            }
            progressFill.style.width = `${pct}%`;
            progressText.textContent = `${pct}%`;
        }

        // Initialize Stage 0
        updateStep(0, 'active', 5);

        // Stage transitions timers
        const t0 = setTimeout(() => updateStep(0, 'completed', 20), 500);
        const t1 = setTimeout(() => updateStep(1, 'active', 25), 600);
        const t2 = setTimeout(() => updateStep(1, 'completed', 45), 1500);
        const t3 = setTimeout(() => updateStep(2, 'active', 50), 1600);
        const t4 = setTimeout(() => updateStep(2, 'completed', 70), 3000);
        const t5 = setTimeout(() => updateStep(3, 'active', 75), 3100);
        const t6 = setTimeout(() => updateStep(3, 'completed', 90), 4500);
        const t7 = setTimeout(() => updateStep(4, 'active', 93), 4600);

        // Construct Form Data
        const formData = new FormData();
        formData.append('document', file);

        const startTime = performance.now();

        fetch('/api/analyze', {
            method: 'POST',
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.details || err.error || 'Server error'); });
            }
            return response.json();
        })
        .then(data => {
            const endTime = performance.now();
            const latencySec = ((endTime - startTime) / 1000).toFixed(2);
            data.latency = `${latencySec}s`;

            // End progress bars successfully
            clearTimeout(t0); clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
            clearTimeout(t4); clearTimeout(t5); clearTimeout(t6); clearTimeout(t7);
            
            // Mark all completed
            for (let i = 0; i <= 4; i++) {
                updateStep(i, 'completed', 100);
            }
            
            setTimeout(() => {
                progressContainer.style.display = 'none';
                const uploadedState = document.getElementById('uploaded-state');
                const uploadedFilename = document.getElementById('uploaded-filename');
                if (uploadedState && uploadedFilename) {
                    uploadedFilename.textContent = file.name;
                    uploadedState.style.display = 'flex';
                }
                renderDashboard(data);
            }, 500);
        })
        .catch(err => {
            clearTimeout(t0); clearTimeout(t1); clearTimeout(t2); clearTimeout(t3);
            clearTimeout(t4); clearTimeout(t5); clearTimeout(t6); clearTimeout(t7);
            alert(`Integrity analysis failed: ${err.message}`);
            // Reset dropzone
            uploadPrompt.style.display = 'flex';
            progressContainer.style.display = 'none';
            const uploadedState = document.getElementById('uploaded-state');
            if (uploadedState) uploadedState.style.display = 'none';
        });
    }

    // Dynamic HSL Risk Color Interpolator (0% green -> 50% yellow -> 100% red)
    function getRiskColorInterpolated(score) {
        let r, g, b;
        if (score < 50) {
            // Green (48, 209, 88) to Yellow (255, 159, 10)
            r = Math.floor(48 + (255 - 48) * (score / 50));
            g = Math.floor(209 + (159 - 209) * (score / 50));
            b = Math.floor(88 + (10 - 88) * (score / 50));
        } else {
            // Yellow (255, 159, 10) to Red (255, 69, 58)
            r = 255;
            g = Math.floor(159 + (69 - 159) * ((score - 50) / 50));
            b = Math.floor(10 + (58 - 10) * ((score - 50) / 50));
        }
        return `rgb(${r}, ${g}, ${b})`;
    }

    // Render properties in tree block
    function buildPropertiesTree(obj, container) {
        container.innerHTML = '';
        if (Object.keys(obj).length === 0) {
            container.innerHTML = '<p class="placeholder-text">No properties found.</p>';
            return;
        }

        function formatIfDate(val) {
            if (typeof val === 'string' && val.startsWith('D:')) {
                const match = val.match(/^D:(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})([+\-Z])?(\d{2})?'?(\d{2})?'?/);
                if (match) {
                    const [ , year, month, day, hour, min, sec, tzSign, tzHour, tzMin ] = match;
                    try {
                        let isoStr = `${year}-${month}-${day}T${hour}:${min}:${sec}`;
                        if (tzSign === 'Z') {
                            isoStr += 'Z';
                        } else if (tzSign) {
                            isoStr += `${tzSign}${tzHour || '00'}:${tzMin || '00'}`;
                        }
                        const d = new Date(isoStr);
                        if (!isNaN(d.getTime())) {
                            return d.toLocaleString();
                        }
                    } catch (e) {
                        return val;
                    }
                }
            }
            return val;
        }

        function createTree(data, parentEl) {
            for (const key in data) {
                const node = document.createElement('div');
                node.className = 'tree-node';
                
                const keySpan = document.createElement('span');
                keySpan.className = 'tree-key';
                keySpan.textContent = `${key}: `;
                node.appendChild(keySpan);
                
                const val = data[key];
                if (typeof val === 'object' && val !== null) {
                    node.appendChild(document.createTextNode('{'));
                    const childContainer = document.createElement('div');
                    childContainer.style.marginLeft = '12px';
                    createTree(val, childContainer);
                    node.appendChild(childContainer);
                    const closeBracket = document.createElement('div');
                    closeBracket.textContent = '}';
                    node.appendChild(closeBracket);
                } else {
                    const valSpan = document.createElement('span');
                    valSpan.className = 'tree-val';
                    valSpan.textContent = formatIfDate(val);
                    node.appendChild(valSpan);
                }
                parentEl.appendChild(node);
            }
        }
        createTree(obj, container);
    }

    // Dynamic numeric score updater
    function updateScoreDisplay(scoreTextEl, score) {
        const color = getRiskColorInterpolated(score);
        scoreTextEl.textContent = `${score}%`;
        scoreTextEl.style.color = color;
    }

    // Draw ELA anomaly overlays relative to parent scale
    function renderAnomalousOverlays(pixelReport) {
        originalOverlays.innerHTML = '';
        elaOverlays.innerHTML = '';
        
        if (!pixelReport || !pixelReport.grid_analysis.anomalous_blocks) return;

        const naturalWidth = imgOriginal.naturalWidth;
        const naturalHeight = imgOriginal.naturalHeight;

        if (!naturalWidth || !naturalHeight) return;

        pixelReport.grid_analysis.anomalous_blocks.forEach((a, idx) => {
            const [x1, y1, x2, y2] = a.bbox;
            const left = (x1 / naturalWidth) * 100;
            const top = (y1 / naturalHeight) * 100;
            const width = ((x2 - x1) / naturalWidth) * 100;
            const height = ((y2 - y1) / naturalHeight) * 100;

            const boxHtml = `<div id="anomaly-box-${idx}" class="anomaly-bounding-box" style="
                left: ${left}%; 
                top: ${top}%; 
                width: ${width}%; 
                height: ${height}%;
            " title="Anomaly: Row ${a.row}, Col ${a.col} (StdDev: ${a.std_dev_deviations}x)"></div>`;

            originalOverlays.insertAdjacentHTML('beforeend', boxHtml);
            // We'll also give an ID to the ELA one, appending -ela
            const elaBoxHtml = `<div id="anomaly-box-ela-${idx}" class="anomaly-bounding-box" style="
                left: ${left}%; 
                top: ${top}%; 
                width: ${width}%; 
                height: ${height}%;
            " title="Anomaly: Row ${a.row}, Col ${a.col} (StdDev: ${a.std_dev_deviations}x)"></div>`;
            elaOverlays.insertAdjacentHTML('beforeend', elaBoxHtml);
        });
    }

    // Handle overlays drawing on image load
    imgOriginal.onload = () => {
        if (currentReportData && currentReportData.pixel_report) {
            renderAnomalousOverlays(currentReportData.pixel_report);
        }
    };

    // Forensic Inspector modal helper
    function openForensicDetail(category) {
        if (!currentReportData) return;
        
        const modal = document.getElementById('forensic-detail-modal');
        const modalTitle = document.getElementById('modal-tile-title');
        const injectedContent = document.getElementById('modal-injected-content');
        
        injectedContent.innerHTML = ''; // reset
        
        if (category === 'attributes') {
            modalTitle.textContent = 'Document Attributes';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">File details</h4>
                        <div class="raw-properties-tree">
                            <div class="tree-node"><span class="tree-key">File Name:</span> <span class="tree-val">${currentReportData.file_system.file_name}</span></div>
                            <div class="tree-node"><span class="tree-key">File Size:</span> <span class="tree-val">${(currentReportData.file_system.size_bytes / 1024).toFixed(2)} KB (${currentReportData.file_system.size_bytes} bytes)</span></div>
                            <div class="tree-node"><span class="tree-key">Mime Type:</span> <span class="tree-val">${currentReportData.file_system.mime_type}</span></div>
                            <div class="tree-node"><span class="tree-key">MD5 Checksum:</span> <span class="tree-val code-text" style="font-size:11px;">${currentReportData.file_system.md5_checksum}</span></div>
                            <div class="tree-node"><span class="tree-key">Absolute Path:</span> <span class="tree-val">${currentReportData.file_system.absolute_path || 'N/A'}</span></div>
                        </div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Image Specifications</h4>
                        <div class="raw-properties-tree" id="attr-img-properties"></div>
                    </div>
                </div>
            `;
            const imgProperties = document.getElementById('attr-img-properties');
            if (currentReportData.metadata_report && currentReportData.metadata_report.extracted && currentReportData.metadata_report.extracted['Image Attributes']) {
                buildPropertiesTree(currentReportData.metadata_report.extracted['Image Attributes'], imgProperties);
            } else {
                imgProperties.innerHTML = '<p class="placeholder-text">No image attributes available.</p>';
            }
        }
        else if (category === 'rules') {
            modalTitle.textContent = 'Credential Integrity & Fact-Checks';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Rule Assertions & Audits</h4>
                        <div class="flag-list" id="modal-rule-assertions-list"></div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Extracted Values</h4>
                        <div class="raw-properties-tree" id="modal-rule-extracted-tree"></div>
                    </div>
                </div>
            `;
            
            const ruleAssertList = document.getElementById('modal-rule-assertions-list');
            const ruleExtractTree = document.getElementById('modal-rule-extracted-tree');
            
            if (currentReportData.rule_report && currentReportData.rule_report.document_type !== "UNKNOWN") {
                buildPropertiesTree(currentReportData.rule_report.extracted_data, ruleExtractTree);
                
                const flags = currentReportData.rule_report.validation_flags;
                const docType = currentReportData.rule_report.document_type;
                
                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'rule-summary-header';
                summaryDiv.style.marginBottom = '12px';
                summaryDiv.style.fontWeight = 'bold';
                const verificationMethod = currentReportData.rule_report.verification_method || "Format Matching";
                summaryDiv.innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <div>Extracted Type: <span class="path-badge path-fast" style="font-size:10px;">${docType}</span></div>
                        <div style="font-size: 0.85rem; color: var(--text-secondary); margin-top: 4px;">
                            Verify Method: <span class="path-badge path-fast" style="font-size:10px; background-color: rgba(0, 191, 255, 0.15); border-color: rgba(0, 191, 255, 0.3); color: #00bfff;">${verificationMethod}</span>
                        </div>
                    </div>
                `;
                ruleAssertList.appendChild(summaryDiv);

                if (flags && flags.length > 0) {
                    flags.forEach(flag => {
                        const el = document.createElement('div');
                        el.className = `flag-alert ${flag.severity.toLowerCase()}`;
                        el.innerHTML = `
                            <div class="alert-header">
                                <span>${flag.rule_id}</span>
                                <span class="path-badge ${flag.severity === 'High' ? 'path-neural' : flag.severity === 'Medium' ? 'path-fusion' : 'path-fast'}" style="font-size: 8px; padding: 2px 6px;">${flag.severity.toUpperCase()}</span>
                            </div>
                            <div class="alert-desc">${flag.description}</div>
                        `;
                        ruleAssertList.appendChild(el);
                    });
                } else {
                    const el = document.createElement('div');
                    el.className = 'flag-alert success';
                    el.style.borderColor = 'rgba(48, 209, 88, 0.3)';
                    el.style.backgroundColor = 'rgba(48, 209, 88, 0.08)';
                    el.innerHTML = `
                        <div class="alert-header"><span style="color:var(--success);">✓ ALL SANITY CHECKS PASSED</span></div>
                        <div class="alert-desc">All format, date chronology, checksum validations, and font style metrics conform to standard templates.</div>
                    `;
                    ruleAssertList.appendChild(el);
                }
            } else {
                ruleAssertList.innerHTML = '<p class="placeholder-text">No classification or validation rules executed for this document type.</p>';
                ruleExtractTree.innerHTML = '<p class="placeholder-text">No extracted fields available.</p>';
            }
        }
        else if (category === 'pixel') {
            modalTitle.textContent = 'Pixel ELA Diagnostics';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Anomalous Grid Coordinates</h4>
                        <div class="flag-list" id="modal-pixel-anomalies-list"></div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Global ELA Metrics</h4>
                        <div class="raw-properties-tree" id="modal-pixel-stats-tree"></div>
                    </div>
                </div>
            `;
            
            const anomaliesList = document.getElementById('modal-pixel-anomalies-list');
            const statsTree = document.getElementById('modal-pixel-stats-tree');
            
            if (currentReportData.pixel_report) {
                // Stats ELA details
                const stats = {
                    "Global Mean Error": currentReportData.pixel_report.ela_statistics.global_mean_error,
                    "Global Standard Deviation": currentReportData.pixel_report.ela_statistics.global_stddev_error,
                    "Global Peak Difference": currentReportData.pixel_report.ela_statistics.global_max_error,
                    "Grid size": `${currentReportData.pixel_report.grid_analysis.rows}x${currentReportData.pixel_report.grid_analysis.cols}`,
                    "Average Block Mean": currentReportData.pixel_report.grid_analysis.average_block_mean,
                    "Block Deviation Variance": currentReportData.pixel_report.grid_analysis.stddev_block_means,
                    "Verdict Status": currentReportData.pixel_report.tampering_risk
                };
                buildPropertiesTree(stats, statsTree);
                
                const pixelAnomalies = currentReportData.pixel_report.grid_analysis.anomalous_blocks;
                if (pixelAnomalies && pixelAnomalies.length > 0) {
                    pixelAnomalies.forEach((a, idx) => {
                        const el = document.createElement('div');
                        el.className = 'flag-alert high anomaly-item';
                        el.style.cursor = 'pointer';
                        el.innerHTML = `
                            <div class="alert-header">
                                <span>Grid block Anomaly #${idx+1}</span>
                                <span class="path-badge path-neural" style="font-size: 8px; padding: 2px 6px;">ANOMALY</span>
                            </div>
                            <div class="alert-desc">
                                Coordinate: Row <strong>${a.row}</strong>, Col <strong>${a.col}</strong><br>
                                BBox dimensions: [${a.bbox.join(', ')}]<br>
                                Standard Deviation offset: <strong>${a.std_dev_deviations}x</strong> (Mean: ${a.mean_error})
                            </div>
                        `;
                        
                        el.addEventListener('click', () => {
                            document.querySelectorAll('.anomaly-bounding-box.highlight').forEach(box => {
                                box.classList.remove('highlight');
                            });
                            const boxOrig = document.getElementById(`anomaly-box-${idx}`);
                            const boxEla = document.getElementById(`anomaly-box-ela-${idx}`);
                            if (boxOrig) boxOrig.classList.add('highlight');
                            if (boxEla) boxEla.classList.add('highlight');
                            
                            modal.style.display = 'none';
                        });
                        
                        anomaliesList.appendChild(el);
                    });
                } else {
                    anomaliesList.innerHTML = '<p class="placeholder-text">No local compression anomalies found (clean pixel profile).</p>';
                }
            } else {
                anomaliesList.innerHTML = '<p class="placeholder-text">Pixel analysis is not available or disabled for this file type.</p>';
                statsTree.innerHTML = '<p class="placeholder-text">No stats available.</p>';
            }
        }
        else if (category === 'provenance') {
            modalTitle.textContent = 'Digital Provenance & XMP History';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Warning Flags</h4>
                        <div class="flag-list" id="modal-metadata-flags-list"></div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Extracted Document Properties</h4>
                        <div class="raw-properties-tree" id="modal-metadata-properties-tree"></div>
                    </div>
                </div>
            `;
            
            const metaFlags = document.getElementById('modal-metadata-flags-list');
            const metaProps = document.getElementById('modal-metadata-properties-tree');
            
            buildPropertiesTree(currentReportData.metadata_report.extracted, metaProps);
            
            const flags = currentReportData.metadata_report.red_flags;
            if (flags && flags.length > 0) {
                flags.forEach(flag => {
                    const el = document.createElement('div');
                    el.className = `flag-alert ${flag.severity.toLowerCase()}`;
                    el.innerHTML = `
                        <div class="alert-header">
                            <span>${flag.rule_id}</span>
                            <span class="path-badge ${flag.severity === 'High' ? 'path-neural' : flag.severity === 'Medium' ? 'path-fusion' : 'path-fast'}" style="font-size: 8px; padding: 2px 6px;">${flag.severity.toUpperCase()}</span>
                        </div>
                        <div class="alert-desc">${flag.description}</div>
                    `;
                    metaFlags.appendChild(el);
                });
            } else {
                metaFlags.innerHTML = '<p class="placeholder-text">No metadata warnings found.</p>';
            }
        }
        else if (category === 'compression') {
            modalTitle.textContent = 'JPEG Compression & Structure';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Double JPEG Compression</h4>
                        <div class="raw-properties-tree" id="modal-compression-props"></div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">File Incremental Revisions</h4>
                        <div class="raw-properties-tree" id="modal-revisions-props"></div>
                    </div>
                </div>
            `;
            const compProps = document.getElementById('modal-compression-props');
            const revProps = document.getElementById('modal-revisions-props');
            
            if (currentReportData.metadata_report && currentReportData.metadata_report.extracted && currentReportData.metadata_report.extracted['Double JPEG Compression']) {
                buildPropertiesTree(currentReportData.metadata_report.extracted['Double JPEG Compression'], compProps);
            } else {
                compProps.innerHTML = '<p class="placeholder-text">No double JPEG compression details found (standard PNG or non-JPEG format).</p>';
            }
            
            if (currentReportData.metadata_report && currentReportData.metadata_report.extracted && currentReportData.metadata_report.extracted['Format-Specific Structure']) {
                buildPropertiesTree(currentReportData.metadata_report.extracted['Format-Specific Structure'], revProps);
            } else {
                revProps.innerHTML = '<p class="placeholder-text">No format-specific structure info (e.g. PDF revisions, PNG chunks) found.</p>';
            }
        }
        else if (category === 'fonts') {
            modalTitle.textContent = 'OCR character Baseline & Alignment';
            injectedContent.innerHTML = `
                <div class="modal-split-layout">
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Font Profiles & Alignment Metrics</h4>
                        <div class="raw-properties-tree" id="modal-fonts-props"></div>
                    </div>
                    <div class="column">
                        <h4 style="margin-top:0; color:var(--accent);">Baseline Deviations Checklist</h4>
                        <div class="flag-list" id="modal-fonts-deviations"></div>
                    </div>
                </div>
            `;
            const fontProps = document.getElementById('modal-fonts-props');
            const devList = document.getElementById('modal-fonts-deviations');
            
            if (currentReportData.metadata_report && currentReportData.metadata_report.extracted && currentReportData.metadata_report.extracted['OCR Character Metrics']) {
                const charMetrics = currentReportData.metadata_report.extracted['OCR Character Metrics'];
                buildPropertiesTree(charMetrics, fontProps);
                
                if (charMetrics.character_misalignment && charMetrics.character_misalignment > 0) {
                    const el = document.createElement('div');
                    el.className = 'flag-alert medium';
                    el.innerHTML = `
                        <div class="alert-header"><span>CHARACTER ALIGNMENT ALERT</span> <span class="path-badge path-fusion" style="font-size: 8px;">ALIGNMENT</span></div>
                        <div class="alert-desc">Detected <strong>${charMetrics.character_misalignment}</strong> characters deviating significantly from their line baseline heights. This points to character-level replacement forging.</div>
                    `;
                    devList.appendChild(el);
                } else {
                    const el = document.createElement('div');
                    el.className = 'flag-alert success';
                    el.style.borderColor = 'rgba(48, 209, 88, 0.3)';
                    el.style.backgroundColor = 'rgba(48, 209, 88, 0.08)';
                    el.innerHTML = `
                        <div class="alert-header"><span style="color:var(--success);">✓ ALIGNMENT CONSISTENT</span></div>
                        <div class="alert-desc">All characters conform to standard bounding box baseline levels without anomalous offsets.</div>
                    `;
                    devList.appendChild(el);
                }
            } else {
                fontProps.innerHTML = '<p class="placeholder-text">OCR font metrics are not available (no text lines analyzed).</p>';
                devList.innerHTML = '<p class="placeholder-text">No font checklist available.</p>';
            }
        }
        
        modal.style.display = 'flex';
    }

    // Dynamic dashboard tiles builder
    function buildDashboardTiles(data) {
        const tilesArea = document.getElementById('forensic-tiles-area');
        tilesArea.innerHTML = ''; // reset
        
        // 1. Document Attributes Tile
        const sizeKb = (data.file_system.size_bytes / 1024).toFixed(2);
        const format = data.file_system.mime_type.toUpperCase().split('/')[1] || data.file_system.file_extension.substring(1).toUpperCase();
        createTileCard(tilesArea, 'attributes', '🛠️', 'Document Attributes', 'clean', 'LOADED', [
            { label: 'Format', val: format },
            { label: 'Size', val: `${sizeKb} KB` },
            { label: 'MD5', val: data.file_system.md5_checksum.substring(0, 10) + '...' }
        ]);

        // 2. Rule Verification Tile
        let ruleStatus = 'clean';
        let ruleStatusText = 'PASSED';
        let ruleSummary = 'All checks passed';
        if (data.rule_report) {
            const flags = data.rule_report.validation_flags;
            const points = data.rule_report.risk_score;
            if (flags && flags.length > 0) {
                ruleStatus = points >= 45 ? 'failed' : 'warning';
                ruleStatusText = `${flags.length} ALERTS`;
                ruleSummary = `${flags.length} rules flagged`;
            } else if (data.rule_report.document_type === 'UNKNOWN') {
                ruleStatus = 'warning';
                ruleStatusText = 'UNKNOWN';
                ruleSummary = 'No rules match doc type';
            }
        }
        createTileCard(tilesArea, 'rules', '📜', 'Rule Verification', ruleStatus, ruleStatusText, [
            { label: 'Doc Type', val: data.rule_report ? data.rule_report.document_type : 'UNKNOWN' },
            { label: 'Verify Method', val: (data.rule_report && data.rule_report.verification_method) ? data.rule_report.verification_method : 'Format Matching' },
            { label: 'Rule Score', val: data.rule_report ? `${data.rule_report.risk_score}%` : 'N/A' },
            { label: 'Sanity Check', val: ruleSummary }
        ]);

        // 3. Pixel ELA Tile
        let pixelStatus = 'clean';
        let pixelStatusText = 'CLEAN';
        let anomalyCount = 0;
        if (data.pixel_report) {
            anomalyCount = data.pixel_report.grid_analysis.anomalous_blocks.length;
            const score = data.pixel_report.tampering_score;
            if (anomalyCount > 0 || score > 15) {
                pixelStatus = score >= 50 ? 'failed' : 'warning';
                pixelStatusText = `${score}% RISK`;
            }
        } else {
            pixelStatus = 'warning';
            pixelStatusText = 'SKIPPED';
        }
        createTileCard(tilesArea, 'pixel', '🖼️', 'Pixel ELA Diagnostics', pixelStatus, pixelStatusText, [
            { label: 'Anomalies', val: anomalyCount > 0 ? `${anomalyCount} blocks` : 'None' },
            { label: 'Tampering Score', val: data.pixel_report ? `${data.pixel_report.tampering_score}%` : 'N/A' },
            { label: 'Grid Map', val: data.pixel_report ? 'Available' : 'Unavailable' }
        ]);

        // 4. Digital Provenance Tile
        let provStatus = 'clean';
        let provStatusText = 'CLEAN';
        let creatorTool = 'N/A';
        if (data.metadata_report) {
            const flags = data.metadata_report.red_flags;
            if (flags && flags.length > 0) {
                provStatus = data.metadata_report.risk_score >= 40 ? 'failed' : 'warning';
                provStatusText = `${flags.length} FLAGGED`;
            }
            if (data.metadata_report.extracted && data.metadata_report.extracted['XMP Metadata']) {
                creatorTool = data.metadata_report.extracted['XMP Metadata']['CreatorTool'] || 'N/A';
                if (creatorTool.length > 18) creatorTool = creatorTool.substring(0, 15) + '...';
            }
        }
        createTileCard(tilesArea, 'provenance', '🧠', 'Digital Provenance', provStatus, provStatusText, [
            { label: 'Software', val: creatorTool },
            { label: 'Risk Score', val: data.metadata_report ? `${data.metadata_report.risk_score}%` : 'N/A' },
            { label: 'AI Metadata', val: data.metadata_report && data.metadata_report.extracted && data.metadata_report.extracted['XMP Metadata'] && data.metadata_report.extracted['XMP Metadata']['AiGenerated'] ? 'DETECTED' : 'None' }
        ]);

        // 5. Compression Analysis Tile
        let compStatus = 'clean';
        let compStatusText = 'CHECKED';
        let doubleJpeg = 'Clean';
        let pdfRevisions = 1;
        if (data.metadata_report && data.metadata_report.extracted) {
            if (data.metadata_report.extracted['Double JPEG Compression']) {
                doubleJpeg = data.metadata_report.extracted['Double JPEG Compression']['Double Compression'] ? 'DETECTED' : 'Clean';
                if (doubleJpeg === 'DETECTED') {
                    compStatus = 'warning';
                    compStatusText = 'DOUBLE COMP';
                }
            }
            if (data.metadata_report.extracted['Format-Specific Structure']) {
                pdfRevisions = data.metadata_report.extracted['Format-Specific Structure']['Incremental Revisions Count'] || 1;
                if (pdfRevisions > 1) {
                    compStatus = 'failed';
                    compStatusText = `${pdfRevisions} REVISIONS`;
                }
            }
        }
        createTileCard(tilesArea, 'compression', '⚙️', 'Compression & Structure', compStatus, compStatusText, [
            { label: 'Double Compression', val: doubleJpeg },
            { label: 'PDF Revisions', val: pdfRevisions > 1 ? `${pdfRevisions} found` : 'None' },
            { label: 'Stego Payload', val: data.metadata_report && data.metadata_report.extracted && data.metadata_report.extracted['Steganographic / Watermark Payloads'] && data.metadata_report.extracted['Steganographic / Watermark Payloads']['Tail Payload Detected'] ? 'YES' : 'Clean' }
        ]);

        // 6. Font Alignment Tile
        let fontsStatus = 'clean';
        let fontsStatusText = 'CONSISTENT';
        let verticalShift = 'None';
        if (data.metadata_report && data.metadata_report.extracted && data.metadata_report.extracted['OCR Character Metrics']) {
            const fontMetrics = data.metadata_report.extracted['OCR Character Metrics'];
            const misaligned = fontMetrics.character_misalignment || 0;
            if (misaligned > 0) {
                fontsStatus = misaligned > 5 ? 'failed' : 'warning';
                fontsStatusText = `${misaligned} SHIFTS`;
                verticalShift = `${misaligned} characters`;
            }
        }
        createTileCard(tilesArea, 'fonts', '🔤', 'Font & Alignment', fontsStatus, fontsStatusText, [
            { label: 'Baseline Offsets', val: verticalShift },
            { label: 'Font Faces', val: 'Consistent' },
            { label: 'Layout Flow', val: 'Aligned' }
        ]);
    }

    function createTileCard(container, category, icon, title, status, statusText, telemetryList) {
        const tile = document.createElement('div');
        tile.className = 'forensic-tile';
        tile.addEventListener('click', () => openForensicDetail(category));
        
        let telemetryHtml = '';
        telemetryList.forEach(item => {
            telemetryHtml += `
                <div class="telemetry-row" style="display:flex; justify-content:space-between; font-size:0.75rem; margin-top:2px;">
                    <span class="label" style="color:var(--text-secondary);">${item.label}:</span>
                    <span class="value" style="color:var(--text-primary); font-weight:600;">${item.val}</span>
                </div>
            `;
        });
        
        tile.innerHTML = `
            <div class="tile-header" style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid rgba(255,255,255,0.03); padding-bottom:6px;">
                <span class="tile-title" style="font-weight:700; font-size:0.92rem; display:flex; align-items:center; gap:6px;">${icon} ${title}</span>
                <span class="tile-status ${status}">${statusText}</span>
            </div>
            <div class="tile-telemetry" style="display:flex; flex-direction:column; gap:4px; margin-top:4px;">
                ${telemetryHtml}
            </div>
            <div class="tile-footer" style="margin-top:auto; font-size:0.7rem; color:var(--accent); font-weight:500; text-align:right; border-top:1px solid rgba(255,255,255,0.02); padding-top:6px;">
                Inspect details →
            </div>
        `;
        
        container.appendChild(tile);
    }

    // Render Dashboard Results
    function renderDashboard(data) {
        currentReportData = data;
        
        // Hide welcome state, show results state
        welcomePlaceholder.style.display = 'none';
        resultsArea.style.display = 'block';
        btnResetTop.style.display = 'block';

        // 1. Telemetry metadata row
        resMimetype.textContent = data.file_system.mime_type.toUpperCase().split('/')[1] || data.file_system.file_extension.substring(1).toUpperCase();
        resFilesize.textContent = (data.file_system.size_bytes / 1024).toFixed(2) + ' KB';
        resMd5.textContent = data.file_system.md5_checksum;
        const resLatency = document.getElementById('res-latency');
        if (resLatency) resLatency.textContent = data.latency || '0.00s';

        // Overall risk badge styling
        overallRiskBadge.textContent = `${data.overall_risk_level.toUpperCase()} RISK`;
        overallRiskBadge.className = 'path-badge';
        if (data.overall_risk_level === 'High') {
            overallRiskBadge.className = 'path-badge path-neural';
            overallRiskBadge.style.color = 'var(--danger)';
            overallRiskBadge.style.borderColor = 'rgba(255, 69, 58, 0.3)';
            overallRiskBadge.style.backgroundColor = 'rgba(255, 69, 58, 0.08)';
        } else if (data.overall_risk_level === 'Medium') {
            overallRiskBadge.className = 'path-badge path-fusion';
            overallRiskBadge.style.color = 'var(--warning)';
            overallRiskBadge.style.borderColor = 'rgba(255, 159, 10, 0.3)';
            overallRiskBadge.style.backgroundColor = 'rgba(255, 159, 10, 0.08)';
        } else {
            overallRiskBadge.className = 'path-badge path-fast';
        }

        // 2. Risk Scores
        updateScoreDisplay(overallScoreTxt, data.overall_risk_score);
        updateScoreDisplay(metadataScoreTxt, data.metadata_report.risk_score);

        if (data.rule_report && data.rule_report.document_type !== "UNKNOWN") {
            ruleGaugeWrapper.style.display = 'block';
            updateScoreDisplay(ruleScoreTxt, data.rule_report.risk_score);
        } else {
            ruleGaugeWrapper.style.display = 'none';
        }

        // 3. Pixel level ELA diagnostics checks (if image)
        if (data.pixel_report) {
            pixelGaugeWrapper.style.display = 'block';
            updateScoreDisplay(pixelScoreTxt, data.pixel_report.tampering_score);
            
            // Render Side-by-side comparators
            imageComparisonArea.style.display = 'flex';
            nonImagePlaceholder.style.display = 'none';
            
            // Set image paths - triggers onload overlays render
            imgOriginal.src = data.file_system.original_url;
            imgEla.src = data.ela_url || '';
        } else {
            pixelGaugeWrapper.style.display = 'none';
            imageComparisonArea.style.display = 'none';
            nonImagePlaceholder.style.display = 'block';
        }

        // 4. Build Tiles Grid
        buildDashboardTiles(data);

        // 5. JSON output prettier string
        jsonOutput.textContent = JSON.stringify(data, null, 4);
    }

    // Lightbox Carousel Controls
    let lightboxImages = [];
    let currentLightboxIndex = 0;

    function openLightbox(index) {
        if (!imgOriginal.src || imgOriginal.src === "" || imgOriginal.src.includes('#') || !currentReportData) return;
        
        lightboxImages = [
            { src: imgOriginal.src, title: 'Original Document', showOverlays: true },
            { src: imgEla.src, title: 'Error Level Map (ELA)', showOverlays: true }
        ];
        currentLightboxIndex = index;
        updateLightboxContent();
        document.getElementById('lightbox-modal').style.display = 'flex';
    }

    function updateLightboxContent() {
        const item = lightboxImages[currentLightboxIndex];
        const lightboxImg = document.getElementById('lightbox-img');
        const lightboxCaption = document.getElementById('lightbox-caption');
        const lightboxOverlays = document.getElementById('lightbox-overlays');
        
        lightboxImg.src = item.src;
        lightboxCaption.textContent = item.title;
        lightboxOverlays.innerHTML = '';
        
        lightboxImg.onload = () => {
            if (item.showOverlays && currentReportData && currentReportData.pixel_report) {
                const naturalWidth = lightboxImg.naturalWidth;
                const naturalHeight = lightboxImg.naturalHeight;
                if (naturalWidth && naturalHeight) {
                    currentReportData.pixel_report.grid_analysis.anomalous_blocks.forEach(a => {
                        const [x1, y1, x2, y2] = a.bbox;
                        const left = (x1 / naturalWidth) * 100;
                        const top = (y1 / naturalHeight) * 100;
                        const width = ((x2 - x1) / naturalWidth) * 100;
                        const height = ((y2 - y1) / naturalHeight) * 100;

                        const boxHtml = `<div class="anomaly-bounding-box" style="
                            left: ${left}%; 
                            top: ${top}%; 
                            width: ${width}%; 
                            height: ${height}%;
                        " title="Anomaly: Row ${a.row}, Col ${a.col}"></div>`;

                        lightboxOverlays.insertAdjacentHTML('beforeend', boxHtml);
                    });
                }
            }
        };
    }

    imgOriginal.addEventListener('click', () => openLightbox(0));
    imgEla.addEventListener('click', () => openLightbox(1));

    const lightboxPrev = document.getElementById('lightbox-prev');
    const lightboxNext = document.getElementById('lightbox-next');
    const lightboxClose = document.getElementById('lightbox-close');
    const lightboxModal = document.getElementById('lightbox-modal');

    if (lightboxPrev) {
        lightboxPrev.addEventListener('click', (e) => {
            e.stopPropagation();
            currentLightboxIndex = (currentLightboxIndex - 1 + lightboxImages.length) % lightboxImages.length;
            updateLightboxContent();
        });
    }

    if (lightboxNext) {
        lightboxNext.addEventListener('click', (e) => {
            e.stopPropagation();
            currentLightboxIndex = (currentLightboxIndex + 1) % lightboxImages.length;
            updateLightboxContent();
        });
    }

    if (lightboxClose) {
        lightboxClose.addEventListener('click', () => {
            lightboxModal.style.display = 'none';
        });
    }

    if (lightboxModal) {
        lightboxModal.addEventListener('click', () => {
            lightboxModal.style.display = 'none';
        });
        
        const lightboxWrapper = document.querySelector('.lightbox-content-wrapper');
        if (lightboxWrapper) {
            lightboxWrapper.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }

    // Forensic detail modal close handlers
    const forensicModal = document.getElementById('forensic-detail-modal');
    const forensicModalClose = document.getElementById('modal-close');
    
    if (forensicModalClose) {
        forensicModalClose.addEventListener('click', () => {
            forensicModal.style.display = 'none';
        });
    }
    
    if (forensicModal) {
        forensicModal.addEventListener('click', () => {
            forensicModal.style.display = 'none';
        });
        
        const modalCard = forensicModal.querySelector('.modal-card');
        if (modalCard) {
            modalCard.addEventListener('click', (e) => {
                e.stopPropagation();
            });
        }
    }
});
