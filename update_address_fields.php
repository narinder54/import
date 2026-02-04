#!/usr/bin/env php
<?php
/**
 * Update Address Fields Script (PHP Version)
 * Updates city, state, and pincode for all existing records based on their addresses
 */

class AddressUpdater {
    private $cities_by_state;
    private $conn;

    public function __construct() {
        // Load cities database
        $cities_json = file_get_contents('cities_by_state.json');
        $this->cities_by_state = json_decode($cities_json, true);

        // Connect to database (XAMPP MySQL socket)
        $this->conn = new mysqli('localhost', 'root', '', 'immigration_agents_db', 3306, '/Applications/XAMPP/xamppfiles/var/mysql/mysql.sock');

        if ($this->conn->connect_error) {
            die("❌ Connection failed: " . $this->conn->connect_error . "\n");
        }
    }

    public function extract_pincode($address) {
        if (empty($address)) {
            return null;
        }
        preg_match('/\b\d{6}\b/', $address, $matches);
        return $matches[0] ?? null;
    }

    public function extract_city_from_address($address) {
        if (empty($address)) {
            return null;
        }

        // Split address by comma and clean up parts
        $parts = array_map('trim', explode(',', $address));
        if (count($parts) < 3) {
            return null;
        }

        // Address format: ..., City, State Pincode
        // Get last part (should be "State Pincode" or just "Pincode")
        $last_part = end($parts);

        // Remove pincode from last part to get potential state
        $last_part_cleaned = trim(preg_replace('/\b\d{6}\b/', '', $last_part));

        // If last part had both state and pincode, city is second-to-last
        // If last part was just pincode, state is second-to-last and city is third-to-last
        if (!empty($last_part_cleaned)) {
            // Format: ..., City, State Pincode
            $potential_city = count($parts) >= 2 ? $parts[count($parts) - 2] : null;
        } else {
            // Format: ..., City, State, Pincode
            $potential_city = count($parts) >= 3 ? $parts[count($parts) - 3] : null;
        }

        if (empty($potential_city)) {
            return null;
        }

        $potential_city = trim($potential_city);

        // Validate city exists in our database
        foreach ($this->cities_by_state as $state_name => $cities) {
            foreach ($cities as $city_name) {
                if (strcasecmp($potential_city, $city_name) === 0) {
                    return $city_name;
                }
                // Also check if potential_city contains the city name
                if (stripos($potential_city, $city_name) !== false) {
                    return $city_name;
                }
            }
        }

        return null;
    }

    public function extract_state_from_address($address) {
        if (empty($address)) {
            return null;
        }

        // Split address by comma and clean up parts
        $parts = array_map('trim', explode(',', $address));
        if (count($parts) < 2) {
            return null;
        }

        // Address format: ..., City, State Pincode OR ..., City, State, Pincode
        // Get last part
        $last_part = end($parts);

        // Remove pincode from last part to get potential state
        $last_part_cleaned = trim(preg_replace('/\b\d{6}\b/', '', $last_part));

        // Determine which part contains state
        if (!empty($last_part_cleaned)) {
            // Format: ..., City, State Pincode
            $potential_state = $last_part_cleaned;
        } else {
            // Format: ..., City, State, Pincode - state is second-to-last
            $potential_state = count($parts) >= 2 ? $parts[count($parts) - 2] : null;
        }

        if (empty($potential_state)) {
            return null;
        }

        $potential_state_lower = strtolower($potential_state);

        // State abbreviations and alternate names
        $state_mappings = [
            'mh' => 'Maharashtra', 'maharashtra' => 'Maharashtra',
            'ka' => 'Karnataka', 'karnataka' => 'Karnataka',
            'tn' => 'Tamil Nadu', 'tamil nadu' => 'Tamil Nadu', 'tamilnadu' => 'Tamil Nadu',
            'tg' => 'Telangana', 'telangana' => 'Telangana',
            'ap' => 'Andhra Pradesh', 'andhra pradesh' => 'Andhra Pradesh',
            'gj' => 'Gujarat', 'gujarat' => 'Gujarat',
            'rj' => 'Rajasthan', 'rajasthan' => 'Rajasthan',
            'up' => 'Uttar Pradesh', 'uttar pradesh' => 'Uttar Pradesh',
            'mp' => 'Madhya Pradesh', 'madhya pradesh' => 'Madhya Pradesh',
            'pb' => 'Punjab', 'punjab' => 'Punjab',
            'hr' => 'Haryana', 'haryana' => 'Haryana',
            'wb' => 'West Bengal', 'west bengal' => 'West Bengal',
            'kl' => 'Kerala', 'kerala' => 'Kerala',
            'or' => 'Odisha', 'odisha' => 'Odisha', 'orissa' => 'Odisha',
            'jh' => 'Jharkhand', 'jharkhand' => 'Jharkhand',
            'as' => 'Assam', 'assam' => 'Assam',
            'br' => 'Bihar', 'bihar' => 'Bihar',
            'cg' => 'Chhattisgarh', 'chhattisgarh' => 'Chhattisgarh',
            'ga' => 'Goa', 'goa' => 'Goa',
            'hp' => 'Himachal Pradesh', 'himachal pradesh' => 'Himachal Pradesh',
            'jk' => 'Jammu and Kashmir', 'jammu and kashmir' => 'Jammu and Kashmir',
            'dl' => 'Delhi', 'delhi' => 'Delhi', 'new delhi' => 'Delhi',
            'ch' => 'Chandigarh', 'chandigarh' => 'Chandigarh',
            'py' => 'Puducherry', 'puducherry' => 'Puducherry', 'pondicherry' => 'Puducherry',
            'uk' => 'Uttarakhand', 'uttarakhand' => 'Uttarakhand',
        ];

        // Check exact match first
        foreach ($state_mappings as $key => $state_name) {
            if ($potential_state_lower === $key || $potential_state_lower === str_replace(' ', '', $key)) {
                return $state_name;
            }
        }

        // Check if state name is contained in the potential state part
        foreach (array_keys($this->cities_by_state) as $state_name) {
            if (stripos($potential_state_lower, strtolower($state_name)) !== false) {
                return $state_name;
            }
        }

        return null;
    }

