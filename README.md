# Risk Assessment and Decision-Making System

## Overview

This project implements a risk assessment and decision-making system for a financial service. It uses FastAPI to expose various endpoints for risk calculations, user assessments, and financial decisions.


## Key Components

1. **API Routes** (`decision.py`): Defines FastAPI routes for various risk assessment and decision-making processes.

2. **Score Retrieval** (`scoreRetrieval.py`): Manages the retrieval and caching of risk scores from an external API.

3. **Utility Functions** (`utility.py`): Provides helper functions for database connections, configuration management, and data retrieval.

4. **Custom Logging** (`utils.py`): Implements custom JSON logging for better log management.

5. **Risk Level Assessment** (`risklevel.py`): Handles activation risk scoring.

6. **Payroll Grace Period** (`PRGracePeriod.py`): Manages decisions related to payroll grace periods.

7. **Microservice Endpoints** (`microservice_endpoints.py`): Interacts with external services, particularly for Express CM status and direct deposit information.

## Main Features

- Max Adjustment Calculations
- Express Future Max Determination
- Restore Grace Period Decisions
- Savings Deposit Request Risk Assessment
- New User Max Calculations
- Payroll Grace Period Decisions
- Competitor Max Decisions
- Unemployment Checks for Existing Users

## Technical Stack

- **Framework**: FastAPI
- **Database**: Custom database connection methods (likely SQL Server)
- **External Services**: Express CM service
- **Logging**: Python's logging module with custom JSON formatting
- **Monitoring**: Datadog statsd
- **Configuration**: Custom configuration module (`ah_config`)
- **Experimentation**: Custom A/B testing framework

## Setup and Configuration

### Pre-requisites

 * Docker - https://www.docker.com/products/docker-desktop
 * Python3 - https://www.python.org/downloads/
 * **credentials** file in ~/.aws/ containing:
   * valid AWS credentials
   * region = us-west-2
   * see https://app.tettra.co/teams/activehours/pages/setting-up-aws-mfa-locally

```bash

# Build the app

python3 scripts/docker_helper.py build

# Run a folder of tests

python3 scripts/docker_helper.py test ./integration-tests/

# Run a specific test

python3 scripts/docker_helper.py test ./integration-tests/test_get_old_max.py

# NOTE: The "test" command runs tests as integration tests by default, 
# meaning a local webserver will automatically be started as apart of the tests

# Run unit tests

python3 scripts/docker_helper.py test ./unit-tests/ -u

# Start the app in development mode

python3 scripts/docker_helper.py start

# Help

python3 scripts/docker_helper.py ---help

# Get help for a specific command

python3 scripts/docker_helper.py start --help

```
