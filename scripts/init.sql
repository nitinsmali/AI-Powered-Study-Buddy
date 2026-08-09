-- This file is automatically executed by MySQL's docker-entrypoint.
-- It creates the database with proper charset/collation settings
-- (docker-compose already creates the DB via MYSQL_DATABASE, but this
--  ensures the right character set is applied).

ALTER DATABASE study_buddy
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
