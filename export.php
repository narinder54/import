<?php
require_once 'config.php';
require_once 'scraper.php';

$scraper = new GoogleBusinessScraper();

// Check if we're exporting filtered results or all results
$filters = [];
if (isset($_GET['city']) || isset($_GET['state']) || isset($_GET['pincode']) || isset($_GET['services'])) {
    $filters = [
        'city' => $_GET['city'] ?? '',
        'state' => $_GET['state'] ?? '',
        'pincode' => $_GET['pincode'] ?? '',
        'services' => $_GET['services'] ?? ''
    ];
    $agents = $scraper->searchAgents($filters);
    $filename = 'filtered_agents_' . date('Y-m-d_His') . '.csv';
} else {
    $agents = $scraper->getAllAgents(10000, 0); // Export up to 10,000 records
    $filename = 'all_agents_' . date('Y-m-d_His') . '.csv';
}

// If download parameter is set, export the CSV
if (isset($_GET['download']) && $_GET['download'] === 'true') {
    // Set headers for CSV download
    header('Content-Type: text/csv; charset=utf-8');
    header('Content-Disposition: attachment; filename="' . $filename . '"');
    header('Pragma: no-cache');
    header('Expires: 0');

    // Open output stream
    $output = fopen('php://output', 'w');

    // Add BOM for Excel UTF-8 support
    fprintf($output, chr(0xEF).chr(0xBB).chr(0xBF));

    // CSV Headers
    fputcsv($output, [
        'Business Name',
        'Address',
        'Phone',
        'City',
        'State',
        'PIN Code',
        'Website',
        'Email',
        'Services',
        'Source Location',
        'Date Added'
    ]);

    // Add data rows
    foreach ($agents as $agent) {
        fputcsv($output, [
            $agent['business_name'],
            $agent['address'],
            $agent['phone'],
            $agent['city'],
            $agent['state'],
            $agent['pincode'],
            $agent['website'],
            $agent['email'],
            $agent['services'],
            $agent['source_location'],
            date('Y-m-d H:i:s', strtotime($agent['scraped_date']))
        ]);
    }

    fclose($output);
    exit;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Export to CSV</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Export Agents to CSV</h1>
            <div class="header-actions">
                <a href="index.php" class="btn-secondary">Dashboard</a>
                <a href="search.php" class="btn-secondary">Search</a>
            </div>
        </header>

        <div class="section">
            <div class="export-preview">
                <h2>Export Preview</h2>

                <?php if (!empty($filters) && array_filter($filters)): ?>
                    <div class="notice">
                        <h3>Filtered Export</h3>
                        <p>You are exporting filtered results based on:</p>
                        <ul>
                            <?php if (!empty($filters['city'])): ?>
                                <li><strong>City:</strong> <?php echo htmlspecialchars($filters['city']); ?></li>
                            <?php endif; ?>
                            <?php if (!empty($filters['state'])): ?>
                                <li><strong>State:</strong> <?php echo htmlspecialchars($filters['state']); ?></li>
                            <?php endif; ?>
                            <?php if (!empty($filters['pincode'])): ?>
                                <li><strong>PIN Code:</strong> <?php echo htmlspecialchars($filters['pincode']); ?></li>
                            <?php endif; ?>
                            <?php if (!empty($filters['services'])): ?>
                                <li><strong>Services:</strong> <?php echo htmlspecialchars($filters['services']); ?></li>
                            <?php endif; ?>
                        </ul>
                    </div>
                <?php endif; ?>

                <div class="stats-grid">
                    <div class="stat-card">
                        <h3>Records to Export</h3>
                        <p class="stat-number"><?php echo number_format(count($agents)); ?></p>
                    </div>
                    <div class="stat-card">
                        <h3>File Format</h3>
                        <p class="stat-number">CSV</p>
                    </div>
                    <div class="stat-card">
                        <h3>File Name</h3>
                        <p style="font-size: 14px; margin-top: 10px;"><?php echo $filename; ?></p>
                    </div>
                </div>

                <?php if (empty($agents)): ?>
                    <div class="notice">
                        <p>No agents found to export.</p>
                        <a href="index.php" class="btn-primary">Go to Dashboard</a>
                    </div>
                <?php else: ?>
                    <div class="export-info">
                        <h3>CSV will include the following fields:</h3>
                        <ul>
                            <li>Business Name</li>
                            <li>Address</li>
                            <li>Phone</li>
                            <li>City</li>
                            <li>State</li>
                            <li>PIN Code</li>
                            <li>Website</li>
                            <li>Email</li>
                            <li>Services</li>
                            <li>Source Location</li>
                            <li>Date Added</li>
                        </ul>
                    </div>

                    <div class="export-actions">
                        <a href="export.php?download=true<?php echo !empty($filters) ? '&' . http_build_query($filters) : ''; ?>" class="btn-primary btn-large">
                            Download CSV File
                        </a>
                        <a href="search.php" class="btn-secondary">Change Filters</a>
                    </div>

                    <div class="section">
                        <h3>Preview (First 10 Records)</h3>
                        <div class="table-responsive">
                            <table class="agents-table">
                                <thead>
                                    <tr>
                                        <th>Business Name</th>
                                        <th>Phone</th>
                                        <th>City</th>
                                        <th>State</th>
                                        <th>Services</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <?php foreach (array_slice($agents, 0, 10) as $agent): ?>
                                        <tr>
                                            <td><?php echo htmlspecialchars($agent['business_name']); ?></td>
                                            <td><?php echo htmlspecialchars($agent['phone'] ?: '-'); ?></td>
                                            <td><?php echo htmlspecialchars($agent['city'] ?: '-'); ?></td>
                                            <td><?php echo htmlspecialchars($agent['state'] ?: '-'); ?></td>
                                            <td><?php echo htmlspecialchars($agent['services'] ?: '-'); ?></td>
                                        </tr>
                                    <?php endforeach; ?>
                                </tbody>
                            </table>
                        </div>
                        <?php if (count($agents) > 10): ?>
                            <p class="preview-note">Showing 10 of <?php echo count($agents); ?> records. Download CSV to see all.</p>
                        <?php endif; ?>
                    </div>
                <?php endif; ?>
            </div>
        </div>
    </div>
</body>
</html>
