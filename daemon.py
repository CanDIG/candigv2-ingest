from config import DAEMON_PATH
import os
from watchdog.observers import Observer
import watchdog.events
from candigv2_logging.logging import initialize, CanDIGLogger
import json
from katsu_ingest import ingest_schemas
from htsget_ingest import htsget_ingest
from datetime import datetime


logger = CanDIGLogger(__file__)

initialize()


def ingest_file(file_path):
    json_data = None
    status_code = 500

    # this dictionary contains the current status/results of the ingest; it will be updated and written out to the results_path as the ingest progresses.
    results = {
        "last_updated": str(datetime.now()),
        "complete": False
    }
    results_path = os.path.join(DAEMON_PATH, "results", os.path.basename(file_path))
    try:
        with open(file_path) as f:
            json_data = json.load(f)
        if json_data is not None:
            logger.info(f"Ingesting {file_path}")
            if "katsu" in json_data:
                json_data = json_data["katsu"]
                programs = list(json_data.keys())
                for program_id in programs:
                    try:
                        ingest_results, status_code = ingest_schemas(json_data[program_id]["schemas"], results_path=results_path, result_dict=results, program_id=program_id)
                        results[program_id] = ingest_results
                    except Exception as e:
                        results[program_id] = f"Exception: {type(e)} {str(e)}"
            elif "htsget" in json_data:
                json_data = json_data["htsget"]
                programs = list(json_data.keys())
                for program_id in programs:
                    results[program_id] = {}
                for program_id in programs:
                    try:
                        results[program_id] = ingest_results
                    except Exception as e:
                        results_json = None
                        with open(results_path) as f:
                            results_json = json.load(f)
                        if results_json is not None and program_id in results_json:
                            results[program_id]["errors"].append(f"Exception during ingest: {type(e)} {str(e)}")
                        else:
                            results[program_id] = f"Exception: {type(e)} {str(e)}"
            results["complete"] = True
        os.remove(file_path)
    except Exception as e:
        message = f"Couldn't load data from {file_path}: {type(e)} {str(e)}"
        logger.error(message)
        results["error"] = message
        status_code = 500
    with open(results_path, "w") as f:
        json.dump(results, f)
    return results, status_code


class DaemonHandler(watchdog.events.FileSystemEventHandler):
    def on_created(self, event):
        ingest_file(event.src_path)


if __name__ == "__main__":
    ## look for any backlog IDs, ingest those, then listen for new IDs to ingest.
    ingest_path = os.path.join(DAEMON_PATH, "to_ingest")
    logger.info(f"ingesting started on {ingest_path}")
    to_ingest = os.listdir(ingest_path)
    logger.info(f"Finishing backlog: ingesting {to_ingest}")
    while len(to_ingest) > 0:
        try:
            file_path = f"{ingest_path}/{to_ingest.pop()}"
            ingest_file(file_path)
        except Exception as e:
            logger.warning(str(e))
        to_ingest = os.listdir(ingest_path)

    # now that the backlog is complete, listen for new files created:
    logger.info(f"listening for new files at {ingest_path}")
    event_handler = DaemonHandler()
    observer = Observer()
    observer.schedule(event_handler, ingest_path, recursive=False)
    observer.start()
    try:
        while observer.is_alive():
            observer.join(1)
    finally:
        observer.stop()
        observer.join()
