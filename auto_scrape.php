<?php
require_once 'config.php';

/**
 * PHP Wrapper for Python Google Maps Scraper
 */

class AutoScraper {
    private $pythonPath;
    private $scriptPath;

    public function __construct() {
        // Try to detect Python path
        $this->pythonPath = $this->detectPython();
        $this->scriptPath = __DIR__ . '/google_maps_scraper.py';
    }

    private function detectPython() {
        // Use wrapper script that sets correct PYTHONPATH
        return __DIR__ . '/run_scraper.sh';
    }

    private function getScriptDir() {
        return __DIR__;
    }

    public function checkPythonSetup() {
        // Check if Python is installed
        $pythonVersion = shell_exec("{$this->pythonPath} --version 2>&1");

        if (empty($pythonVersion)) {
            return [
                'installed' => false,
                'message' => 'Python is not installed or not found in PATH'
            ];
        }

        // Check if Playwright is installed
        $playwrightCheck = shell_exec("{$this->pythonPath} -c \"import playwright\" 2>&1");

        return [
            'installed' => true,
            'python_version' => trim($pythonVersion),
            'playwright_installed' => empty($playwrightCheck) || strpos($playwrightCheck, 'ModuleNotFoundError') === false,
            'script_exists' => file_exists($this->scriptPath)
        ];
    }

    public function scrapeGoogleMaps($query, $location, $maxResults = 20, $headless = true) {
        // Escape arguments
        $query_escaped = escapeshellarg($query);
        $location_escaped = escapeshellarg($location);
        $maxResults = (int)$maxResults;
        $headless_str = $headless ? 'true' : 'false';

        // Build command to run scraper as the current user (narinder)
        // This bypasses the Apache daemon user SIGTRAP issue
        $scriptDir = $this->getScriptDir();
        $command = sprintf(
            'cd %s && sudo -u narinder ./run_scraper.sh google_maps_scraper.py %s %s %s %s 2>&1',
            escapeshellarg($scriptDir),
            $query_escaped,
            $location_escaped,
            $maxResults,
            $headless_str
        );

        // Execute the command and capture output
        $output = shell_exec($command);

        // Extract JSON result from output
        if (preg_match('/\{.*"success".*\}/s', $output, $matches)) {
            $result = json_decode($matches[0], true);
            $result['raw_output'] = $output;
            return $result;
        }

        return [
            'success' => false,
            'message' => 'Failed to parse Python script output',
            'raw_output' => $output
        ];
    }

    public function getScrapingProgress() {
        // This could be enhanced with a progress file or database tracking
        return [
            'status' => 'idle',
            'message' => 'No active scraping session'
        ];
    }
}

// Handle AJAX requests
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    header('Content-Type: application/json');

    $action = $_POST['action'] ?? '';
    $scraper = new AutoScraper();

    switch ($action) {
        case 'check_setup':
            echo json_encode($scraper->checkPythonSetup());
            exit;

        case 'scrape':
            $query = $_POST['query'] ?? '';
            $location = $_POST['location'] ?? '';
            $maxResults = $_POST['max_results'] ?? 20;
            // Checkbox: if set and 'on', run headless; otherwise visible
            $headless = isset($_POST['headless']) && $_POST['headless'] === 'on';

            if (empty($query) || empty($location)) {
                echo json_encode([
                    'success' => false,
                    'message' => 'Query and location are required'
                ]);
                exit;
            }

            $result = $scraper->scrapeGoogleMaps($query, $location, $maxResults, $headless);
            echo json_encode($result);
            exit;

        default:
            echo json_encode([
                'success' => false,
                'message' => 'Invalid action'
            ]);
            exit;
    }
}

// Get setup status for page load
$scraper = new AutoScraper();
$setup = $scraper->checkPythonSetup();

