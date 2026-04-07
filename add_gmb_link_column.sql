-- Add GMB link column to agents table
-- Run this SQL in phpMyAdmin or MySQL command line

USE immigration_agents_db;

-- Add the gmb_link column
ALTER TABLE agents
ADD COLUMN gmb_link VARCHAR(500) DEFAULT '' AFTER longitude;

-- Verify the change
DESCRIBE agents;

-- Success message
SELECT 'GMB link column added successfully!' AS status;
