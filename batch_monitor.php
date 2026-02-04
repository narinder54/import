<?php
require_once 'config.php';

// Load state
$stateFile = __DIR__ . '/scraper_state.json';
$state = json_decode(file_get_contents($stateFile), true);

// Load config
$configFile = __DIR__ . '/batch_config.json';
$config = json_decode(file_get_contents($configFile), true);

// Load cities by state
$citiesFile = __DIR__ . '/cities_by_state.json';
$citiesByState = json_decode(file_get_contents($citiesFile), true);

// Calculate progress
$totalQueries = count($config['queries']);
$statesToScrape = $config['states_to_scrape'] ?? array_keys($citiesByState);
$totalCities = 0;
foreach ($statesToScrape as $stateName) {
    $totalCities += count($citiesByState[$stateName] ?? []);
}
$totalCombinations = $totalQueries * $totalCities;

$currentQueryIdx = $state['last_query_index'];
$currentStateIdx = $state['last_state_index'] ?? 0;
$currentCityIdx = $state['last_city_index'];
$currentStateName = $state['current_state'] ?? ($statesToScrape[$currentStateIdx] ?? 'N/A');
$currentCityName = $state['current_city'] ?? 'N/A';

// Calculate completed combinations (approximate)
$completed = 0;
for ($q = 0; $q < $currentQueryIdx; $q++) {
    $completed += $totalCities;
}
for ($s = 0; $s < $currentStateIdx; $s++) {
    $completed += count($citiesByState[$statesToScrape[$s]] ?? []);
}
$completed += $currentCityIdx;
$progressPercent = $totalCombinations > 0 ? ($completed / $totalCombinations) * 100 : 0;

// Get database stats
try {
    $conn = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS);
    $stmt = $conn->query("SELECT COUNT(*) as total FROM agents");
    $totalAgents = $stmt->fetch()['total'];

    $stmt = $conn->query("SELECT COUNT(*) as total FROM agents WHERE created_at >= DATE_SUB(NOW(), INTERVAL 1 HOUR)");
    $recentAgents = $stmt->fetch()['total'];
} catch (PDOException $e) {
    $totalAgents = 'N/A';
    $recentAgents = 'N/A';
}

// Status badge
$statusColors = [
    'ready' => '#gray',
    'running' => '#28a745',
    'paused' => '#ffc107',
    'completed' => '#17a2b8',
    'stopped_captcha' => '#dc3545',
    'error' => '#dc3545'
];
$statusColor = $statusColors[$state['status']] ?? '#6c757d';

