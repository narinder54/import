<?php
echo "<h2>Deep Directory Access Test</h2>";

$testPath = '/Users/narinder/Library/Python/3.9/lib/python/site-packages';

echo "<h3>Can PHP read the directory?</h3>";
if (is_dir($testPath)) {
    echo "✓ Directory exists<br>";
    if (is_readable($testPath)) {
        echo "✓ Directory is readable by PHP<br>";

        // Try to list contents
        $contents = scandir($testPath);
        if ($contents) {
            echo "✓ Can list directory contents (" . count($contents) . " items)<br>";
            echo "<strong>Contents:</strong><br>";
            echo "<pre>";
            foreach ($contents as $item) {
                if ($item != '.' && $item != '..') {
                    echo $item . "\n";
                }
            }
            echo "</pre>";
        } else {
            echo "✗ Cannot list directory contents<br>";
        }
    } else {
        echo "✗ Directory is NOT readable by PHP<br>";
    }
} else {
    echo "✗ Directory does not exist or is not accessible<br>";
}

echo "<h3>Can we see playwright directory?</h3>";
$playwrightPath = $testPath . '/playwright';
if (is_dir($playwrightPath)) {
    echo "✓ Playwright directory exists<br>";
    if (is_readable($playwrightPath)) {
        echo "✓ Playwright directory is readable<br>";

        $playwrightInit = $playwrightPath . '/__init__.py';
        if (file_exists($playwrightInit)) {
            echo "✓ __init__.py exists<br>";
            if (is_readable($playwrightInit)) {
                echo "✓ __init__.py is readable<br>";
            } else {
                echo "✗ __init__.py is NOT readable<br>";
            }
        } else {
            echo "✗ __init__.py does NOT exist<br>";
        }
    } else {
        echo "✗ Playwright directory is NOT readable<br>";
    }
} else {
    echo "✗ Playwright directory does not exist or is not accessible<br>";
}

echo "<h3>Test Python can see the file directly</h3>";
$wrapper = __DIR__ . '/run_scraper.sh';
$cmd = "$wrapper -c \"import os; print('File exists:', os.path.exists('/Users/narinder/Library/Python/3.9/lib/python/site-packages/playwright/__init__.py'))\" 2>&1";
echo "Command: <code>$cmd</code><br>";
$out = shell_exec($cmd);
echo "Output: <pre>" . htmlspecialchars($out) . "</pre>";

echo "<h3>Test Python can list the directory</h3>";
$cmd2 = "$wrapper -c \"import os; print(os.listdir('/Users/narinder/Library/Python/3.9/lib/python/site-packages'))\" 2>&1";
echo "Command: <code>$cmd2</code><br>";
$out2 = shell_exec($cmd2);
echo "Output: <pre>" . htmlspecialchars($out2) . "</pre>";

echo "<h3>Test with absolute import</h3>";
$cmd3 = "$wrapper -c \"import sys; import os; sys.path.insert(0, '/Users/narinder/Library/Python/3.9/lib/python/site-packages'); print('playwright in path?', 'playwright' in os.listdir('/Users/narinder/Library/Python/3.9/lib/python/site-packages')); import playwright\" 2>&1";
echo "Command: <code>$cmd3</code><br>";
$out3 = shell_exec($cmd3);
echo "Output: <pre>" . htmlspecialchars($out3) . "</pre>";
?>
