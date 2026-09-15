-- Initialize database for Lenny Growth Assistant
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- The tables will be created by the application on startup
-- This file just ensures the extension is available