// Auto-refresh if running
$autoRefresh = ($state['status'] === 'running') ? '<meta http-equiv="refresh" content="10">' : '';
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Batch Scraper Monitor</title>
    <link rel="stylesheet" href="style.css">
    <?php echo $autoRefresh; ?>
    <style>
        .monitor-header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 12px;
            margin-bottom: 30px;
        }

        .status-badge {
            display: inline-block;
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            text-transform: uppercase;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            text-align: center;
        }

        .stat-value {
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
            margin: 10px 0;
        }

        .stat-label {
            color: #666;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }

        .progress-bar {
            width: 100%;
            height: 30px;
            background: #e0e0e0;
            border-radius: 15px;
            overflow: hidden;
            margin: 20px 0;
        }

        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
            transition: width 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: 600;
        }

        .current-info {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
        }

        .action-buttons {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }

        .btn-control {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }

        .btn-reset {
            background: #dc3545;
            color: white;
        }

        .btn-reset:hover {
            background: #c82333;
        }

        .alert {
            padding: 15px;
            border-radius: 8px;
            margin: 20px 0;
        }

        .alert-warning {
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            color: #856404;
        }

        .alert-danger {
            background: #f8d7da;
            border-left: 4px solid #dc3545;
            color: #721c24;
        }

        .alert-success {
            background: #d4edda;
            border-left: 4px solid #28a745;
            color: #155724;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Batch Scraper Monitor</h1>
            <div class="header-actions">
                <a href="index.php" class="btn-secondary">Dashboard</a>
                <a href="auto_scrape.php" class="btn-secondary">Manual Scraper</a>
            </div>
        </header>

        <div class="monitor-header">
            <h2>Automated Batch Scraper Status</h2>
            <span class="status-badge" style="background: <?php echo $statusColor; ?>">
                <?php echo strtoupper($state['status']); ?>
            </span>
            <?php if ($state['status'] === 'running'): ?>
                <p style="margin-top: 15px; opacity: 0.9;">
                    🔄 Auto-refreshing every 10 seconds...
                </p>
            <?php endif; ?>
        </div>

        <!-- Progress Bar -->
        <div class="section">
            <h3>Overall Progress</h3>
            <div class="progress-bar">
                <div class="progress-fill" style="width: <?php echo round($progressPercent, 2); ?>%">
                    <?php echo round($progressPercent, 1); ?>%
                </div>
            </div>
            <p style="text-align: center; color: #666;">
                Completed <?php echo $completed; ?> of <?php echo $totalCombinations; ?> combinations
            </p>
        </div>

        <!-- Stats Grid -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Scraped</div>
                <div class="stat-value"><?php echo number_format($state['total_scraped']); ?></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Total Saved</div>
                <div class="stat-value"><?php echo number_format($state['total_saved']); ?></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">In Database</div>
                <div class="stat-value"><?php echo is_numeric($totalAgents) ? number_format($totalAgents) : $totalAgents; ?></div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Last Hour</div>
                <div class="stat-value"><?php echo is_numeric($recentAgents) ? number_format($recentAgents) : $recentAgents; ?></div>
            </div>
        </div>

        <!-- Current Status -->
        <div class="section">
            <h3>Current Status</h3>
            <div class="current-info">
                <p><strong>Current Query:</strong> <?php echo $config['queries'][$currentQueryIdx] ?? 'N/A'; ?></p>
                <p><strong>Current State:</strong> <?php echo $currentStateName; ?> (<?php echo count($citiesByState[$currentStateName] ?? []); ?> cities)</p>
                <p><strong>Current City:</strong> <?php echo $currentCityName; ?></p>
                <p><strong>Query Progress:</strong> <?php echo $currentQueryIdx + 1; ?> of <?php echo $totalQueries; ?></p>
                <p><strong>State Progress:</strong> <?php echo $currentStateIdx + 1; ?> of <?php echo count($statesToScrape); ?></p>
                <p><strong>Total Cities:</strong> <?php echo $totalCities; ?> cities across <?php echo count($statesToScrape); ?> states</p>
                <?php if ($state['last_run_timestamp']): ?>
                    <p><strong>Last Run:</strong> <?php echo date('Y-m-d H:i:s', strtotime($state['last_run_timestamp'])); ?></p>
                <?php endif; ?>
            </div>
        </div>

        <!-- Alerts -->
        <?php if ($state['captcha_detected']): ?>
            <div class="alert alert-danger">
                <strong>⚠ CAPTCHA Detected!</strong><br>
                The scraper detected bot protection and stopped automatically. Please wait a few hours before resuming.
            </div>
        <?php endif; ?>

        <?php if ($state['status'] === 'completed'): ?>
            <div class="alert alert-success">
                <strong>🎉 Scraping Completed!</strong><br>
                All cities have been scraped successfully. Total saved: <?php echo number_format($state['total_saved']); ?> agents.
            </div>
        <?php endif; ?>

        <?php if ($state['status'] === 'paused'): ?>
            <div class="alert alert-warning">
                <strong>⏸ Scraper Paused</strong><br>
                Run the scraper again to resume from where it stopped.
            </div>
        <?php endif; ?>

        <!-- Configuration -->
        <div class="section">
            <h3>Configuration</h3>
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px;">
                <p><strong>Queries:</strong> <?php echo implode(', ', $config['queries']); ?></p>
                <p><strong>Delay Range:</strong> <?php echo $config['delays']['min_seconds']; ?>-<?php echo $config['delays']['max_seconds']; ?> seconds</p>
                <p><strong>Scroll Range:</strong> <?php echo $config['scrolling']['min_scrolls']; ?>-<?php echo $config['scrolling']['max_scrolls']; ?> times</p>
                <p><strong>Mode:</strong> <?php echo $config['headless'] ? 'Headless' : 'Visible Browser'; ?></p>
                <p><strong>Notifications:</strong> <?php echo $config['send_notifications'] ? '✓ Enabled' : '✗ Disabled'; ?></p>
            </div>
        </div>

        <!-- Actions -->
        <div class="section">
            <h3>Actions</h3>
            <div class="action-buttons">
                <button onclick="if(confirm('Reset progress and start from beginning?')) location.href='?action=reset'" class="btn-control btn-reset">
                    Reset Progress
                </button>
                <a href="BATCH_SCRAPER_README.md" class="btn-control" style="background: #17a2b8; color: white; text-decoration: none;">
                    View Documentation
                </a>
            </div>
        </div>

        <!-- Instructions -->
        <div class="section">
            <h3>How to Run</h3>
            <pre style="background: #1e1e1e; color: #d4d4d4; padding: 20px; border-radius: 8px; overflow-x: auto;">
# Start the batch scraper
cd /Applications/XAMPP/xamppfiles/htdocs/import
./start_batch_scraper.sh

# Pause: Press Ctrl+C (state will be saved)
# Resume: Run the command again

# Run in background
nohup ./start_batch_scraper.sh > scraper.log 2>&1 &

# Check log
tail -f scraper.log
            </pre>
        </div>
    </div>

    <?php
    // Handle reset action
    if (isset($_GET['action']) && $_GET['action'] === 'reset') {
        $resetState = [
            'last_query_index' => 0,
            'last_state_index' => 0,
            'last_city_index' => 0,
            'current_state' => null,
            'current_city' => null,
            'completed_combinations' => [],
            'total_scraped' => 0,
            'total_saved' => 0,
            'last_run_timestamp' => null,
            'status' => 'ready',
            'captcha_detected' => false,
            'error_count' => 0
        ];
        file_put_contents($stateFile, json_encode($resetState, JSON_PRETTY_PRINT));
        echo '<script>alert("Progress reset successfully!"); location.href="batch_monitor.php";</script>';
    }
    ?>
</body>
</html>
