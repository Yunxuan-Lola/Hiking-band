import time
import sqlite3
import logging

import hike
import db
import bt

logging.basicConfig(filename="receiver.log", level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

hubdb = db.HubDatabase()
hubbt = bt.HubBluetooth()

def process_sessions(sessions: list[hike.HikeSession], user_id):
    """Callback function to process sessions.

    Calculates the calories for a hiking session.
    Saves the session into the database for the specified user.

    Args:
        sessions: list of `hike.HikeSession` objects to process
    """

    for s in sessions:
        s.calc_kcal()
        hubdb.save(s, user_id)
        logging.info(f"Processed and saved session {s.id} for user {user_id}.")


def main():
    print("Starting Bluetooth receiver.")
    hubdb.init_user()
    
    try:
        while True:
            hubbt.wait_for_connection()
            hubbt.synchronize(callback=process_sessions)
            
    except KeyboardInterrupt:
        #print("CTRL+C Pressed. Shutting down the server...")
        logging.info("CTRL+C Pressed. Shutting down the server.")
    except Exception as e:
        logging.error(f"Unexpected shutdown... ERROR: {e}")
        #print(f"Unexpected shutdown...")
        #print(f"ERROR: {e}")
        hubbt.sock.close()
        raise e

if __name__ == "__main__":
    try:
            main()
    except Exception as e:
        logging.error(f"Receiver crashed: {e}. Restarting in 5 seconds...")
        time.sleep(5)  # Auto-restart after failure
