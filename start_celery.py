#!/usr/bin/env python
"""
Startup script for Celery worker and beat scheduler
"""
import os
import sys
import subprocess
import time

def start_celery_worker():
    """Start Celery worker"""
    print("Starting Celery worker...")
    worker_cmd = [
        sys.executable, '-m', 'celery', 
        'worker', 
        '-A', 'landnest',
        '--loglevel=info',
        '--concurrency=4'
    ]
    
    try:
        subprocess.run(worker_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting Celery worker: {e}")
        return False
    return True

def start_celery_beat():
    """Start Celery beat scheduler"""
    print("Starting Celery beat scheduler...")
    beat_cmd = [
        sys.executable, '-m', 'celery', 
        'beat', 
        '-A', 'landnest',
        '--loglevel=info'
    ]
    
    try:
        subprocess.run(beat_cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error starting Celery beat: {e}")
        return False
    return True

def start_both():
    """Start both worker and beat in separate processes"""
    import multiprocessing
    
    print("Starting Celery services...")
    
    # Start worker in background process
    worker_process = multiprocessing.Process(target=start_celery_worker)
    worker_process.start()
    
    # Give worker time to start
    time.sleep(2)
    
    # Start beat in background process
    beat_process = multiprocessing.Process(target=start_celery_beat)
    beat_process.start()
    
    try:
        print("Celery worker and beat are running. Press Ctrl+C to stop.")
        worker_process.join()
        beat_process.join()
    except KeyboardInterrupt:
        print("\nStopping Celery services...")
        worker_process.terminate()
        beat_process.terminate()
        worker_process.join()
        beat_process.join()
        print("Services stopped.")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == 'worker':
            start_celery_worker()
        elif sys.argv[1] == 'beat':
            start_celery_beat()
        elif sys.argv[1] == 'both':
            start_both()
        else:
            print("Usage: python start_celery.py [worker|beat|both]")
    else:
        start_both()
