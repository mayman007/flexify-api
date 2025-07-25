# Flexify API

A FastAPI-based REST API for serving wallpapers, KWGT widgets, and KLWP files with metadata extraction and caching. Used in [Flexify](https://github.com/mayman007/Flexify).

## Features

- **Wallpaper Management**: Serve wallpapers from different quality folders (hq, mid, low) with color extraction
- **KWGT Widget Support**: Handle both KWGT files and images with category organization
- **KLWP Integration**: Serve KLWP files and associated images
- **Metadata Caching**: Automatic metadata extraction and caching for improved performance
- **Color Analysis**: Extract prominent colors from wallpapers using K-means clustering
- **Async Processing**: Fully asynchronous for better performance

## Installation

### Prerequisites

- [Python](https://www.python.org/downloads/) 3.8 or higher
- [Git](https://git-scm.com/downloads) for cloning the project (recommended)

### Setup

1. **Clone or download the project files**
   ```bash
   git clone https://github.com/mayman007/flexify-api
   cd flexify-api
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create environment file**
   
   Create a `.env` file in the project root with your asset paths:
   ```env
   WALLPAPERS_BASE_PATH=C:\path\to\your\wallpapers
   WIDGETS_BASE_PATH=C:\path\to\your\widgets
   KLWP_BASE_PATH=C:\path\to\your\klwp
   ```

4. **Organize your assets**
   
   Your folder structure should look like:
   ```
   Wallpapers/
   ├── hq/
   │   ├── category1/
   │   │   ├── wallpaper1.png
   │   │   └── wallpaper2.png
   │   └── category2/
   │       ├── wallpaper3.png
   │       └── wallpaper4.png
   ├── mid/
   │   ├── category1/
   │   │   ├── wallpaper1.png
   │   │   └── wallpaper2.png
   │   └── category2/
   │       ├── wallpaper3.png
   │       └── wallpaper4.png
   └── low/
       ├── category1/
       │   ├── wallpaper1.png
       │   └── wallpaper2.png
       └── category2/
           ├── wallpaper3.png
           └── wallpaper4.png
   
   Widgets/
   ├── category1/
   │   ├── widget1.kwgt
   │   └── widget1.png (preview image)
   └── category2/
       ├── widget2.kwgt
       └── widget2.png (preview image)
   
   KLWP/
   ├── theme1.klwp
   ├── theme1.png (preview image)
   ├── theme2.klwp
   └── theme2.png (preview image)
   ```

Note: Same wallpaper in different quality folders must hold the same name.

## Running the API

### Development Mode
```bash
python main.py
```

### Production Mode
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` (or `http://127.0.0.1:8000`)

## API Documentation

Once running, visit `http://localhost:8000/docs` for interactive API documentation.

### Endpoints

#### Wallpapers

- **GET** `/wallpapers/{folder_type}` - List wallpapers by quality folder
  - Parameters: `folder_type` (hq, mid, low)
  - Returns: Array of wallpaper metadata with colors, resolution, size

- **GET** `/wallpapers/{folder_type}/{category}` - List wallpapers in specific category
  - Parameters: `folder_type`, `category`
  - Returns: Filtered wallpaper array

- **GET** `/wallpapers/{folder_type}/{category}/{filename}` - Download wallpaper file
  - Parameters: `folder_type`, `category`, `filename`
  - Returns: Image file with PNG→JPG fallback

#### Widgets

- **GET** `/widgets` - List all widgets
  - Returns: Array of widget metadata with type and category

- **GET** `/widgets/{category}` - List widgets in specific category
  - Parameters: `category`
  - Returns: Filtered widget array

- **GET** `/widgets/{category}/{filename}` - Download widget file
  - Parameters: `category`, `filename`
  - Returns: KWGT file or image with appropriate headers

#### KLWP

- **GET** `/klwp` - List all KLWP files
  - Returns: Array of KLWP file metadata

- **GET** `/klwp/{filename}` - Download KLWP file
  - Parameters: `filename`
  - Returns: KLWP file or image

### Response Examples

#### Wallpaper Response
```json
{
  "name": "wallpaper.png",
  "category": "nature",
  "resolution": "1920x1080",
  "size": 2048576,
  "colors": ["#1a2b3c", "#4d5e6f", "#7a8b9c", "#adbecf", "#d0e1f2"]
}
```

#### Widget Response
```json
{
  "name": "clock_widget.kwgt",
  "category": "clocks",
  "type": "kwgt"
}
```

#### KLWP Response
```json
{
  "name": "minimal_theme.klwp",
  "type": "klwp"
}
```

## Troubleshooting

### Common Issues

1. **"Module not found" errors**
   - Ensure all dependencies are installed: `pip install -r requirements.txt`

2. **"Path not found" errors**
   - Check your `.env` file paths are correct and directories exist
   - Ensure paths use forward slashes or escaped backslashes

3. **Color extraction fails**
   - Verify PIL/Pillow can open your image files
   - Check image files aren't corrupted

4. **Slow initial startup**
   - Normal on first run as metadata is being extracted
   - Subsequent starts use cached metadata

### Performance Tips

- Use smaller image files for faster color extraction
- Organize files in logical category folders
- The API uses threading for CPU-bound color extraction tasks

## Development

### Project Structure
```
flexify-api/
├── main.py          # FastAPI application entry point
├── routers.py       # API route definitions
├── services.py      # Business logic and caching
├── models.py        # Pydantic response models
├── config.py        # Configuration and environment variables
├── requirements.txt # Python dependencies
└── .env            # Environment variables (create this)
```

### Adding New Features

1. Add new routes in `routers.py`
2. Implement business logic in `services.py`
3. Define response models in `models.py`
4. Update configuration in `config.py` if needed

## Hosting on VPS (Internet Access)

### Prerequisites for VPS Deployment

- VPS with Ubuntu/Debian (recommended) or CentOS
- SSH access to your VPS
- Domain name (optional but recommended)
- Basic knowledge of Linux commands

Note: You can create a VPS with free tier/trial from [OCI](https://www.oracle.com/cloud/), [GCP](https://cloud.google.com/), [AWS](https://aws.amazon.com/), etc.

### Step-by-Step VPS Setup

1. **Connect to your VPS**
   ```bash
   ssh root@your-vps-ip
   # or
   ssh username@your-vps-ip
   ```

2. **Update system packages**
   ```bash
   sudo apt update && sudo apt upgrade -y  # Ubuntu/Debian
   # or
   sudo yum update -y  # CentOS
   ```

3. **Install Python and pip**
   ```bash
   sudo apt install python3 python3-pip python3-venv -y  # Ubuntu/Debian
   # or
   sudo yum install python3 python3-pip -y  # CentOS
   ```

4. **Upload your project files**
   ```bash
   # Using scp from your local machine
   scp -r flexify-api/ username@your-vps-ip:/home/username/
   
   # Or clone from repository
   git clone https://github.com/yourusername/flexify-api.git
   cd flexify-api
   ```

5. **Install dependencies**
   ```bash
   cd flexify-api
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

6. **Configure environment**
   ```bash
   # Create .env file with your VPS paths
   nano .env
   ```
   Example VPS `.env`:
   ```env
   WALLPAPERS_BASE_PATH=/home/username/assets/wallpapers
   WIDGETS_BASE_PATH=/home/username/assets/widgets
   KLWP_BASE_PATH=/home/username/assets/klwp
   ```

7. **Upload your asset files**
   ```bash
   # Create asset directories
   mkdir -p /home/username/assets/{wallpapers,widgets,klwp}
   
   # Upload from local machine
   scp -r /path/to/local/wallpapers/ username@your-vps-ip:/home/username/assets/
   scp -r /path/to/local/widgets/ username@your-vps-ip:/home/username/assets/
   scp -r /path/to/local/klwp/ username@your-vps-ip:/home/username/assets/
   ```

### Running in Production

#### Option 1: Simple Screen Session
```bash
# Install screen
sudo apt install screen -y

# Start a screen session
screen -S flexify-api

# Activate virtual environment and run
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000

# Detach from screen: Ctrl+A then D
# Reattach later: screen -r flexify-api
```

#### Option 2: Using Systemd Service (Recommended)

1. **Create service file**
   ```bash
   sudo nano /etc/systemd/system/flexify-api.service
   ```

2. **Add service configuration**
   ```ini
   [Unit]
   Description=Flexify API
   After=network.target

   [Service]
   Type=simple
   User=username
   WorkingDirectory=/home/username/flexify-api
   Environment=PATH=/home/username/flexify-api/venv/bin
   ExecStart=/home/username/flexify-api/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   ```

3. **Enable and start service**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable flexify-api
   sudo systemctl start flexify-api
   
   # Check status
   sudo systemctl status flexify-api
   ```

### Firewall Configuration

```bash
# Ubuntu/Debian (UFW)
sudo ufw allow 8000
sudo ufw enable

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --reload
```
Note: You may need to open the port from the VPS console.

### Using a Reverse Proxy (Recommended)

#### Install and Configure Nginx

1. **Install Nginx**
   ```bash
   sudo apt install nginx -y  # Ubuntu/Debian
   # or
   sudo yum install nginx -y  # CentOS
   ```

2. **Create Nginx configuration**
   ```bash
   sudo nano /etc/nginx/sites-available/flexify-api
   ```

3. **Add configuration**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;  # Replace with your domain or VPS IP
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
   }
   ```

4. **Enable configuration**
   ```bash
   sudo ln -s /etc/nginx/sites-available/flexify-api /etc/nginx/sites-enabled/
   sudo nginx -t  # Test configuration
   sudo systemctl restart nginx
   ```

### SSL Certificate (HTTPS)

#### Using Certbot (Let's Encrypt)

```bash
# Install Certbot
sudo apt install certbot python3-certbot-nginx -y

# Get SSL certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already set up by certbot)
sudo certbot renew --dry-run
```

### Access Your API

After setup, your API will be accessible at:
- **HTTP**: `http://your-vps-ip:8000` or `http://your-domain.com`
- **HTTPS**: `https://your-domain.com` (if SSL configured)
- **API Docs**: `http://your-domain.com/docs`

### Security Considerations

1. **Change default SSH port**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Change Port 22 to Port 2222 (or another port)
   sudo systemctl restart ssh
   ```

2. **Disable root login**
   ```bash
   sudo nano /etc/ssh/sshd_config
   # Set PermitRootLogin no
   sudo systemctl restart ssh
   ```

3. **Use strong passwords or SSH keys**
4. **Keep system updated**
5. **Consider using fail2ban for brute force protection**

### Monitoring and Logs

```bash
# Check service logs
sudo journalctl -u flexify-api -f

# Check Nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log

# Monitor system resources
htop
df -h  # Check disk space
```
