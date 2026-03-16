"""
PM2 Auto-Monitor - Monitors processes and restarts crashed ones
Run via: python monitor_and_restart.py
Or schedule with Windows Task Scheduler
"""
import subprocess
import time
import json
from datetime import datetime

CHECK_INTERVAL = 60  # seconds between checks

def get_pm2_list():
    """Get list of PM2 processes with status"""
    try:
        result = subprocess.run(
            ['pm2', 'jlist'],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return json.loads(result.stdout)
        return []
    except Exception as e:
        print(f"Error getting PM2 list: {e}")
        return []

def check_and_restart():
    """Check processes and restart if needed"""
    processes = get_pm2_list()
    restarted = []
    
    for proc in processes:
        name = proc.get('name', 'unknown')
        pm_id = proc.get('pm_id')
        status = proc.get('status', '')
        pid = proc.get('pid', 0)
        
        # Check if process is not online or has no pid
        if status != 'online' or pid == 0:
            # Skip if it's intentionally stopped (waiting)
            if 'waiting' in status.lower():
                continue
                
            print(f"[{datetime.now().isoformat()}] Process {name} (id={pm_id}) status={status}, pid={pid} - RESTARTING")
            try:
                subprocess.run(['pm2', 'restart', str(pm_id)], timeout=30)
                restarted.append(name)
            except Exception as e:
                print(f"  Error restarting {name}: {e}")
    
    if restarted:
        print(f"Restarted: {restarted}")
    
    return restarted

def main():
    print(f"PM2 Auto-Monitor started. Checking every {CHECK_INTERVAL}s")
    print("Press Ctrl+C to stop")
    
    while True:
        try:
            check_and_restart()
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            print("\nStopping monitor...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
