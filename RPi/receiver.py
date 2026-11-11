import logging

import hike
import db
import bt
from activity_rec import ActivityRecognition

logging.basicConfig(filename="receiver.log", level=logging.INFO,
                    format="%(asctime)s - %(levelname)s - %(message)s", force=True)

hubdb = db.HubDatabase()
hubbt = bt.HubBluetooth()

activity_rec = ActivityRecognition()
bt.set_activity_recognition(activity_rec)


def process_sessions(sessions: list[hike.HikeSession], user_id):
    """Callback function to process sessions.

    Calculates the calories for a hiking session.
    Saves the session into the database for the specified user.

    Args:
        sessions: list of `hike.HikeSession` objects to process
    """
    for s in sessions:
        s.calc_kcal()

        if activity_rec.is_ready:
            s.activity_mode = activity_rec.get_dominant_activity()
            s.activity_distribution = activity_rec.get_activity_distribution()
            logging.info(f"Session {s.id} activity mode: {s.activity_mode}")
        else:
            s.activity_mode = "unknown"
            s.activity_distribution = {}

        hubdb.save(s, user_id)
        activity_rec.reset()
        logging.info(f"Processed and saved session {s.id} for user {user_id}.")


def main():
    print("Starting Bluetooth receiver.")
    print("Initializing database...")
    hubdb.init_user()
    hubdb.migrate_database()

    print("Initializing activity recognition model...")
    if activity_rec.initialize():
        print("Activity recognition model loaded.")
    else:
        print("No trained model found; activity recognition will remain unknown.")

    try:
        while True:
            hubbt.wait_for_connection()
            hubbt.synchronize(callback=process_sessions)

    except KeyboardInterrupt:
        logging.info("CTRL+C Pressed. Shutting down the server.")
        print("Shutting down...")
    except Exception as e:
        logging.error(f"Unexpected shutdown... ERROR: {e}")
        print(f"Error: {e}")
        if hasattr(hubbt, 'sock') and hubbt.sock:
            hubbt.sock.close()
        raise e


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception("Receiver crashed: %s", e)
        raise
