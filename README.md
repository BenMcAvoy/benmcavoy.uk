# My Portfolio

A responsive portfolio website built with Flask showcasing my projects, skills, and experience.

## Design

- GitHub activity integration showing recent contributions
- Contact form using ntfy.sh
- Docker deployment
- Project showcase

## Tech Stack

- Backend: Flask (Python)
- Frontend: HTML, CSS, JavaScript (vanilla)
- Deployment: Docker, Gunicorn
- APIs: GitHub REST API
- Notifications: ntfy.sh

## Local Development

### Prerequisites

- Python 3.11+
- uv package management

### Setup

1. Clone the repository:
```bash
git clone https://github.com/BenMcAvoy/benmcavoy.uk.git
cd benmcavoy.uk
uv run python app.py
```
The site will be available at `http://localhost:5000`.

## Production Deployment

### Using Docker

1. Make sure to first create a `.env` file with the necessary environment variables (see `.env.example`).
2. Make sure to edit `docker-compose.yml` with anything you need to change. (you may not need to change anything)
3. Build and run the Docker containers:
```bash
docker build -t benmcavoy.uk .
docker-compose up -d
```

## License

MIT License - See LICENSE file for details

## Contact

- Email: ben.mcavoy@tutanota.com
- GitHub: [@BenMcAvoy](https://github.com/BenMcAvoy)
- Website: [benmcavoy.uk](https://benmcavoy.uk)
