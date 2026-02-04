<?php
// Database Setup Script
// Run this file once to create the database and tables

// Connect without database first to create it
$conn = new mysqli('localhost', 'root', '');

if ($conn->connect_error) {
    die("Connection failed: " . $conn->connect_error);
}

// Create database if not exists
$sql = "CREATE DATABASE IF NOT EXISTS immigration_agents_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci";
if ($conn->query($sql) === TRUE) {
    echo "Database created successfully or already exists.<br>";
} else {
    die("Error creating database: " . $conn->error);
}

// Select the database
$conn->select_db('immigration_agents_db');

// Create agents table
$createTableSQL = "CREATE TABLE IF NOT EXISTS agents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_name VARCHAR(255) NOT NULL,
    address TEXT,
    phone VARCHAR(50),
    city VARCHAR(100),
    state VARCHAR(100),
    pincode VARCHAR(10),
    website VARCHAR(255),
    email VARCHAR(255),
    services VARCHAR(255) COMMENT 'Immigration, IELTS, PTE, etc.',
    google_place_id VARCHAR(255) UNIQUE COMMENT 'Unique ID to prevent duplicates',
    source_location VARCHAR(255) COMMENT 'Search term used (city/PIN)',
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    scraped_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('active', 'inactive') DEFAULT 'active',
    notes TEXT,
    INDEX idx_city (city),
    INDEX idx_state (state),
    INDEX idx_pincode (pincode),
    INDEX idx_services (services),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

if ($conn->query($createTableSQL) === TRUE) {
    echo "Table 'agents' created successfully or already exists.<br>";
} else {
    die("Error creating table: " . $conn->error);
}

// Create search history table to track what we've already searched
$createSearchHistorySQL = "CREATE TABLE IF NOT EXISTS search_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    search_query VARCHAR(255) NOT NULL,
    search_type ENUM('city', 'pincode') NOT NULL,
    location VARCHAR(255) NOT NULL,
    results_found INT DEFAULT 0,
    search_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_search (search_query, location)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci";

if ($conn->query($createSearchHistorySQL) === TRUE) {
    echo "Table 'search_history' created successfully or already exists.<br>";
} else {
    die("Error creating search_history table: " . $conn->error);
}

echo "<br><strong>Database setup completed successfully!</strong><br>";
echo "<a href='index.php'>Go to Dashboard</a>";

$conn->close();
?>
