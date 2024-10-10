until python daemon.py; do
    echo "Daemon crashed with exit code $?.  Respawning.." >&2
    sleep 1
done