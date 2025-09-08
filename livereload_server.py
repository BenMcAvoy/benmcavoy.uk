from livereload import Server
from app import app

# Create livereload server and wrap the Flask app
server = Server(app.wsgi_app)

# Watch templates and python files for changes
server.watch('templates/*.html')
server.watch('static/styles.css')
server.watch('*.py')

# Optionally watch static files
server.watch('static/*')

if __name__ == '__main__':
    # Start the livereload server on port 5000 and live-reload port 35729
    print('Starting livereload server on http://0.0.0.0:5000')
    server.serve(port=5000, host='0.0.0.0', liveport=35729, open_url_delay=None)
