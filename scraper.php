<?php
require_once 'config.php';

// Web Scraper for Google My Business Listings
// This script scrapes immigration agents, IELTS, and PTE coaching centers

class GoogleBusinessScraper {
    private $conn;
    private $userAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36';

    public function __construct() {
        $this->conn = getDBConnection();
    }

    // Check if entry already exists using phone or business name + city
    private function isDuplicate($phone, $businessName, $city) {
        // Check by phone (most reliable)
        if (!empty($phone)) {
            $stmt = $this->conn->prepare("SELECT id FROM agents WHERE phone = ?");
            $stmt->bind_param("s", $phone);
            $stmt->execute();
            $result = $stmt->get_result();
            if ($result->num_rows > 0) {
                return true;
            }
        }

        // Check by business name + city combination
        if (!empty($businessName) && !empty($city)) {
            $stmt = $this->conn->prepare("SELECT id FROM agents WHERE business_name = ? AND city = ?");
            $stmt->bind_param("ss", $businessName, $city);
            $stmt->execute();
            $result = $stmt->get_result();
            if ($result->num_rows > 0) {
                return true;
            }
        }

        return false;
    }

    // Insert agent data with duplicate check
    public function insertAgent($data) {
        // Check for duplicates first
        if ($this->isDuplicate($data['phone'], $data['business_name'], $data['city'])) {
            return ['success' => false, 'message' => 'Duplicate entry - already exists'];
        }

        $stmt = $this->conn->prepare("
            INSERT INTO agents
            (business_name, address, phone, city, state, pincode, website, email, services, google_place_id, source_location, latitude, longitude)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ");

        $stmt->bind_param(
            "sssssssssssdd",
            $data['business_name'],
            $data['address'],
            $data['phone'],
            $data['city'],
            $data['state'],
            $data['pincode'],
            $data['website'],
            $data['email'],
            $data['services'],
            $data['google_place_id'],
            $data['source_location'],
            $data['latitude'],
            $data['longitude']
        );

        if ($stmt->execute()) {
            return ['success' => true, 'message' => 'Agent added successfully', 'id' => $stmt->insert_id];
        } else {
            return ['success' => false, 'message' => 'Error: ' . $stmt->error];
        }
    }

    // Scrape Google search results (basic implementation)
    public function scrapeGoogleSearch($query, $location) {
        // Note: This is a basic implementation. Google actively blocks scrapers.
        // Consider using: Selenium, Puppeteer, or paid services like SerpAPI

        $searchQuery = urlencode($query . ' ' . $location . ' India');
        $url = "https://www.google.com/search?q=" . $searchQuery;

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $url);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, 1);
        curl_setopt($ch, CURLOPT_USERAGENT, $this->userAgent);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);

        $html = curl_exec($ch);
        $httpCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);

        if ($httpCode != 200) {
            return ['success' => false, 'message' => 'Failed to fetch results. HTTP Code: ' . $httpCode];
        }

        // Parse HTML (basic parsing - needs enhancement)
        // This is a placeholder - Google's HTML structure is complex and changes frequently

        return ['success' => true, 'message' => 'Scraping completed', 'html' => $html];
    }

    // Record search history
    public function recordSearch($query, $type, $location, $resultsFound) {
        $stmt = $this->conn->prepare("
            INSERT INTO search_history (search_query, search_type, location, results_found)
            VALUES (?, ?, ?, ?)
            ON DUPLICATE KEY UPDATE results_found = ?, search_date = CURRENT_TIMESTAMP
        ");

        $stmt->bind_param("sssii", $query, $type, $location, $resultsFound, $resultsFound);
        $stmt->execute();
    }

    // Get all agents
    public function getAllAgents($limit = 100, $offset = 0) {
        $stmt = $this->conn->prepare("
            SELECT * FROM agents
            WHERE status = 'active'
            ORDER BY scraped_date DESC
            LIMIT ? OFFSET ?
        ");
        $stmt->bind_param("ii", $limit, $offset);
        $stmt->execute();
        return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    }

    // Search agents
    public function searchAgents($filters) {
        $sql = "SELECT * FROM agents WHERE status = 'active'";
        $params = [];
        $types = "";

        if (!empty($filters['city'])) {
            $sql .= " AND city LIKE ?";
            $params[] = "%" . $filters['city'] . "%";
            $types .= "s";
        }

        if (!empty($filters['state'])) {
            $sql .= " AND state LIKE ?";
            $params[] = "%" . $filters['state'] . "%";
            $types .= "s";
        }

        if (!empty($filters['pincode'])) {
            $sql .= " AND pincode = ?";
            $params[] = $filters['pincode'];
            $types .= "s";
        }

        if (!empty($filters['services'])) {
            $sql .= " AND services LIKE ?";
            $params[] = "%" . $filters['services'] . "%";
            $types .= "s";
        }

        $sql .= " ORDER BY scraped_date DESC LIMIT 1000";

        $stmt = $this->conn->prepare($sql);

        if (!empty($params)) {
            $stmt->bind_param($types, ...$params);
        }

        $stmt->execute();
        return $stmt->get_result()->fetch_all(MYSQLI_ASSOC);
    }

    // Get statistics
    public function getStats() {
        $stats = [];

        // Total agents
        $result = $this->conn->query("SELECT COUNT(*) as total FROM agents WHERE status = 'active'");
        $stats['total'] = $result->fetch_assoc()['total'];

        // By city
        $result = $this->conn->query("SELECT city, COUNT(*) as count FROM agents WHERE status = 'active' GROUP BY city ORDER BY count DESC LIMIT 10");
        $stats['by_city'] = $result->fetch_all(MYSQLI_ASSOC);

        // By state
        $result = $this->conn->query("SELECT state, COUNT(*) as count FROM agents WHERE status = 'active' AND state IS NOT NULL AND state != '' GROUP BY state ORDER BY count DESC");
        $stats['by_state'] = $result->fetch_all(MYSQLI_ASSOC);

        // By services
        $result = $this->conn->query("SELECT services, COUNT(*) as count FROM agents WHERE status = 'active' GROUP BY services ORDER BY count DESC");
        $stats['by_services'] = $result->fetch_all(MYSQLI_ASSOC);

        return $stats;
    }
}

// Example usage and manual data entry form
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['action'])) {
    $scraper = new GoogleBusinessScraper();

    if ($_POST['action'] === 'add_manual') {
        // Manual entry from form
        $data = [
            'business_name' => $_POST['business_name'] ?? '',
            'address' => $_POST['address'] ?? '',
            'phone' => $_POST['phone'] ?? '',
            'city' => $_POST['city'] ?? '',
            'state' => $_POST['state'] ?? '',
            'pincode' => $_POST['pincode'] ?? '',
            'website' => $_POST['website'] ?? '',
            'email' => $_POST['email'] ?? '',
            'services' => $_POST['services'] ?? '',
            'google_place_id' => uniqid('manual_', true), // Generate unique ID for manual entries
            'source_location' => 'Manual Entry',
            'latitude' => $_POST['latitude'] ?? null,
            'longitude' => $_POST['longitude'] ?? null
        ];

        $result = $scraper->insertAgent($data);
        echo json_encode($result);
        exit;
    }
}
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Immigration Agents Scraper</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <h1>Immigration Agents Data Scraper</h1>

        <div class="notice">
            <h3>Important Notice:</h3>
            <p>Direct Google scraping is challenging due to anti-bot measures. This script provides the foundation.</p>
            <p>For production use, consider:</p>
            <ul>
                <li>Manual data entry (form below)</li>
                <li>CSV import functionality</li>
                <li>Google Places API integration</li>
                <li>Third-party scraping services (SerpAPI, ScraperAPI)</li>
            </ul>
        </div>

        <div class="section">
            <h2>Manual Data Entry</h2>
            <form id="manualEntryForm">
                <div class="form-row">
                    <div class="form-group">
                        <label>Business Name *</label>
                        <input type="text" name="business_name" required>
                    </div>
                    <div class="form-group">
                        <label>Phone *</label>
                        <input type="text" name="phone" required>
                    </div>
                </div>

                <div class="form-group">
                    <label>Address</label>
                    <textarea name="address" rows="2"></textarea>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>City *</label>
                        <input type="text" name="city" required>
                    </div>
                    <div class="form-group">
                        <label>State *</label>
                        <input type="text" name="state" required>
                    </div>
                    <div class="form-group">
                        <label>PIN Code</label>
                        <input type="text" name="pincode">
                    </div>
                </div>

                <div class="form-row">
                    <div class="form-group">
                        <label>Website</label>
                        <input type="url" name="website">
                    </div>
                    <div class="form-group">
                        <label>Email</label>
                        <input type="email" name="email">
                    </div>
                </div>

                <div class="form-group">
                    <label>Services *</label>
                    <select name="services" required>
                        <option value="">Select Service</option>
                        <option value="Immigration">Immigration</option>
                        <option value="IELTS">IELTS</option>
                        <option value="PTE">PTE</option>
                        <option value="Immigration, IELTS">Immigration + IELTS</option>
                        <option value="Immigration, PTE">Immigration + PTE</option>
                        <option value="IELTS, PTE">IELTS + PTE</option>
                        <option value="Immigration, IELTS, PTE">All Services</option>
                    </select>
                </div>

                <button type="submit" class="btn-primary">Add Agent</button>
            </form>
            <div id="formMessage"></div>
        </div>

        <div class="section">
            <a href="index.php" class="btn-primary">View All Agents Dashboard</a>
        </div>
    </div>

    <script>
        document.getElementById('manualEntryForm').addEventListener('submit', function(e) {
            e.preventDefault();

            const formData = new FormData(this);
            formData.append('action', 'add_manual');

            fetch('scraper.php', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                const messageDiv = document.getElementById('formMessage');
                if (data.success) {
                    messageDiv.innerHTML = '<div class="success">' + data.message + '</div>';
                    this.reset();
                } else {
                    messageDiv.innerHTML = '<div class="error">' + data.message + '</div>';
                }
            })
            .catch(error => {
                document.getElementById('formMessage').innerHTML = '<div class="error">Error: ' + error + '</div>';
            });
        });
    </script>
</body>
</html>