// Predefined search configurations
$searchConfigs = [
    ['query' => 'immigration consultant', 'cities' => ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Pune', 'Hyderabad', 'Ahmedabad', 'Kolkata']],
    ['query' => 'IELTS coaching', 'cities' => ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Pune', 'Chandigarh', 'Jaipur']],
    ['query' => 'PTE coaching', 'cities' => ['Delhi', 'Mumbai', 'Bangalore', 'Hyderabad', 'Pune', 'Ahmedabad']],
    ['query' => 'visa consultant', 'cities' => ['Delhi', 'Mumbai', 'Bangalore', 'Chennai', 'Pune']],
];
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Automated Google Maps Scraper</title>
    <link rel="stylesheet" href="style.css">
    <style>
        .setup-status {
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        .setup-status.success { background: #d4edda; border-left: 4px solid #28a745; }
        .setup-status.error { background: #f8d7da; border-left: 4px solid #dc3545; }
        .setup-status.warning { background: #fff3cd; border-left: 4px solid #ffc107; }

        .scraping-output {
            background: #1e1e1e;
            color: #d4d4d4;
            padding: 20px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            max-height: 400px;
            overflow-y: auto;
            white-space: pre-wrap;
            display: none;
        }

        .scraping-output.active { display: block; }

        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #667eea;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }

        .quick-actions {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }

        .quick-action-card {
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
            cursor: pointer;
            transition: all 0.3s;
        }

        .quick-action-card:hover {
            border-color: #667eea;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(102, 126, 234, 0.2);
        }

        .quick-action-card h4 {
            color: #667eea;
            margin-bottom: 10px;
        }

        .quick-action-card .cities {
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Automated Google Maps Scraper</h1>
            <div class="header-actions">
                <a href="index.php" class="btn-secondary">Dashboard</a>
                <a href="scraper.php" class="btn-secondary">Manual Entry</a>
            </div>
        </header>

        <!-- Setup Status -->
        <div class="setup-status <?php echo $setup['installed'] ? ($setup['playwright_installed'] ? 'success' : 'warning') : 'error'; ?>">
            <h3>Setup Status</h3>

            <?php if (!$setup['installed']): ?>
                <p><strong>Python is not installed!</strong></p>
                <p>Please install Python 3.8+ from <a href="https://www.python.org/downloads/" target="_blank">python.org</a></p>

            <?php elseif (!$setup['playwright_installed']): ?>
                <p><strong>Python detected:</strong> <?php echo $setup['python_version']; ?></p>
                <p><strong>Playwright not installed!</strong></p>
                <p>Run these commands in terminal:</p>
                <pre style="background: #fff; padding: 10px; border-radius: 4px; margin-top: 10px;">
cd <?php echo __DIR__; ?>

pip3 install -r requirements.txt
playwright install chromium
                </pre>

            <?php else: ?>
                <p><strong>✓ Python:</strong> <?php echo $setup['python_version']; ?></p>
                <p><strong>✓ Playwright:</strong> Installed</p>
                <p><strong>✓ Script:</strong> Ready</p>
                <p style="margin-top: 10px; color: #28a745;"><strong>All systems ready! You can start scraping.</strong></p>
            <?php endif; ?>
        </div>

        <?php if ($setup['installed'] && $setup['playwright_installed']): ?>
        <!-- Manual Scraping Form -->
        <div class="section">
            <h2>Custom Search</h2>
            <form id="scrapeForm">
                <div class="form-row">
                    <div class="form-group">
                        <label>Search Query *</label>
                        <input type="text" name="query" id="query" placeholder="e.g., immigration consultant, IELTS coaching" required>
                    </div>
                    <div class="form-group">
                        <label>Location *</label>
                        <input type="text" name="location" id="location" placeholder="e.g., Delhi, Mumbai" required>
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Max Results</label>
                        <input type="number" name="max_results" value="20" min="5" max="100">
                    </div>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" name="headless" value="true" checked>
                            Run in background (headless mode)
                        </label>
                    </div>
                </div>

                <button type="submit" class="btn-primary" id="scrapeBtn">
                    Start Scraping
                </button>
            </form>
        </div>

        <!-- Quick Actions -->
        <div class="section">
            <h2>Quick Start Templates</h2>
            <div class="quick-actions">
                <?php foreach ($searchConfigs as $config): ?>
                    <div class="quick-action-card" onclick="quickScrape('<?php echo $config['query']; ?>', <?php echo json_encode($config['cities']); ?>)">
                        <h4><?php echo ucwords($config['query']); ?></h4>
                        <p class="cities">Cities: <?php echo implode(', ', array_slice($config['cities'], 0, 4)); ?>
                            <?php if (count($config['cities']) > 4): ?>
                                + <?php echo count($config['cities']) - 4; ?> more
                            <?php endif; ?>
                        </p>
                        <p style="margin-top: 10px; color: #667eea; font-weight: 600;">Click to start</p>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>

        <!-- Output Console -->
        <div class="section">
            <h2>Scraping Output</h2>
            <div id="scrapingOutput" class="scraping-output"></div>
            <div id="idleMessage" style="text-align: center; color: #999; padding: 40px;">
                No active scraping session. Start a search above.
            </div>
        </div>
        <?php endif; ?>
    </div>

    <script>
        const setupReady = <?php echo json_encode($setup['installed'] && $setup['playwright_installed']); ?>;

        if (setupReady) {
            document.getElementById('scrapeForm').addEventListener('submit', async function(e) {
                e.preventDefault();

                const formData = new FormData(this);
                formData.append('action', 'scrape');

                const btn = document.getElementById('scrapeBtn');
                const output = document.getElementById('scrapingOutput');
                const idleMessage = document.getElementById('idleMessage');

                btn.disabled = true;
                btn.innerHTML = '<span class="loading"></span> Scraping in progress...';
                output.classList.add('active');
                idleMessage.style.display = 'none';
                output.textContent = 'Initializing scraper...\n';

                try {
                    const response = await fetch('auto_scrape.php', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.raw_output) {
                        output.textContent = result.raw_output;
                    }

                    if (result.success) {
                        output.textContent += '\n\n✓ SUCCESS!\n';
                        output.textContent += `Scraped: ${result.scraped} listings\n`;
                        output.textContent += `Saved: ${result.saved} new agents\n`;
                        output.textContent += `Duplicates: ${result.duplicates}\n`;

                        alert(`Success! Scraped ${result.scraped} listings, saved ${result.saved} new agents.`);
                    } else {
                        output.textContent += '\n\n✗ FAILED\n';
                        output.textContent += result.message || 'Unknown error';
                        alert('Scraping failed. Check output for details.');
                    }

                } catch (error) {
                    output.textContent += '\n\n✗ ERROR: ' + error.message;
                    alert('Error: ' + error.message);
                } finally {
                    btn.disabled = false;
                    btn.textContent = 'Start Scraping';
                }
            });
        }

        async function quickScrape(query, cities) {
            if (!confirm(`This will scrape "${query}" for ${cities.length} cities. Continue?`)) {
                return;
            }

            const output = document.getElementById('scrapingOutput');
            const idleMessage = document.getElementById('idleMessage');

            output.classList.add('active');
            idleMessage.style.display = 'none';
            output.textContent = `Starting batch scraping for: ${query}\nCities: ${cities.join(', ')}\n\n`;

            let totalScraped = 0;
            let totalSaved = 0;

            for (const city of cities) {
                output.textContent += `\n${'='.repeat(50)}\nScraping: ${query} - ${city}\n${'='.repeat(50)}\n`;

                const formData = new FormData();
                formData.append('action', 'scrape');
                formData.append('query', query);
                formData.append('location', city);
                formData.append('max_results', 20);
                formData.append('headless', 'true');

                try {
                    const response = await fetch('auto_scrape.php', {
                        method: 'POST',
                        body: formData
                    });

                    const result = await response.json();

                    if (result.raw_output) {
                        output.textContent += result.raw_output + '\n';
                    }

                    if (result.success) {
                        totalScraped += result.scraped;
                        totalSaved += result.saved;
                    }

                    // Delay between cities to avoid detection
                    await new Promise(resolve => setTimeout(resolve, 3000));

                } catch (error) {
                    output.textContent += `\n✗ Error for ${city}: ${error.message}\n`;
                }
            }

            output.textContent += `\n\n${'='.repeat(50)}\nBATCH COMPLETE\n${'='.repeat(50)}\n`;
            output.textContent += `Total scraped: ${totalScraped}\n`;
            output.textContent += `Total saved: ${totalSaved}\n`;

            alert(`Batch complete! Scraped ${totalScraped} listings across ${cities.length} cities.`);
        }
    </script>
</body>
</html>
