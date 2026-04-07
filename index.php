<?php
require_once 'config.php';
require_once 'scraper.php';

$scraper = new GoogleBusinessScraper();
$stats = $scraper->getStats();

// Pagination
$page = isset($_GET['page']) ? (int)$_GET['page'] : 1;
$perPage = 50;
$offset = ($page - 1) * $perPage;

$agents = $scraper->getAllAgents($perPage, $offset);
$totalAgents = $stats['total'];
$totalPages = ceil($totalAgents / $perPage);
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immigration Agents Dashboard</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Immigration Agents Database</h1>
            <div class="header-actions">
                <a href="scraper.php" class="btn-secondary">Add New Agent</a>
                <a href="auto_scrape.php" class="btn-secondary">Auto Scraper</a>
                <a href="batch_monitor.php" class="btn-secondary">Batch Monitor</a>
                <a href="search.php" class="btn-secondary">Search & Filter</a>
                <a href="export.php" class="btn-primary">Export to CSV</a>
            </div>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>Total Agents</h3>
                <p class="stat-number"><?php echo number_format($totalAgents); ?></p>
            </div>
            <div class="stat-card">
                <h3>States Covered</h3>
                <p class="stat-number"><?php echo count($stats['by_state']); ?></p>
            </div>
            <div class="stat-card">
                <h3>Cities Covered</h3>
                <p class="stat-number"><?php echo count($stats['by_city']); ?></p>
            </div>
            <div class="stat-card">
                <h3>Service Types</h3>
                <p class="stat-number"><?php echo count($stats['by_services']); ?></p>
            </div>
        </div>

        <div class="section">
            <h2>Agents by State</h2>
            <div class="state-grid">
                <?php foreach ($stats['by_state'] as $state): ?>
                    <div class="state-card">
                        <strong><?php echo htmlspecialchars($state['state'] ?: 'Unknown'); ?></strong>
                        <span><?php echo number_format($state['count']); ?> agents</span>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>

        <div class="section">
            <h2>Top Cities</h2>
            <div class="city-grid">
                <?php foreach (array_slice($stats['by_city'], 0, 10) as $city): ?>
                    <div class="city-card">
                        <strong><?php echo htmlspecialchars($city['city'] ?: 'Unknown'); ?></strong>
                        <span><?php echo $city['count']; ?> agents</span>
                    </div>
                <?php endforeach; ?>
            </div>
        </div>

        <div class="section">
            <h2>Recent Agents (Page <?php echo $page; ?> of <?php echo $totalPages; ?>)</h2>

            <?php if (empty($agents)): ?>
                <div class="notice">
                    <p>No agents found in the database.</p>
                    <a href="scraper.php" class="btn-primary">Add Your First Agent</a>
                </div>
            <?php else: ?>
                <div class="table-responsive">
                    <table class="agents-table">
                        <thead>
                            <tr>
                                <th>Business Name</th>
                                <th>Phone</th>
                                <th>City</th>
                                <th>State</th>
                                <th>PIN</th>
                                <th>Services</th>
                                <th>Website</th>
                                <th>Added</th>
                            </tr>
                        </thead>
                        <tbody>
                            <?php foreach ($agents as $agent): ?>
                                <tr>
                                    <td><strong><?php echo htmlspecialchars($agent['business_name']); ?></strong></td>
                                    <td><?php echo htmlspecialchars($agent['phone'] ?: '-'); ?></td>
                                    <td><?php echo htmlspecialchars($agent['city'] ?: '-'); ?></td>
                                    <td><?php echo htmlspecialchars($agent['state'] ?: '-'); ?></td>
                                    <td><?php echo htmlspecialchars($agent['pincode'] ?: '-'); ?></td>
                                    <td><span class="badge"><?php echo htmlspecialchars($agent['services'] ?: '-'); ?></span></td>
                                    <td>
                                        <?php if ($agent['website']): ?>
                                            <a href="<?php echo htmlspecialchars($agent['website']); ?>" target="_blank">Visit</a>
                                        <?php else: ?>
                                            -
                                        <?php endif; ?>
                                    </td>
                                    <td><?php echo date('d M Y', strtotime($agent['scraped_date'])); ?></td>
                                </tr>
                            <?php endforeach; ?>
                        </tbody>
                    </table>
                </div>

                <?php if ($totalPages > 1): ?>
                    <div class="pagination">
                        <?php if ($page > 1): ?>
                            <a href="?page=<?php echo $page - 1; ?>" class="btn-secondary">Previous</a>
                        <?php endif; ?>

                        <span class="page-info">Page <?php echo $page; ?> of <?php echo $totalPages; ?></span>

                        <?php if ($page < $totalPages): ?>
                            <a href="?page=<?php echo $page + 1; ?>" class="btn-secondary">Next</a>
                        <?php endif; ?>
                    </div>
                <?php endif; ?>
            <?php endif; ?>
        </div>
    </div>
</body>
</html>
