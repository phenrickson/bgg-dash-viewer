# Changelog

All notable changes to this project will be documented in this file.

## [0.3.0] - 2025-01-23

### Added
- User authentication system with Flask-Login
- User registration and login pages
- Password hashing with bcrypt
- User storage in BigQuery (`core.users` table)
- Session management with signed cookies
- Auth tests with mocked BigQuery
- SECRET_KEY configuration for production deployment

### Changed
- Updated Cloud Run deployment to include SECRET_KEY environment variable

## [0.2.0] - Previous Release

- Initial dashboard viewer functionality
- BigQuery integration for game data
- Similarity search features
