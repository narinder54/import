#!/usr/bin/env php
<?php
/**
 * Database Migration: Add GMB Link Column
 * Run this script to add the gmb_link column to the agents table
 */

$host = 'localhost';
$user = 'root';
$pass = '';
$db = 'immigration_agents_db';

try {
    // Connect to database
    $conn = new mysqli($host, $user, $pass, $db);

    if ($conn->connect_error) {
        die("❌ Connection failed: " . $conn->connect_error . "\n");
    }

    echo "✓ Connected to database\n\n";

    // Check if column already exists
    $result = $conn->query("SHOW COLUMNS FROM agents LIKE 'gmb_link'");

    if ($result->num_rows > 0) {
        echo "⚠️  Column 'gmb_link' already exists in agents table\n";
        echo "   No migration needed.\n";
    } else {
        echo "📝 Adding 'gmb_link' column to agents table...\n";

        $sql = "ALTER TABLE agents ADD COLUMN gmb_link VARCHAR(500) DEFAULT '' AFTER longitude";

        if ($conn->query($sql) === TRUE) {
            echo "✅ SUCCESS: gmb_link column added successfully!\n\n";

            // Show table structure
            echo "📋 Updated table structure:\n";
            echo str_repeat("-", 60) . "\n";

            $result = $conn->query("DESCRIBE agents");
            while ($row = $result->fetch_assoc()) {
                printf("%-25s %-15s %s\n",
                    $row['Field'],
                    $row['Type'],
                    $row['Null'] == 'NO' ? 'NOT NULL' : 'NULL'
                );
            }

            echo str_repeat("-", 60) . "\n";
        } else {
            echo "❌ ERROR: " . $conn->error . "\n";
        }
    }

    $conn->close();

} catch (Exception $e) {
    die("❌ Error: " . $e->getMessage() . "\n");
}

echo "\n✓ Migration complete!\n";
echo "  You can now run the scraper with GMB link support.\n";
?>
