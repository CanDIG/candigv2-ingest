from config import DAEMON_PATH
import os
from watchdog.observers import Observer
import watchdog.events
from candigv2_logging.logging import initialize, CanDIGLogger
import json
from katsu_ingest import ingest_schemas
from htsget_ingest import htsget_ingest


KATSU_URL = os.environ.get("KATSU_URL")


logger = CanDIGLogger(__file__)

initialize()


def ingest_file(file_path):
    json_data = None
    results = {}
    results_path = os.path.join(DAEMON_PATH, "results", os.path.basename(file_path))
    with open(file_path) as f:
        json_data = json.load(f)
    if json_data is not None:
        logger.info(f"Ingesting {file_path}")
        if "katsu" in json_data:
            json_data = json_data["katsu"]
            programs = list(json_data.keys())
            for program_id in programs:
                ingest_results, status_code = ingest_schemas(json_data[program_id]["schemas"])
                results[program_id] = ingest_results
        elif "htsget" in json_data:
            json_data = json_data["htsget"]
            programs = list(json_data.keys())
            for program_id in programs:
                ingest_results, status_code = htsget_ingest(json_data[program_id])
                results[program_id] = ingest_results
        with open(results_path, "w") as f:
            json.dump(results, f)
        os.remove(file_path)
        return results, status_code
    return {"error": f"No such file {file_path}"}, 404


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
