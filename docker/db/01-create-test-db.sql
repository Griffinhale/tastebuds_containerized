-- Create a dedicated test database for API test runs in Docker.
CREATE DATABASE tastebuds_test;
GRANT ALL PRIVILEGES ON DATABASE tastebuds_test TO tastebuds;
