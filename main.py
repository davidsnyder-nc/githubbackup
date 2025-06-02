import os
from app import app, scheduler
import atexit

if __name__ == '__main__':
    # Ensure scheduler shuts down when the app exits
    atexit.register(lambda: scheduler.shutdown())
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
