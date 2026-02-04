<?php
echo "<h2>Deep Debug</h2>";

$wrapper = __DIR__ . '/run_scraper.sh';
$python = '/usr/bin/python3';

echo "<h3>Test 1: Direct Python</h3>";
$cmd1 = "$python --version 2>&1";
echo "Command: <code>$cmd1</code><br>";
$out1 = shell_exec($cmd1);
echo "Output: <pre>" . htmlspecialchars($out1) . "</pre>";

echo "<h3>Test 2: Wrapper Script --version</h3>";
$cmd2 = "$wrapper --version 2>&1";
echo "Command: <code>$cmd2</code><br>";
$out2 = shell_exec($cmd2);
echo "Output: <pre>" . htmlspecialchars($out2) . "</pre>";

echo "<h3>Test 3: Wrapper Script import playwright</h3>";
$cmd3 = "$wrapper -c \"import playwright\" 2>&1";
echo "Command: <code>$cmd3</code><br>";
$out3 = shell_exec($cmd3);
echo "Output: <pre>" . htmlspecialchars($out3 ?: '(empty - success!)') . "</pre>";
echo "Empty (success): " . (empty($out3) ? 'YES ✓' : 'NO ✗') . "<br>";
echo "Has error: " . (strpos($out3, 'ModuleNotFoundError') !== false ? 'YES ✗' : 'NO ✓') . "<br>";

echo "<h3>Test 4: Check wrapper script exists and is executable</h3>";
echo "File exists: " . (file_exists($wrapper) ? 'YES ✓' : 'NO ✗') . "<br>";
echo "Is executable: " . (is_executable($wrapper) ? 'YES ✓' : 'NO ✗') . "<br>";
echo "File permissions: " . substr(sprintf('%o', fileperms($wrapper)), -4) . "<br>";

echo "<h3>Test 5: Read wrapper script content</h3>";
echo "<pre>" . htmlspecialchars(file_get_contents($wrapper)) . "</pre>";

echo "<h3>Test 6: Which python in wrapper context</h3>";
$cmd6 = "$wrapper -c \"import sys; print(sys.executable)\" 2>&1";
echo "Command: <code>$cmd6</code><br>";
$out6 = shell_exec($cmd6);
echo "Output: <pre>" . htmlspecialchars($out6) . "</pre>";

echo "<h3>Test 7: sys.path in wrapper context</h3>";
$cmd7 = "$wrapper -c \"import sys; print('\\n'.join(sys.path))\" 2>&1";
echo "Command: <code>$cmd7</code><br>";
$out7 = shell_exec($cmd7);
echo "Output: <pre>" . htmlspecialchars($out7) . "</pre>";

echo "<h3>Test 8: Try to import and show location</h3>";
$cmd8 = "$wrapper -c \"import sys; sys.path.insert(0, '/Users/narinder/Library/Python/3.9/lib/python/site-packages'); import playwright; print('SUCCESS:', playwright.__file__)\" 2>&1";
echo "Command: <code>$cmd8</code><br>";
$out8 = shell_exec($cmd8);
echo "Output: <pre>" . htmlspecialchars($out8) . "</pre>";
?>