    public function update_all_records() {
        // Get all records with addresses
        $result = $this->conn->query("SELECT id, business_name, address, city, state, pincode FROM agents WHERE address IS NOT NULL AND address != ''");

        if (!$result) {
            echo "❌ Query error: " . $this->conn->error . "\n";
            return;
        }

        $records = $result->fetch_all(MYSQLI_ASSOC);
        $total_records = count($records);

        echo "📊 Found {$total_records} records with addresses\n";
        echo str_repeat("=", 80) . "\n\n";

        $updated_count = 0;
        $skipped_count = 0;
        $error_count = 0;

        foreach ($records as $idx => $record) {
            $record_id = $record['id'];
            $business_name = $record['business_name'];
            $address = $record['address'];
            $old_city = $record['city'];
            $old_state = $record['state'];
            $old_pincode = $record['pincode'];

            // Extract new values
            $new_city = $this->extract_city_from_address($address);
            $new_state = $this->extract_state_from_address($address);
            $new_pincode = $this->extract_pincode($address);

            // Check if any value changed
            $city_changed = !empty($new_city) && $new_city !== $old_city;
            $state_changed = !empty($new_state) && $new_state !== $old_state;
            $pincode_changed = !empty($new_pincode) && $new_pincode !== $old_pincode;

            if ($city_changed || $state_changed || $pincode_changed) {
                $num = $idx + 1;
                echo "[{$num}/{$total_records}] Updating: " . substr($business_name, 0, 50) . "\n";
                echo "  📍 Address: " . substr($address, 0, 80) . "...\n";

                if ($city_changed) {
                    echo "  🏙️  City: {$old_city} → {$new_city}\n";
                }
                if ($state_changed) {
                    echo "  🗺️  State: {$old_state} → {$new_state}\n";
                }
                if ($pincode_changed) {
                    echo "  📮 Pincode: {$old_pincode} → {$new_pincode}\n";
                }

                // Update record
                $final_city = $new_city ?: $old_city;
                $final_state = $new_state ?: $old_state;
                $final_pincode = $new_pincode ?: $old_pincode;

                $stmt = $this->conn->prepare("UPDATE agents SET city = ?, state = ?, pincode = ? WHERE id = ?");
                $stmt->bind_param("sssi", $final_city, $final_state, $final_pincode, $record_id);

                if ($stmt->execute()) {
                    $updated_count++;
                    echo "  ✅ Updated successfully\n\n";
                } else {
                    $error_count++;
                    echo "  ❌ Error updating: " . $stmt->error . "\n\n";
                }

                $stmt->close();
            } else {
                $skipped_count++;
                if (($idx + 1) % 50 === 0) {
                    $num = $idx + 1;
                    echo "[{$num}/{$total_records}] No changes needed, continuing...\n";
                }
            }
        }

        // Summary
        echo "\n" . str_repeat("=", 80) . "\n";
        echo "📊 Update Summary:\n";
        echo str_repeat("=", 80) . "\n";
        echo "  ✅ Updated: {$updated_count} records\n";
        echo "  ⏭️  Skipped (no changes): {$skipped_count} records\n";
        echo "  ❌ Errors: {$error_count} records\n";
        echo "  📝 Total processed: {$total_records} records\n";
        echo str_repeat("=", 80) . "\n\n";
    }

    public function __destruct() {
        if ($this->conn) {
            $this->conn->close();
        }
    }
}

// Main execution
echo "\n🔄 Starting Address Field Update\n";
echo str_repeat("=", 80) . "\n";
echo "This script will update city, state, and pincode for all records\n";
echo "based on their addresses using proper parsing logic.\n";
echo str_repeat("=", 80) . "\n\n";

$updater = new AddressUpdater();
$updater->update_all_records();

echo "✅ Update complete!\n\n";
?>
