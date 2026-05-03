# MirageNet

MirageNet is a high-interaction, multi-protocol honeypot system designed for real-time threat intelligence discovery. It captures, logs, and categorizes network attacks across various service simulations.

---

## Project Demo

[![MirageNet - Live SOC Dashboard & Honeypot Demo](https://img.youtube.com/vi/J_4JA4qYdMo/0.jpg)](https://www.youtube.com/watch?v=J_4JA4qYdMo)

Watch the full demo: Click the image above to see MirageNet in action, including live attack tracking and the SOC dashboard.

---

## Key Features

* **SSH Sensor**: A full Linux-like terminal simulation that captures authentication attempts and command execution logs using a fake file system.
* **HTTP Sensor**: A deceptive web listener that redirects unauthorized requests to a WordPress login decoy, capturing brute-force and payload upload attempts.
* **SOC Management Dashboard**: A secure, hidden interface accessible via a secret URL path. It provides live attack pulse monitoring, geographical distribution maps, and detailed session reports.
* **Automated Forensics**: Real-time behavioral categorization (e.g., Malware Deployment, Brute Force) and automated PDF/JSON data exports for incident response.
* **Ghost Mode Architecture**: Implements security middleware that hides the dashboard from scanners and unauthorized traffic.

---

## Technology Stack

* **Sensors**: Python-based custom listeners for SSH and HTTP.
* **Database**: PostgreSQL for structured attack telemetry storage.
* **Dashboard**: Django framework with HTMX integration for dynamic, real-time analytics.
* **Web Server**: Process-level deployment using Waitress for production stability.

---

## Getting Started

1. **Configure PostgreSQL** and update the **.env** file with your credentials.
2. **Install the necessary packages**:
   `pip install -r requirements.txt`
3. **Run migrations** to initialize Django session tables:
   `python web_dashboard/manage.py migrate`
4. **Initialize the system**:
   `python main.py`

---

## Disclaimer

This software is for security research and educational purposes only. Unauthorized deployment in production environments without proper authorization is prohibited.
