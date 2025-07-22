# CA-GPU-Monitoring

**CA-GPU-Monitoring** is a lightweight GPU monitoring tool tailored for systems utilizing CUDA-based GPUs. The project is built to efficiently monitor GPU utilization across machines, especially in cluster or lab environments.

## Features

- Real-time GPU usage monitoring
- User-specific process tracking
- Web interface to monitor all machines in a lab or cluster
- Multi-platform support (Linux tested)
- Built using Python, Flask, and NVIDIA's `nvidia-smi`

## Project Structure

```
.
├── backend/            # Flask backend server to monitor GPU status
│   ├── app.py
│   └── utils.py
├── frontend/           # Frontend assets for displaying GPU usage (optional or under development)
├── README.md
└── requirements.txt    # Python dependencies
```

## Getting Started

### Prerequisites

- Python 3.7+
- NVIDIA GPU and drivers installed
- `nvidia-smi` available in path
- Recommended: virtualenv or conda for environment isolation

### Installation

1. Clone the repository:

```bash
git clone https://github.com/MoeenHP/CA-GPU-Monitoring.git
cd CA-GPU-Monitoring/backend
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the application:

```bash
python app.py
```

The backend server should now be running on `http://localhost:8000` (or a port defined in the code).

## Usage

Visit the web interface to see all connected machines and their current GPU usage. You can customize or extend the tool to push data from multiple systems to a centralized frontend.


## Contributing

Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change or add.

## License

[MIT License](https://opensource.org/licenses/MIT)
