<?php
require_once 'config.php';
require_once 'scraper.php';

$scraper = new GoogleBusinessScraper();
$results = [];
$searched = false;

if ($_SERVER['REQUEST_METHOD'] === 'GET' && (isset($_GET['city']) || isset($_GET['state']) || isset($_GET['pincode']) || isset($_GET['services']))) {
    $filters = [
        'city' => $_GET['city'] ?? '',
        'state' => $_GET['state'] ?? '',
        'pincode' => $_GET['pincode'] ?? '',
        'services' => $_GET['services'] ?? ''
    ];

    $results = $scraper->searchAgents($filters);
    $searched = true;
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Search Agents</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Search Immigration Agents</h1>
            <div class="header-actions">
                <a href="index.php" class="btn-secondary">Dashboard</a>
                <a href="scraper.php" class="btn-secondary">Add Agent</a>
            </div>
        </header>

        <div class="section">
            <form method="GET" action="search.php" class="search-form">
                <div class="form-row">
                    <div class="form-group">
                        <label>City</label>
                        <input type="text" name="city" placeholder="e.g., Delhi, Mumbai" value="<?php echo htmlspecialchars($_GET['city'] ?? ''); ?>">
                    </div>
                    <div class="form-group">
                        <label>State</label>
                        <input type="text" name="state" placeholder="e.g., Maharashtra" value="<?php echo htmlspecialchars($_GET['state'] ?? ''); ?>">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>PIN Code</label>
                        <input type="text" name="pincode" placeholder="e.g., 110001" value="<?php echo htmlspecialchars($_GET['pincode'] ?? ''); ?>">
                    </div>
                    <div class="form-group">
                        <label>Services</label>
                        <select name="services">
                            <option value="">All Services</option>
                            <option value="Immigration" <?php echo (isset($_GET['services']) && $_GET['services'] === 'Immigration') ? 'selected' : ''; ?>>Immigration</option>
                            <option value="IELTS" <?php echo (isset($_GET['services']) && $_GET['services'] === 'IELTS') ? 'selected' : ''; ?>>IELTS</option>
                            <option value="PTE" <?php echo (isset($_GET['services']) && $_GET['services'] === 'PTE') ? 'selected' : ''; ?>>PTE</option>
                        </select>
                    </div>
                </div>

                <div class="form-actions">
                    <button type="submit" class="btn-primary">Search</button>
                    <a href="search.php" class="btn-secondary">Clear</a>
                </div>
            </form>
        </div>

        <?php if ($searched): ?>
            <div class="section">
                <div class="results-header">
                    <h2>Search Results</h2>
                    <div>
                        <span class="result-count"><?php echo count($results); ?> results found</span>
                        <?php if (!empty($results)): ?>
                            <a href="export.php?<?php echo http_build_query($_GET); ?>" class="btn-primary">Export These Results</a>
                        <?php endif; ?>
                    </div>
                </div>

                <?php if (empty($results)): ?>
                    <div class="notice">
                        <p>No agents found matching your search criteria.</p>
                        <p>Try adjusting your filters or <a href="scraper.php">add new agents</a>.</p>
                    </div>
                <?php else: ?>
                    <div class="table-responsive">
                        <table class="agents-table">
                            <thead>
                                <tr>
                                    <th>Business Name</th>
                                    <th>Address</th>
                                    <th>Phone</th>
                                    <th>City</th>
                                    <th>State</th>
                                    <th>PIN</th>
                                    <th>Services</th>
                                    <th>Contact</th>
                                </tr>
                            </thead>
                            <tbody>
                                <?php foreach ($results as $agent): ?>
                                    <tr>
                                        <td><strong><?php echo htmlspecialchars($agent['business_name']); ?></strong></td>
                                        <td><?php echo htmlspecialchars($agent['address'] ?: '-'); ?></td>
                                        <td><?php echo htmlspecialchars($agent['phone'] ?: '-'); ?></td>
                                        <td><?php echo htmlspecialchars($agent['city'] ?: '-'); ?></td>
                                        <td><?php echo htmlspecialchars($agent['state'] ?: '-'); ?></td>
                                        <td><?php echo htmlspecialchars($agent['pincode'] ?: '-'); ?></td>
                                        <td><span class="badge"><?php echo htmlspecialchars($agent['services'] ?: '-'); ?></span></td>
                                        <td>
                                            <?php if ($agent['website']): ?>
                                                <a href="<?php echo htmlspecialchars($agent['website']); ?>" target="_blank">Website</a>
                                            <?php endif; ?>
                                            <?php if ($agent['email']): ?>
                                                <br><a href="mailto:<?php echo htmlspecialchars($agent['email']); ?>">Email</a>
                                            <?php endif; ?>
                                            <?php if (!$agent['website'] && !$agent['email']): ?>
                                                -
                                            <?php endif; ?>
                                        </td>
                                    </tr>
                                <?php endforeach; ?>
                            </tbody>
                        </table>
                    </div>
                <?php endif; ?>
            </div>
        <?php endif; ?>
    </div>
</body>
</html>
