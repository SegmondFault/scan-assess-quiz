# count_devices Module

This module performs a network scan using nmap to discover active devices and generates quiz questions based on the device count.

## How it works

1. **Network Detection**: Automatically detects your local network
2. **nmap Scan**: Runs `nmap -sn` to ping scan the network and discover active devices
3. **Question Generation**: Creates dynamic quiz questions based on the actual device count discovered

## Generated Questions

### Question 1: Device Count Estimation
- Asks the user to guess how many devices were discovered
- Provides multiple choice options around the actual count
- Scores based on accuracy:
  - Exact match: +20 (local_area_network), +10 (awareness_and_compliance)
  - Within 1 device: +10, +5
  - Off by more: -5, -2

### Question 2: Network Monitoring Awareness
- Questions the user about regular network monitoring practices
- Scores based on monitoring frequency

## Requirements

- `nmap` must be installed on the system and available in PATH
- The user must have network access to perform the scan
- Appropriate permissions to run network scans

## Error Handling

If nmap is not installed or the scan fails, the module gracefully reports the error and returns no questions.
