<?php
/**
 * Update existing database entries with state names extracted from addresses
 */

require_once 'config.php';

// State name patterns and abbreviations
$stateMappings = [
    'maharashtra' => 'Maharashtra', 'mh' => 'Maharashtra',
    'karnataka' => 'Karnataka', 'ka' => 'Karnataka',
    'tamil nadu' => 'Tamil Nadu', 'tamilnadu' => 'Tamil Nadu', 'tn' => 'Tamil Nadu',
    'telangana' => 'Telangana', 'tg' => 'Telangana',
    'andhra pradesh' => 'Andhra Pradesh', 'ap' => 'Andhra Pradesh',
    'gujarat' => 'Gujarat', 'gj' => 'Gujarat',
    'rajasthan' => 'Rajasthan', 'rj' => 'Rajasthan',
    'uttar pradesh' => 'Uttar Pradesh', 'up' => 'Uttar Pradesh',
    'madhya pradesh' => 'Madhya Pradesh', 'mp' => 'Madhya Pradesh',
    'punjab' => 'Punjab', 'pb' => 'Punjab',
    'haryana' => 'Haryana', 'hr' => 'Haryana',
    'west bengal' => 'West Bengal', 'wb' => 'West Bengal',
    'kerala' => 'Kerala', 'kl' => 'Kerala',
    'odisha' => 'Odisha', 'orissa' => 'Odisha', 'or' => 'Odisha',
    'jharkhand' => 'Jharkhand', 'jh' => 'Jharkhand',
    'assam' => 'Assam', 'as' => 'Assam',
    'bihar' => 'Bihar', 'br' => 'Bihar',
    'chhattisgarh' => 'Chhattisgarh', 'cg' => 'Chhattisgarh',
    'goa' => 'Goa', 'ga' => 'Goa',
    'himachal pradesh' => 'Himachal Pradesh', 'hp' => 'Himachal Pradesh',
    'jammu and kashmir' => 'Jammu and Kashmir', 'jk' => 'Jammu and Kashmir',
    'delhi' => 'Delhi', 'new delhi' => 'Delhi', 'dl' => 'Delhi',
    'chandigarh' => 'Chandigarh', 'ch' => 'Chandigarh',
    'puducherry' => 'Puducherry', 'pondicherry' => 'Puducherry', 'py' => 'Puducherry',
    'uttarakhand' => 'Uttarakhand', 'uk' => 'Uttarakhand',
];

function extractStateFromAddress($address, $stateMappings) {
    if (empty($address)) {
        return null;
    }

    $addressLower = strtolower($address);

    foreach ($stateMappings as $key => $stateName) {
        if (strpos($addressLower, $key) !== false) {
            return $stateName;
        }
    }

    return null;
}

try {
    $conn = new PDO("mysql:host=" . DB_HOST . ";dbname=" . DB_NAME, DB_USER, DB_PASS);
    $conn->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);

    // Get all agents with empty state
    $stmt = $conn->query("SELECT id, address FROM agents WHERE state IS NULL OR state = ''");
    $agents = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo "<!DOCTYPE html>
<html>
<head>
    <meta charset='UTF-8'>
    <title>Update States</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }
        .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        h1 { color: #333; }
        .stats { background: #e3f2fd; padding: 15px; border-radius: 5px; margin: 20px 0; }
        .progress { margin: 20px 0; }
        .result { padding: 10px; margin: 5px 0; border-left: 4px solid #4caf50; background: #f1f8e9; }
        .no-state { border-left-color: #ff9800; background: #fff3e0; }
        pre { background: #263238; color: #aed581; padding: 15px; border-radius: 5px; overflow-x: auto; }
    </style>
</head>
<body>
    <div class='container'>
        <h1>🔄 Updating State Names from Addresses</h1>
        <div class='stats'>
            <strong>Total agents with missing state:</strong> " . count($agents) . "
        </div>
        <div class='progress'>";

    $updated = 0;
    $notFound = 0;

    foreach ($agents as $agent) {
        $state = extractStateFromAddress($agent['address'], $stateMappings);

        if ($state) {
            $updateStmt = $conn->prepare("UPDATE agents SET state = :state WHERE id = :id");
            $updateStmt->execute([':state' => $state, ':id' => $agent['id']]);
            $updated++;
            echo "<div class='result'>✓ Agent ID {$agent['id']} → <strong>{$state}</strong></div>";
        } else {
            $notFound++;
            echo "<div class='result no-state'>⚠ Agent ID {$agent['id']} → Could not extract state from address</div>";
        }

        // Flush output for real-time updates
        if ($updated % 10 == 0) {
            flush();
            ob_flush();
        }
    }

    echo "</div>
        <div class='stats'>
            <h3>✅ Update Complete!</h3>
            <p><strong>Updated:</strong> {$updated} agents</p>
            <p><strong>Not found:</strong> {$notFound} agents (no state pattern in address)</p>
        </div>

        <h3>Verify Results:</h3>
        <pre>";

    // Show state distribution
    $stmt = $conn->query("SELECT state, COUNT(*) as count FROM agents WHERE state != '' GROUP BY state ORDER BY count DESC");
    $distribution = $stmt->fetchAll(PDO::FETCH_ASSOC);

    echo "State Distribution:\n\n";
    foreach ($distribution as $row) {
        echo str_pad($row['state'], 30) . " : " . $row['count'] . " agents\n";
    }

    echo "</pre>
        <p><a href='index.php' style='display: inline-block; padding: 10px 20px; background: #667eea; color: white; text-decoration: none; border-radius: 5px;'>← Back to Dashboard</a></p>
    </div>
</body>
</html>";

} catch (PDOException $e) {
    echo "Error: " . $e->getMessage();
}
?>
